"""Build reports/<run>/ from the SQLite store: Markdown summary + CSV/JSON detail."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from harness import metrics as M
from harness.config import REPORTS, benchmark_config, datasets_config, model_specs
from harness.db import DB
from harness.schema import Case, predicted_key
from harness.sysinfo import git_commit, git_dirty


def _f(v, fmt="{:.3f}"):
    return "–" if v is None else fmt.format(v)


def _params(p):
    if not p:
        return "–"
    return f"{p / 1e9:.1f}B" if p >= 1e9 else f"{p / 1e6:.0f}M"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


class RunData:
    def __init__(self, db: DB, run_id: str):
        self.db, self.run_id = db, run_id
        self.cases = {r["case_id"]: Case.from_dict(json.loads(r["data"]))
                      for r in db.query("SELECT case_id, data FROM cases")}
        # models disabled in config since the run (enabled: false) are dropped from reports
        disabled = {n for n, m in model_specs().items() if not m["enabled"]}
        self.models = {r["model"]: {**dict(r), "spec": json.loads(r["spec"] or "{}"),
                                    "provenance": json.loads(r["provenance"] or "{}")}
                       for r in db.query("SELECT * FROM models WHERE run_id=?", (run_id,))
                       if r["model"] not in disabled}
        self.recs = defaultdict(list)   # (model, mode) -> records
        for r in db.query("SELECT * FROM predictions WHERE run_id=?", (run_id,)):
            case = self.cases.get(r["case_id"])
            if case is None:
                continue
            pred = json.loads(r["prediction"]) if r["prediction"] else None
            probs = json.loads(r["probabilities"]) if r["probabilities"] else None
            self.recs[(r["model"], r["mode"])].append({
                "case_id": case.id, "dataset": case.dataset, "type": case.type,
                "variant": r["variant"], "rep": r["rep"], "keys": case.options,
                "expected_key": case.expected_key,
                "pred_key": None if r["error"] else predicted_key(case, pred, probs),
                "probs": probs, "top_prob": r["top_prob"], "confidence": r["confidence"],
                "correct": r["correct"], "abs_error": r["abs_error"],
                "latency_ms": r["latency_ms"], "error": r["error"]})

    def params(self, model):
        return self.models[model]["spec"].get("params")


def exposure() -> dict[str, list[str]]:
    """dataset -> upstreams trained on its train split (config/datasets.yaml `trained_on`)."""
    return {n: c.get("trained_on") or [] for n, c in datasets_config().items()}


def model_summary(d: RunData, model: str, seen: dict[str, list[str]]) -> dict:
    acc = d.recs[(model, "accuracy")]
    s = M.summarize(acc)
    clean = [float(bool(r["correct"])) for r in acc if not seen.get(r["dataset"])]
    clean_acc = M.mean(clean)
    lat = [r["latency_ms"] for r in d.recs[(model, "latency")] if not r["error"]] or \
          [r["latency_ms"] for r in acc if not r["error"]]
    # only the probe sent right after load is cold (older runs sent "first" after accuracy)
    cold = [r for r in d.recs[(model, "first")] if r["variant"] == "cold" and not r["error"]]
    res = d.db.query("SELECT phase, gpu_mem_mb, proc_rss_mb FROM resource_samples "
                     "WHERE run_id=? AND model=?", (d.run_id, model))
    base = [r["gpu_mem_mb"] for r in res if r["phase"] == "baseline" and r["gpu_mem_mb"] is not None]
    gpu = [r["gpu_mem_mb"] for r in res if r["phase"] != "baseline" and r["gpu_mem_mb"] is not None]
    rss = [r["proc_rss_mb"] for r in res if r["proc_rss_mb"] is not None]
    # a docker-served model's own pid is the docker CLI: its RSS is not the model's
    if "docker run" in d.models[model]["spec"].get("serve", "") and \
            d.models[model]["provenance"].get("mem_source") != "container":
        rss = []
    tp = d.db.query("SELECT MAX(decisions_per_s) FROM throughput WHERE run_id=? AND model=?",
                    (d.run_id, model))[0][0]
    m = d.models[model]
    gpu_delta = (max(gpu) - (base[0] if base else 0)) if gpu else None
    order, rep = order_stats(d, model), repeat_stats(d, model)
    return {
        "model": model, "params": d.params(model), "status": m["status"],
        "served_model": m["provenance"].get("served_model"), **s,
        "accuracy_ci95": M.ci95(s["accuracy"], s["n"]),
        "clean_n": len(clean), "clean_acc": clean_acc,
        "clean_acc_ci95": M.ci95(clean_acc, len(clean)),
        "load_s": m["load_s"], "first_ms": cold[0]["latency_ms"] if cold else None,
        "ready_s": m["load_s"] + cold[0]["latency_ms"] / 1000
                   if cold and m["load_s"] is not None else None,
        "p50_ms": M.percentile(lat, .5), "p95_ms": M.percentile(lat, .95),
        "p99_ms": M.percentile(lat, .99),
        "gpu_mem_delta_mb": gpu_delta, "peak_proc_rss_mb": max(rss) if rss else None,
        "mem_mb": gpu_delta if gpu_delta is not None else (max(rss) if rss else None),
        "max_decisions_per_s": tp,
        **{f"order_{k}": v for k, v in order.items()},
        **{f"repeat_{k}": v for k, v in rep.items()},
    }


def order_stats(d: RunData, model: str) -> dict:
    by_case = defaultdict(dict)
    for r in d.recs[(model, "order")]:
        by_case[r["case_id"]][r["variant"]] = r
    for r in d.recs[(model, "accuracy")]:
        if r["case_id"] in by_case:
            by_case[r["case_id"]]["orig"] = r
    return M.order_robustness(by_case)


def repeat_stats(d: RunData, model: str) -> dict:
    by_case = defaultdict(list)
    for r in d.recs[(model, "repeat")]:
        by_case[r["case_id"]].append(r)
    for r in d.recs[(model, "accuracy")]:
        if r["case_id"] in by_case:
            by_case[r["case_id"]].append(r)
    return M.repeatability(by_case)


def breakdown(d: RunData, models, key: str, seen: dict | None = None) -> list[dict]:
    rows = []
    for model in models:
        groups = defaultdict(list)
        for r in d.recs[(model, "accuracy")]:
            groups[r[key]].append(r)
        for g, rs in sorted(groups.items()):
            s = M.summarize(rs)
            rows.append({"model": model, key: g,
                         **({"trained_on": " ".join(seen.get(g, []))} if seen is not None else {}),
                         "n": s["n"], "errors": s["errors"],
                         "accuracy": s["accuracy"], "brier": s["brier"], "ece": s["ece"],
                         "score_mae": s["score_mae"]})
    return rows


def highlights(d: RunData, models, bench: dict) -> dict[str, list[dict]]:
    """Case-level contrasts that say more than one leaderboard number."""
    answers = defaultdict(dict)   # case_id -> model -> record
    for model in models:
        for r in d.recs[(model, "accuracy")]:
            if r["pred_key"] is not None:
                answers[r["case_id"]][model] = r
    models = [m for m in models if any(m in by_m for by_m in answers.values())]
    kinds = {m: d.models[m]["spec"].get("kind") for m in models}
    jev = [m for m in models if kinds[m] == "cloud"]
    tiny = [m for m in models if (d.params(m) or 1e99) < bench["tiny_max_params"]]
    large = [m for m in models if (d.params(m) or 0) >= bench["large_min_params"]]
    # a contrast is only reported when both sides exist (empty list = none found)
    out = {}
    if tiny and large:
        out["tiny_correct_large_wrong"], out["large_correct_tiny_wrong"] = [], []
    if jev and len(jev) < len(models):
        out["jev_correct_all_locals_wrong"], out["local_consensus_correct_jev_wrong"] = [], []
    out["high_confidence_wrong"] = []

    def row(cid, **kw):
        c = d.cases[cid]
        return {"case_id": cid, "dataset": c.dataset, "type": c.type,
                "expected": c.expected_key, **kw}

    for cid, by_m in answers.items():
        right = {m for m, r in by_m.items() if r["correct"]}
        wrong = set(by_m) - right
        t_ok, l_bad = right & set(tiny), wrong & set(large)
        if t_ok and l_bad and not (right & set(large)):
            out["tiny_correct_large_wrong"].append(row(cid, tiny_correct=sorted(t_ok),
                                                       large_wrong=sorted(l_bad)))
        l_ok, t_bad = right & set(large), wrong & set(tiny)
        if l_ok and t_bad and not (right & set(tiny)):
            out["large_correct_tiny_wrong"].append(row(cid, large_correct=sorted(l_ok),
                                                       tiny_wrong=sorted(t_bad)))
        locals_ = [m for m in by_m if m not in jev]
        for j in jev:
            if j not in by_m or not locals_:
                continue
            local_right = [m for m in locals_ if by_m[m]["correct"]]
            if by_m[j]["correct"] and not local_right:
                out["jev_correct_all_locals_wrong"].append(row(cid, jev=j))
            if not by_m[j]["correct"] and len(local_right) > len(locals_) / 2:
                out["local_consensus_correct_jev_wrong"].append(
                    row(cid, jev=j, jev_answer=by_m[j]["pred_key"],
                        locals_correct=f"{len(local_right)}/{len(locals_)}"))
        for m, r in by_m.items():
            if not r["correct"] and (r["top_prob"] or 0) >= bench["high_confidence"]:
                out["high_confidence_wrong"].append(row(cid, model=m, answer=r["pred_key"],
                                                        top_prob=round(r["top_prob"], 4)))
    return out


def agreement(d: RunData, models) -> list[dict]:
    preds = {m: {r["case_id"]: r["pred_key"] for r in d.recs[(m, "accuracy")] if r["pred_key"]}
             for m in models}
    rows = []
    for a, b in combinations(models, 2):
        shared = preds[a].keys() & preds[b].keys()
        if shared:
            rows.append({"model_a": a, "model_b": b, "shared": len(shared),
                         "agreement": sum(preds[a][c] == preds[b][c] for c in shared) / len(shared)})
    return rows


def run_info(db: DB, run_id: str) -> dict:
    """Which code produced this report: the environment recorded when the run was last
    (re)started, plus the commit of the report generator itself."""
    row = db.query("SELECT created, environment FROM runs WHERE run_id=?", (run_id,))
    env = json.loads(row[0]["environment"] or "{}") if row else {}
    return {"run_id": run_id, "created": row[0]["created"] if row else None,
            "run_commit": env.get("repo_commit"), "run_dirty": env.get("repo_dirty"),
            "report_commit": git_commit(), "report_dirty": git_dirty(), "environment": env}


def build(db: DB, run_id: str) -> Path:
    bench = benchmark_config()
    d = RunData(db, run_id)
    out = REPORTS / run_id
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.csv"):   # empty tables aren't written; don't leave stale ones
        old.unlink()
    models = sorted(d.models, key=lambda m: (d.params(m) or 0, m))
    seen = exposure()
    summ = [model_summary(d, m, seen) for m in models]
    info = run_info(db, run_id)

    write_csv(out / "summary.csv", summ)
    (out / "summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    (out / "run.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    write_csv(out / "by_dataset.csv", breakdown(d, models, "dataset", seen))
    write_csv(out / "by_type.csv", breakdown(d, models, "type"))
    write_csv(out / "agreement.csv", agreement(d, models))
    calib = {}
    for m in models:
        rs = [r for r in d.recs[(m, "accuracy")] if r["pred_key"] and r["top_prob"] is not None]
        calib[m] = M.ece_bins([r["top_prob"] for r in rs], [bool(r["correct"]) for r in rs])
    (out / "calibration.json").write_text(json.dumps(calib, indent=2), encoding="utf-8")
    hl = highlights(d, models, bench)
    for kind, rows in hl.items():
        write_csv(out / f"highlight_{kind}.csv", rows)
    write_csv(out / "throughput.csv", [dict(r) for r in db.query(
        "SELECT * FROM throughput WHERE run_id=?", (run_id,))])
    # current errors only: predictions still unanswered + models whose latest load failed
    # (the errors table is an append-only log and keeps errors later fixed by a resume)
    write_csv(out / "errors.csv", [dict(r) for r in db.query(
        "SELECT model, case_id, mode AS stage, error AS message FROM predictions "
        "WHERE run_id=? AND error IS NOT NULL AND model IN (%s) UNION ALL "
        "SELECT model, NULL, 'load', error FROM models "
        "WHERE run_id=? AND status='load_failed' AND model IN (%s)"
        % ((",".join("?" * len(models)),) * 2), (run_id, *models, run_id, *models))])

    datasets_in_run = sorted({r["dataset"] for m in models for r in d.recs[(m, "accuracy")]})
    exp = {ds: seen.get(ds, []) for ds in datasets_in_run}
    (out / "summary.md").write_text(render_md(run_id, summ, hl, info, out, exp), encoding="utf-8")
    return out


def _commit(sha, dirty) -> str:
    return "unknown" if not sha else f"`{sha[:10]}`" + (" (dirty)" if dirty else "")


def render_md(run_id: str, summ: list[dict], hl: dict, info: dict, out: Path,
              exp: dict[str, list[str]]) -> str:
    counts = next((s for s in summ if s["n"]), summ[0] if summ else {})
    order_n = max((s.get("order_cases") or 0 for s in summ), default=0)
    rep_n = max((s.get("repeat_cases") or 0 for s in summ), default=0)
    # optional columns appear only when some model has data for them
    extra = [(h, k, fmt) for h, k, fmt in (("Ready s", "ready_s", "{:.1f}"),
                                          ("Cold first ms", "first_ms", "{:.0f}"),
                                          ("Max dec/s", "max_decisions_per_s", "{:.1f}"))
             if any(s[k] is not None for s in summ)]
    # the clean column only says something when some datasets are clean and some aren't
    show_clean = any(exp.values()) and not all(exp.values())
    L = [f"# Benchmark report — `{run_id}`", "",
         "Ground truth is dataset labels; Jev is a contestant, not a reference.", "",
         f"Run code: {_commit(info['run_commit'], info['run_dirty'])} · "
         f"report code: {_commit(info['report_commit'], info['report_dirty'])} "
         "(details in `run.json`).", "",
         "| Model | Params | Acc ±95% |" + (" Clean Acc ±95% |" if show_clean else "")
         + " Choice Acc | Noul Acc | Score MAE | Brier | ECE | p50 ms | p95 ms | Peak mem MB | Coverage | Status |",
         "|---|---:|---:|" + ("---:|" if show_clean else "") + "---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]

    def pm(p, ci):
        return "–" if p is None else f"{p:.3f} ±{ci:.3f}"
    for s in summ:
        acc = pm(s["accuracy"], s["accuracy_ci95"]) + " | " + \
            (pm(s["clean_acc"], s["clean_acc_ci95"]) + " | " if show_clean else "")
        L.append(f"| {s['model']} | {_params(s['params'])} | {acc}{_f(s['choice_acc'])} | "
                 f"{_f(s['noul_acc'])} | {_f(s['score_mae'], '{:.2f}')} | {_f(s['brier'])} | "
                 f"{_f(s['ece'])} | {_f(s['p50_ms'], '{:.0f}')} | {_f(s['p95_ms'], '{:.0f}')} | "
                 f"{_f(s['mem_mb'], '{:.0f}')} | "
                 f"{_f(s['coverage'], '{:.0%}')} | {s['status']} |")
    L += ["", f"Cases per model: {counts.get('n', 0)} (choice {counts.get('choice_n', 0)}, "
          f"noul {counts.get('noul_n', 0)}, score {counts.get('score_n', 0)}). "
          "Acc ±95%: overall accuracy with a normal-approximation 95% interval — models whose "
          "intervals overlap are not clearly different. "
          f"Score MAE rests on only {counts.get('score_n', 0)} score cases: treat as indicative. "
          "Accuracy counts errors/refusals as wrong; Coverage = share answered. "
          "Brier: multi-class (noul as 2-class). ECE: top-label confidence, 10 bins. "
          "Latency: sequential warm requests. Peak mem: peak GPU memory over baseline where "
          "the GPU reports it; otherwise (unified memory, e.g. GB10) peak RSS of the server's "
          "process tree, including runtime overhead. – = not measured.", "",
          "Training exposure (held-out splits are always used, but these are home turf for the "
          "listed upstreams): " + "; ".join(
              f"{ds} — {', '.join(u) if u else 'none known'}" for ds, u in exp.items()) + "."
          + (f" Clean Acc: accuracy on the datasets no contestant is known to train on "
             f"({', '.join(ds for ds, u in exp.items() if not u)})." if show_clean else "")
          + " Hosted Jev, Laya, JevK5 and the DeBERTa checkpoint don't publish training data.",
          "",
          "## Robustness", "",
          "| Model | Order consistency | Acc Δ (permuted−orig) | Conf Δ | Repeat agreement | Top-p std | NLL |"
          + "".join(f" {h} |" for h, _, _ in extra),
          "|---|---:|---:|---:|---:|---:|---:|" + "---:|" * len(extra)]
    for s in summ:
        L.append(f"| {s['model']} | {_f(s['order_order_consistency'])} | "
                 f"{_f(s['order_accuracy_delta'], '{:+.3f}')} | {_f(s['order_confidence_delta'])} | "
                 f"{_f(s['repeat_answer_agreement'])} | {_f(s['repeat_mean_top_prob_std'], '{:.4f}')} | "
                 f"{_f(s['nll'])} |" + "".join(f" {_f(s[k], fmt)} |" for _, k, fmt in extra))
    L += ["", f"Order: {order_n} choice cases, each also asked in reversed and seeded-shuffle orders. "
          f"Repeat: {rep_n} cases asked repeatedly. With these sample sizes, differences of a "
          "few points are noise. Order consistency 1.000 with Conf Δ 0 means the model scores "
          "each option as its own sequence, so it cannot see option order (by design, not a bug). "
          + ("Ready s: server launch until the first real decision is answered (not just a "
             "passing health check); Cold first ms: that first decision's latency."
             if any(k == "ready_s" for _, k, _ in extra) else
             "Load/cold-start timing was not captured for this run (it predates the cold probe).")]
    titles = {
        "tiny_correct_large_wrong": "Tiny model correct / every large model wrong",
        "large_correct_tiny_wrong": "Large model correct / every tiny model wrong",
        "jev_correct_all_locals_wrong": "Jev correct / all locals wrong",
        "local_consensus_correct_jev_wrong": "Local consensus correct / Jev wrong",
        "high_confidence_wrong": "High-confidence wrong answers",
    }
    L += ["", "## Highlights", ""]
    for kind, title in titles.items():
        if kind not in hl:   # one side of the contrast isn't in this run
            continue
        rows = hl[kind]
        L.append(f"### {title} ({len(rows)})")
        L.append("")
        for r in rows[:15]:
            extra = ", ".join(f"{k}={v}" for k, v in r.items()
                              if k not in ("case_id", "dataset", "type"))
            L.append(f"- `{r['case_id']}` ({r['type']}): {extra}")
        if len(rows) > 15:
            L.append(f"- … full list in `highlight_{kind}.csv`")
        L.append("")
    files = sorted(p.name for p in out.glob("*") if p.name != "summary.md")
    L += ["## Files", "", ", ".join(f"`{f}`" for f in files) + ".", ""]
    return "\n".join(L)
