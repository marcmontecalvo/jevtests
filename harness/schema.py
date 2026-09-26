"""Internal normalized formats: benchmark cases and model results.

A Case carries the question in Jev wire form (type / instructions / criteria), so
any /v1/systemone server can be asked exactly what the dataset asks.

Expected-value conventions:
  choice -> option key (str)
  noul   -> bool
  score  -> level index (int) into the ordered `criteria` list
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

QUESTION_TYPES = ("choice", "noul", "score")


@dataclass(frozen=True)
class Case:
    id: str
    dataset: str
    type: str
    state: Any
    question: Any                 # Jev `instructions` (str | object | array)
    criteria: Any                 # choice: {option: desc|None}; score: [levels]; noul: {"true","false"}|None
    expected: Any
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in QUESTION_TYPES:
            raise ValueError(f"{self.id}: unknown type {self.type!r}")

    @property
    def options(self) -> list[str]:
        """Answer keys, in the order they are presented."""
        if self.type == "choice":
            return list(self.criteria)
        if self.type == "score":
            return [str(i) for i in range(len(self.criteria))]
        return ["true", "false"]

    @property
    def expected_key(self) -> str:
        """Expected answer as a probability-map key."""
        if self.type == "noul":
            return "true" if self.expected else "false"
        return str(self.expected)

    def jev_question(self) -> dict:
        q = {"type": self.type, "instructions": self.question}
        if self.criteria is not None:
            q["criteria"] = self.criteria
        return q

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Case":
        return cls(**d)


@dataclass
class Result:
    model: str
    case_id: str
    prediction: Any = None                # choice: str, noul: bool, score: float (expected value)
    probabilities: dict | None = None     # option key -> p
    confidence: float | None = None       # provider-reported if given, else top probability
    top_prob: float | None = None         # max(probabilities); used for calibration
    latency_ms: float | None = None
    error: str | None = None
    raw: Any = None                       # provider response, kept for debugging

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_answer(case: Case, answer: dict) -> tuple[Any, dict, float, float]:
    """Jev answer object -> (prediction, probabilities, confidence, top_prob).

    Tolerates servers that omit `type` (e.g. mpuig/system-one) or `confidence`.
    """
    if case.type == "noul":
        p = float(answer["noul"])
        probs = {"true": p, "false": 1.0 - p}
        top = max(p, 1.0 - p)
        return p >= 0.5, probs, top, top

    probs = {str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()}
    if not probs:
        raise ValueError("answer has no probabilities")
    top_key = max(probs, key=probs.get)
    top = probs[top_key]
    confidence = float(answer.get("confidence", top))

    if case.type == "choice":
        return answer.get("choice", top_key), probs, confidence, top

    score = answer.get("score")
    if score is None:
        score = sum(int(k) * v for k, v in probs.items())
    return float(score), probs, confidence, top


def predicted_key(case: Case, prediction: Any, probabilities: dict | None) -> str | None:
    """The discrete answer a prediction commits to (score -> argmax level)."""
    if prediction is None:
        return None
    if case.type == "noul":
        return "true" if prediction else "false"
    if case.type == "choice":
        return str(prediction)
    if probabilities:
        return max(probabilities, key=probabilities.get)
    return str(round(prediction))


def is_correct(case: Case, prediction: Any, probabilities: dict | None) -> bool | None:
    key = predicted_key(case, prediction, probabilities)
    return None if key is None else key == case.expected_key
