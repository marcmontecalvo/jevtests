import pytest

from benchmarks.loaders import hf, jevbench
from benchmarks.transforms.permute import variants
from harness.schema import Case


def choice_case():
    return Case(id="c1", dataset="t", type="choice", state="s", question="q",
                criteria={"a": "A", "b": "B", "c": "C", "d": None}, expected="b")


def test_variants_are_deterministic_and_preserve_everything_but_order():
    v1, v2 = variants(choice_case(), [1, 2]), variants(choice_case(), [1, 2])
    assert set(v1) == {"orig", "rev", "perm1", "perm2"}
    assert list(v1["rev"].criteria) == ["d", "c", "b", "a"]
    assert list(v1["perm1"].criteria) == list(v2["perm1"].criteria)
    for v in v1.values():
        assert v.criteria == choice_case().criteria and v.expected == "b"


def test_non_choice_has_only_original():
    c = Case(id="n", dataset="t", type="noul", state="s", question="q", criteria=None, expected=True)
    assert list(variants(c, [1, 2])) == ["orig"]


def test_jevbench_rows_keep_wire_question_and_map_expected():
    noul = {"id": "p-0", "expected": "no", "family": "policy", "group": "g", "split": "public",
            "labels": ["no", "yes"], "state": "st",
            "question": {"type": "noul", "instructions": "Permitted?",
                         "criteria": {"true": "T", "false": "F"}}}
    c = jevbench.to_case(noul, "original")
    assert c.expected is False and c.id == "jevbench-p-0"
    assert c.jev_question() == noul["question"]
    score = {**noul, "id": "s-0", "expected": 1,
             "question": {"type": "score", "instructions": "How bad?", "criteria": ["x", "y", "z"]}}
    assert jevbench.to_case(score, "hard").expected == 1


def test_hf_choice_and_noul_transforms():
    cfg = {"type": "choice", "source": "src", "split": "test", "text_field": "text",
           "label_field": "label", "label_names": ["neg", "pos"], "transform_version": 1,
           "instructions": "Sentiment?", "criteria": {"neg": "bad", "pos": "good"}}
    c = hf.to_case("sst2", cfg, 3, {"text": "great", "label": 1}, None)
    assert c.expected == "pos" and c.id == "sst2-00003" and c.metadata["original_label"] == 1
    ncfg = {"type": "noul", "source": "src", "split": "validation", "text_field": "passage",
            "question_field": "question", "label_field": "label", "transform_version": 1,
            "instructions_template": "Q: {question}?"}
    n = hf.to_case("boolq", ncfg, 0, {"passage": "p", "question": "is it?", "label": 0}, None)
    assert n.expected is False and n.question == "Q: is it?"


def test_hf_noul_true_label_and_paired_state():
    # HANS: label 0 = entailment -> expected True
    cfg = {"type": "noul", "source": "src", "split": "validation", "text_field": "premise",
           "question_field": "hypothesis", "label_field": "label", "true_label": 0,
           "transform_version": 1, "instructions_template": 'Must "{question}" hold?'}
    row = {"premise": "The cat sat.", "hypothesis": "A cat sat .", "label": 0}
    c = hf.to_case("hans", cfg, 0, row, None)
    assert c.expected is True and c.state == "The cat sat." and c.question == 'Must "A cat sat ." hold?'
    assert hf.to_case("hans", cfg, 1, {**row, "label": 1}, None).expected is False


def test_hf_score_levels_round_half_up():
    cfg = {"type": "score", "source": "src", "split": "test", "label_field": "score",
           "score_scale": 5, "state_fields": {"sentence_1": "s1", "sentence_2": "s2"},
           "levels": [str(i) for i in range(6)], "transform_version": 1, "instructions": "Similar?"}
    row = {"s1": "a", "s2": "b"}
    c = hf.to_case("stsb", cfg, 7, {**row, "score": 0.5}, None)       # 2.5 -> 3, not banker's 2
    assert c.type == "score" and c.expected == 3 and c.expected_key == "3"
    assert c.state == {"sentence_1": "a", "sentence_2": "b"} and c.criteria == cfg["levels"]
    assert hf.to_case("stsb", cfg, 8, {**row, "score": 0.0}, None).expected == 0
    assert hf.to_case("stsb", cfg, 9, {**row, "score": 1.0}, None).expected == 5
    with pytest.raises(ValueError):
        hf.to_case("stsb", cfg, 10, {**row, "score": 1.5}, None)


def test_hf_choice_descriptions_fill_only_named_options():
    cfg = {"type": "choice", "source": "src", "split": "test", "text_field": "text",
           "label_field": "intent", "transform_version": 1, "instructions": "Intent?",
           "descriptions": {"oos": "none of the others"}}
    c = hf.to_case("clinc150", cfg, 0, {"text": "hi", "intent": 1}, ["greeting", "oos"])
    assert c.criteria == {"greeting": None, "oos": "none of the others"} and c.expected == "oos"


def test_financial_phrasebank_parse_splits_on_last_at():
    from benchmarks.loaders import financial_phrasebank as fpb
    rows = fpb.parse("Profit rose to EUR 5 mn .@positive\nMail us @ x.com for info .@neutral\n\n")
    assert rows == [{"sentence": "Profit rose to EUR 5 mn .", "label": "positive"},
                    {"sentence": "Mail us @ x.com for info .", "label": "neutral"}]
    cfg = {"type": "choice", "source": "src", "split": "all", "text_field": "sentence",
           "label_field": "label", "label_names": ["negative", "neutral", "positive"],
           "transform_version": 1, "instructions": "Sentiment?"}
    assert hf.to_case("financial_phrasebank", cfg, 0, rows[0], None).expected == "positive"
