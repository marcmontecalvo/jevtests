"""Runner + HTTP adapter + DB + report against a fake /v1/systemone server."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from harness import report
from harness.config import benchmark_config
from harness.db import DB
from harness.runner import run_benchmark
from harness.schema import Case

SEEN = []


class Fake(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.headers.get("Authorization"), body))
        q = body["questions"]["q"]
        if body["model"] == "reject":   # e.g. litjev refusing an unknown model id
            self.send_response(422)
            self.end_headers()
            return
        if q["type"] == "noul":
            ans = {"type": "noul", "noul": 0.9}
        elif q["type"] == "choice":
            keys = list(q["criteria"])
            first = keys[0]   # position-biased model: always picks the first option shown
            ans = {"type": "choice", "choice": first,
                   "probabilities": {k: (0.7 if k == first else 0.3 / (len(keys) - 1)) for k in keys}}
        else:
            self.send_response(500)
            self.end_headers()
            return
        data = json.dumps({"model": "fake-1.0", "answers": {"q": ans}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture()
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def cases():
    return [
        Case(id="t-choice", dataset="t", type="choice", state="s", question="q",
             criteria={"a": None, "b": None, "c": None}, expected="a"),
        Case(id="t-noul", dataset="t", type="noul", state="s", question="q",
             criteria=None, expected=False),
        Case(id="t-score", dataset="t", type="score", state="s", question="q",
             criteria=["x", "y"], expected=0),
    ]


def test_run_resume_and_report(tmp_path, server, monkeypatch):
    monkeypatch.setattr(report, "REPORTS", tmp_path / "reports")
    db = DB(tmp_path / "r.sqlite")
    cs = cases()
    db.upsert_cases(cs)
    bench = benchmark_config()
    bench["modes"]["latency"]["warm_requests"] = 3
    specs = [{"name": "fake", "kind": "http", "base_url": server, "params": 1e8,
              "health_path": "/", "request_timeout_s": 10},
             {"name": "broken", "kind": "http", "base_url": "http://127.0.0.1:9",
              "startup_timeout_s": 1, "params": 3e10},
             {"name": "rejecting", "kind": "http", "base_url": server, "params": 2e8,
              "health_path": "/", "request_model": "reject"}]
    modes = ("accuracy", "order", "latency", "throughput")
    SEEN.clear()
    status = asyncio.run(run_benchmark(db, "r1", specs, cs, bench, modes))
    assert status == {"fake": "done", "broken": "load_failed", "rejecting": "no_answers"}
    first_pass = len(SEEN)

    # resume: only the errored score case is retried (plus throughput is not re-run)
    asyncio.run(run_benchmark(db, "r1", specs[:1], cs, bench, ("accuracy", "throughput")))
    assert len(SEEN) == first_pass + 1

    out = report.build(db, "r1")
    summ = {s["model"]: s for s in json.loads((out / "summary.json").read_text())}
    f = summ["fake"]
    assert f["choice_acc"] == 1.0 and f["noul_acc"] == 0.0 and f["errors"] == 1
    assert f["order_order_consistency"] == 0.0        # position bias caught
    assert f["p50_ms"] is not None and f["max_decisions_per_s"] > 0
    assert f["ready_s"] >= f["load_s"] and f["first_ms"] is not None   # cold probe after load
    assert summ["broken"]["status"] == "load_failed"
    md = (out / "summary.md").read_text(encoding="utf-8")
    assert "fake" in md
    assert "every large model wrong" not in md   # only large model never answered: hidden
    assert "High-confidence wrong" in md
    assert f["clean_acc"] == f["accuracy"] and f["clean_n"] == f["n"]   # unknown dataset: clean
    assert "Max dec/s" in md and "Ready s" in md                        # optional cols with data

    # the same run with dataset "t" marked as trained on by kev: nothing clean left
    monkeypatch.setattr(report, "exposure", lambda: {"t": ["kev"]})
    out = report.build(db, "r1")
    f = {s["model"]: s for s in json.loads((out / "summary.json").read_text())}["fake"]
    assert f["clean_n"] == 0 and f["clean_acc"] is None
    md = (out / "summary.md").read_text(encoding="utf-8")
    assert "t — kev" in md and "Clean Acc" not in md   # column needs clean and seen datasets
    rows = list(__import__("csv").DictReader(open(out / "by_dataset.csv", encoding="utf-8")))
    assert {r["trained_on"] for r in rows if r["model"] == "fake"} == {"kev"}
    import csv
    errs = list(csv.DictReader(open(out / "errors.csv", encoding="utf-8")))
    assert {(e["model"], e["stage"]) for e in errs if e["model"] != "rejecting"} == {
        ("fake", "accuracy"), ("fake", "latency"), ("broken", "load")}   # current errors only


@pytest.mark.parametrize("provider,key_env,url_env", [
    ("typesafe", "JEV_API_KEY", "JEV_BASE_URL"),
    ("openrouter", "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"),
])
def test_jev_cloud_providers_send_bearer(monkeypatch, server, provider, key_env, url_env):
    from adapters.jev_cloud import JevCloud
    for k in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(key_env, "k123")
    monkeypatch.setenv(url_env, server)
    m = JevCloud({"name": "jev", "kind": "cloud", "provider": provider,
                  "request_model": "jev-latest"})

    async def go():
        await m.load()
        r = await m.evaluate(cases()[1])
        await m.unload()
        return r
    SEEN.clear()
    r = asyncio.run(go())
    assert r.error is None and r.prediction is True
    assert SEEN[0][0] == "Bearer k123" and SEEN[0][1]["model"] == "jev-latest"
    assert m.provenance["served_model"] == "fake-1.0" and m.provenance["provider"] == provider


def test_jev_cloud_missing_key_names_the_right_variable(monkeypatch):
    from adapters.jev_cloud import JevCloud
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        JevCloud({"name": "jev", "kind": "cloud", "provider": "openrouter"})
    with pytest.raises(ValueError, match="unknown provider"):
        JevCloud({"name": "jev", "kind": "cloud", "provider": "nope"})


def test_docker_served_model_samples_the_container(monkeypatch):
    from adapters import http_systemone as H
    m = H.HttpSystemOne({"name": "d", "serve": "x"})
    m.proc = type("P", (), {"pid": 111})()
    m.provenance["command"] = "python -m server --port 1"
    assert m.server_pid() == 111                      # plain process: its own pid

    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return type("R", (), {"stdout": "4242\n"})()
    monkeypatch.setattr(H.subprocess, "run", fake_run)
    m.provenance["command"] = "docker run --rm --name jevtests-d --gpus all img"
    assert m.server_pid() == 4242 and m.server_pid() == 4242
    assert calls == [["docker", "inspect", "-f", "{{.State.Pid}}", "jevtests-d"]]   # cached
    assert m.provenance["mem_source"] == "container"
