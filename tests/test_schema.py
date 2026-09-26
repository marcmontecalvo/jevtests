import pytest

from harness.schema import Case, is_correct, normalize_answer


def case(type_, criteria, expected):
    return Case(id="c", dataset="t", type=type_, state="s", question="q",
                criteria=criteria, expected=expected)


def test_noul_normalizes_to_bool_and_two_way_probs():
    c = case("noul", None, True)
    pred, probs, conf, top = normalize_answer(c, {"type": "noul", "noul": 0.95})
    assert pred is True and probs == {"true": 0.95, "false": pytest.approx(0.05)}
    assert conf == top == 0.95
    assert is_correct(c, pred, probs) is True


def test_choice_keeps_provider_confidence_but_top_prob_is_max():
    c = case("choice", {"billing": None, "technical": None, "sales": None}, "billing")
    ans = {"type": "choice", "choice": "billing", "confidence": 0.81,
           "probabilities": {"billing": 0.88, "technical": 0.12, "sales": 0.0}}
    pred, probs, conf, top = normalize_answer(c, ans)
    assert pred == "billing" and conf == 0.81 and top == 0.88
    assert c.options == ["billing", "technical", "sales"]


def test_score_without_type_or_score_field_uses_expected_value():
    # mpuig/system-one omits `type`; some servers omit `score`
    c = case("score", ["Calm", "Frustrated", "Very angry"], 1)
    pred, probs, _, top = normalize_answer(c, {"probabilities": {"0": 0.0, "1": 0.95, "2": 0.05}})
    assert pred == pytest.approx(1.05) and top == 0.95
    assert is_correct(c, pred, probs) is True        # argmax level 1 == expected


def test_noul_expected_false_key():
    c = case("noul", None, False)
    assert c.expected_key == "false"
    assert is_correct(c, False, {"true": 0.2, "false": 0.8}) is True


def test_unknown_type_rejected():
    with pytest.raises(ValueError):
        case("rank", None, 1)
