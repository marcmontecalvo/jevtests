import pytest

from harness import metrics as M


def rec(type_, expected, pred, probs, correct, abs_error=None):
    return {"type": type_, "expected_key": expected, "pred_key": pred, "probs": probs,
            "top_prob": max(probs.values()) if probs else None, "correct": correct,
            "abs_error": abs_error, "keys": list(probs) if probs else None}


def test_brier_counts_missing_options_and_expected():
    assert M.brier({"a": 1.0, "b": 0.0}, "a") == 0
    assert M.brier({"a": 0.5, "b": 0.5}, "a") == pytest.approx(0.5)
    assert M.brier({"a": 1.0}, "b") == pytest.approx(2.0)   # expected key absent from probs


def test_nll_is_clipped():
    assert M.nll({"a": 1.0}, "a") == pytest.approx(0.0)
    assert M.nll({"a": 1.0}, "b") == pytest.approx(-__import__("math").log(M.EPS))


def test_ece_perfectly_calibrated_is_zero_and_overconfident_is_not():
    assert M.ece([0.75] * 4, [True, True, True, False]) == pytest.approx(0.0)
    assert M.ece([0.95] * 2, [False, False]) == pytest.approx(0.95)


def test_percentile_interpolates():
    assert M.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert M.percentile([10], 0.99) == 10
    assert M.percentile([], 0.5) is None


def test_summarize_mixed_types_and_errors():
    recs = [
        rec("choice", "a", "a", {"a": 0.9, "b": 0.1}, 1),
        rec("choice", "a", "b", {"a": 0.4, "b": 0.6}, 0),
        rec("noul", "true", "true", {"true": 0.8, "false": 0.2}, 1),
        rec("score", "1", "2", {"0": 0.0, "1": 0.4, "2": 0.6}, 0, abs_error=0.6),
        {"type": "choice", "pred_key": None},    # error
    ]
    s = M.summarize(recs)
    assert s["n"] == 5 and s["errors"] == 1 and s["coverage"] == 0.8
    # the errored choice counts as wrong: a model can't raise accuracy by refusing
    assert s["choice_acc"] == pytest.approx(1 / 3)
    assert s["noul_acc"] == 1.0 and s["score_acc"] == 0.0
    assert s["score_mae"] == pytest.approx(0.6) and s["score_rmse"] == pytest.approx(0.6)
    assert s["accuracy"] == pytest.approx(0.4)


def test_order_robustness():
    by_case = {
        "x": {"orig": rec("choice", "a", "a", {"a": .9, "b": .1}, 1),
              "rev": rec("choice", "a", "a", {"a": .7, "b": .3}, 1)},
        "y": {"orig": rec("choice", "a", "a", {"a": .6, "b": .4}, 1),
              "rev": rec("choice", "a", "b", {"a": .4, "b": .6}, 0)},
    }
    r = M.order_robustness(by_case)
    assert r["order_consistency"] == 0.5
    assert r["accuracy_delta"] == pytest.approx(-0.5)
    assert r["confidence_delta"] == pytest.approx(0.1)


def test_repeatability():
    a = rec("choice", "a", "a", {"a": .9, "b": .1}, 1)
    b = rec("choice", "a", "b", {"a": .4, "b": .6}, 0)
    r = M.repeatability({"x": [a, a, a], "y": [a, b, {"pred_key": None}]})
    assert r["answer_agreement"] == 0.5
    assert r["failure_rate"] == pytest.approx(1 / 6)


def test_ci95_half_width():
    assert M.ci95(0.5, 100) == pytest.approx(0.098)
    assert M.ci95(1.0, 50) == 0
    assert M.ci95(None, 10) is None and M.ci95(0.5, 0) is None
