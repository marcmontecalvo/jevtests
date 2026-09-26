"""Build reports/<run>/ from the SQLite store: Markdown summary + CSV/JSON detail."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from harness import metrics as M
from harness.config import REPORTS, benchmark_config
from harness.db import DB
from harness.schema import Case, predicted_key


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
        self.models = {r["model"]: {**dict(r), "spec": json.loads(r["spec"] or "{}"),
                                    "provenance": json.loads(r["provenance"] or "{}")}
                       for r in db.query("SELECT * FROM models WHERE run_id=?", (run_id,))}
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


def model_summary(d: RunData, model: str) -> dict:
    acc = d.recs[(model, "accuracy")]
    s = M.summarize(acc)
    lat = [r["latency_ms"] for r in d.recs[(model, "latency")] if not r["error"]] or \
          [r["latency_ms"] for r in acc if not r["error"]]
    first = d.recs[(model, "first")]
    res = d.db.query("SELECT phase, gpu_mem_mb, proc_rss_mb FROM resource_samples "
                     "WHERE run_id=? AND model=?", (d.run_id, model))
    base = [r["gpu_mem_mb"] for r in res if r["phase"] == "baseline" and r["gpu_mem_mb"] is not None]
    gpu = [r["gpu_mem_mb"] for r in res if r["phase"] != "baseline" and r["gpu_mem_mb"] is not None]
    rss = [r["proc_rss_mb"] for r in res if r["proc_rss_mb"] is not None]
    tp = d.db.query("SELECT MAX(decisions_per_s) FROM throughput WHERE run_id=? AND model=?",
                    (d.run_id, model))[0][0]
    m = d.models[model]
    return {
        "model": model, "params": d.params(model), "status": m["status"],
        "served_model": m["provenance"].get("served_model"), **s,
        "load_s": m["load_s"], "first_ms": first[0]["latency_ms"] if first else None,
        "p50_ms": M.percentile(lat, .5), "p95_ms": M.percentile(lat, .95),
        "p99_ms": M.percentile(lat, .99),
        "gpu_mem_delta_mb": (max(gpu) - (base[0] if base else 0)) if gpu else None,
        "peak_proc_rss_mb": max(rss) if rss else None, "max_decisions_per_s": tp,
        **{f"order_{k}": v for k, v in order_stats(d, model).items() if k != "cases"},
        **{f"repeat_{k}": v for k, v in repeat_stats(d, model).items() if k != "cases"},
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


def breakdown(d: RunData, models, key: str) -> list[dict]:
    rows = []
    for model in models:
        groups = defaultdict(list)
        for r in d.recs[(model, "accuracy")]:
            groups[r[key]].append(r)
        for g, rs in sorted(groups.items()):
            s = M.summarize(rs)
            rows.append({"model": model, key: g, "n": s["n"], "errors": s["errors"],
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
    kinds = {m: d.models[m]["spec"].get("kind") for m in models}
    jev = [m for m in models if kinds[m] == "cloud"]
    tiny = [m for m in models if (d.params(m) or 1e99) < bench["tiny_max_params"]]
    large = [m for m in models if (d.params(m) or 0) >= bench["large_min_params"]]
    out = defaultdict(list)

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


def build(db: DB, run_id: str) -> Path:
    bench = benchmark_config()
    d = RunData(db, run_id)
    out = REPORTS / run_id
    out.mkdir(parents=True, exist_ok=True)
    models = sorted(d.models, key=lambda m: (d.params(m) or 0, m))
    summ = [model_summary(d, m) for m in models]

    write_csv(out / "summary.csv", summ)
    (out / "summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    write_csv(out / "by_dataset.csv", breakdown(d, models, "dataset"))
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
    write_csv(out / "errors.csv", [dict(r) for r in db.query(
        "SELECT model, case_id, stage, message FROM errors WHERE run_id=?", (run_id,))])

    (out / "summary.md").write_text(render_md(run_id, d, summ, hl), encoding="utf-8")
    return out


def render_md(run_id: str, d: RunData, summ: list[dict], hl: dict) -> str:
    L = [f"# Benchmark report — `{run_id}`", "",
         "Ground truth is dataset labels; Jev is a contestant, not a reference.", "",
         "| Model | Params | Choice Acc | Noul Acc | Score MAE | Brier | ECE | p50 ms | p95 ms | VRAM Δ MB | Status |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for s in summ:
        L.append(f"| {s['model']} | {_params(s['params'])} | {_f(s['choice_acc'])} | "
                 f"{_f(s['noul_acc'])} | {_f(s['score_mae'], '{:.2f}')} | {_f(s['brier'])} | "
                 f"{_f(s['ece'])} | {_f(s['p50_ms'], '{:.0f}')} | {_f(s['p95_ms'], '{:.0f}')} | "
                 f"{_f(s['gpu_mem_delta_mb'] or s['peak_proc_rss_mb'], '{:.0f}')} | {s['status']} |")
    L += ["", "Brier: multi-class (noul as 2-class). ECE: top-label confidence, 10 bins. "
          "Latency: sequential warm requests. VRAM Δ: peak GPU memory over baseline "
          "(falls back to server RSS where the GPU reports N/A, e.g. unified memory).", "",
          "## Robustness", "",
          "| Model | Order consistency | Acc Δ (permuted−orig) | Conf Δ | Repeat agreement | Top-p std | NLL | Load s | First ms | Max dec/s |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in summ:
        L.append(f"| {s['model']} | {_f(s['order_order_consistency'])} | "
                 f"{_f(s['order_accuracy_delta'], '{:+.3f}')} | {_f(s['order_confidence_delta'])} | "
                 f"{_f(s['repeat_answer_agreement'])} | {_f(s['repeat_mean_top_prob_std'], '{:.4f}')} | "
                 f"{_f(s['nll'])} | {_f(s['load_s'], '{:.1f}')} | {_f(s['first_ms'], '{:.0f}')} | "
                 f"{_f(s['max_decisions_per_s'], '{:.1f}')} |")
    titles = {
        "tiny_correct_large_wrong": "Tiny model correct / every large model wrong",
        "large_correct_tiny_wrong": "Large model correct / every tiny model wrong",
        "jev_correct_all_locals_wrong": "Jev correct / all locals wrong",
        "local_consensus_correct_jev_wrong": "Local consensus correct / Jev wrong",
        "high_confidence_wrong": "High-confidence wrong answers",
    }
    L += ["", "## Highlights", ""]
    for kind, title in titles.items():
        rows = hl.get(kind, [])
        L.append(f"### {title} ({len(rows)})")
        L.append("")
        for r in rows[:15]:
            extra = ", ".join(f"{k}={v}" for k, v in r.items()
                              if k not in ("case_id", "dataset", "type"))
            L.append(f"- `{r['case_id']}` ({r['type']}): {extra}")
        if len(rows) > 15:
            L.append(f"- … full list in `highlight_{kind}.csv`")
        L.append("")
    L += ["## Files", "",
          "`summary.csv/json` (also accuracy-vs-size and accuracy-vs-latency data), "
          "`by_dataset.csv`, `by_type.csv`, `calibration.json` (reliability bins), "
          "`agreement.csv` (model-vs-model), `throughput.csv`, `errors.csv`, `highlight_*.csv`.", ""]
    return "\n".join(L)
