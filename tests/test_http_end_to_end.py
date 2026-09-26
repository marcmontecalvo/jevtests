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
              "startup_timeout_s": 1, "params": 3e10}]
    modes = ("accuracy", "order", "latency", "throughput")
    SEEN.clear()
    status = asyncio.run(run_benchmark(db, "r1", specs, cs, bench, modes))
    assert status == {"fake": "done", "broken": "load_failed"}   # failure isolated
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
    assert summ["broken"]["status"] == "load_failed"
    assert "fake" in (out / "summary.md").read_text(encoding="utf-8")


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
