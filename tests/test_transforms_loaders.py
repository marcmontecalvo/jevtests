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
