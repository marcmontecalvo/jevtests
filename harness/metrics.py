"""Pure-python metrics. Inputs are per-case records:
   {"type", "expected_key", "pred_key", "probs": {key: p}, "top_prob", "correct", "abs_error"}
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

EPS = 1e-6
ECE_BINS = 10


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def brier(probs: dict, expected_key: str, keys: list[str] | None = None) -> float:
    """Multi-class Brier: sum_k (p_k - y_k)^2 over all option keys (missing p = 0)."""
    keys = keys or list(probs)
    if expected_key not in keys:
        keys = [*keys, expected_key]
    return sum((probs.get(k, 0.0) - (1.0 if k == expected_key else 0.0)) ** 2 for k in keys)


def nll(probs: dict, expected_key: str) -> float:
    return -math.log(max(probs.get(expected_key, 0.0), EPS))


def ece_bins(tops: list[float], corrects: list[bool], n_bins: int = ECE_BINS) -> list[dict]:
    """Reliability-diagram data: equal-width bins on top-label confidence."""
    bins = [{"lo": i / n_bins, "hi": (i + 1) / n_bins, "n": 0, "conf": 0.0, "acc": 0.0}
            for i in range(n_bins)]
    for p, c in zip(tops, corrects):
        b = bins[min(int(p * n_bins), n_bins - 1)]
        b["n"] += 1
        b["conf"] += p
        b["acc"] += float(c)
    for b in bins:
        if b["n"]:
            b["conf"] /= b["n"]
            b["acc"] /= b["n"]
    return bins


def ece(tops: list[float], corrects: list[bool], n_bins: int = ECE_BINS) -> float | None:
    n = len(tops)
    if not n:
        return None
    return sum(b["n"] / n * abs(b["acc"] - b["conf"]) for b in ece_bins(tops, corrects, n_bins))


def percentile(xs: list[float], q: float) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(records: list[dict]) -> dict:
    """Accuracy counts errors/refusals as wrong (so models can't skip hard cases);
    `coverage` says how many were answered. Calibration and MAE use answered records."""
    ok = [r for r in records if r.get("pred_key") is not None]
    by_type = defaultdict(list)
    for r in records:
        by_type[r["type"]].append(r)
    out = {"n": len(records), "answered": len(ok), "errors": len(records) - len(ok),
           "coverage": len(ok) / len(records) if records else None}
    for t in ("choice", "noul", "score"):
        rs = by_type.get(t, [])
        out[f"{t}_n"] = len(rs)
        out[f"{t}_acc"] = mean([float(bool(r.get("correct"))) for r in rs])
    errs = [r["abs_error"] for r in by_type.get("score", []) if r.get("abs_error") is not None]
    out["score_mae"] = mean(errs)
    out["score_rmse"] = math.sqrt(mean([e * e for e in errs])) if errs else None
    out["accuracy"] = mean([float(bool(r.get("correct"))) for r in records])
    with_probs = [r for r in ok if r.get("probs")]
    out["brier"] = mean([brier(r["probs"], r["expected_key"], r.get("keys")) for r in with_probs])
    out["nll"] = mean([nll(r["probs"], r["expected_key"]) for r in with_probs])
    tops = [r["top_prob"] for r in with_probs if r.get("top_prob") is not None]
    cors = [bool(r["correct"]) for r in with_probs if r.get("top_prob") is not None]
    out["ece"] = ece(tops, cors)
    return out


def order_robustness(by_case: dict[str, dict[str, dict]]) -> dict:
    """by_case[case_id][variant] = record. Needs 'orig' plus >=1 other variant."""
    consistent, acc_orig, acc_other, conf_delta = [], [], [], []
    for variants in by_case.values():
        if "orig" not in variants or len(variants) < 2:
            continue
        preds = {v["pred_key"] for v in variants.values()}
        consistent.append(float(len(preds) == 1 and None not in preds))
        o = variants["orig"]
        acc_orig.append(float(bool(o["correct"])))
        for name, v in variants.items():
            if name == "orig":
                continue
            acc_other.append(float(bool(v["correct"])))
            if o.get("top_prob") is not None and v.get("top_prob") is not None:
                conf_delta.append(abs(v["top_prob"] - o["top_prob"]))
    a0, a1 = mean(acc_orig), mean(acc_other)
    return {"cases": len(consistent), "order_consistency": mean(consistent),
            "accuracy_delta": None if a0 is None or a1 is None else a1 - a0,
            "confidence_delta": mean(conf_delta)}


def repeatability(by_case: dict[str, list[dict]]) -> dict:
    """by_case[case_id] = records from repeated identical requests."""
    agree, prob_std, fails, total = [], [], 0, 0
    for reps in by_case.values():
        total += len(reps)
        fails += sum(r.get("pred_key") is None for r in reps)
        answered = [r for r in reps if r.get("pred_key") is not None]
        if len(answered) < 2:
            continue
        agree.append(float(len({r["pred_key"] for r in answered}) == 1))
        tops = [r["top_prob"] for r in answered if r.get("top_prob") is not None]
        if len(tops) > 1:
            prob_std.append(statistics.pstdev(tops))
    return {"cases": len(agree), "answer_agreement": mean(agree),
            "mean_top_prob_std": mean(prob_std),
            "failure_rate": fails / total if total else None}
