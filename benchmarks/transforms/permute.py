"""Deterministic option-order variants for Choice cases (order-robustness mode).

Only the order in which options are presented changes; keys, descriptions and the
expected answer are untouched.
"""
from __future__ import annotations

import dataclasses
import random

from harness.schema import Case


def reorder(case: Case, keys: list[str]) -> Case:
    return dataclasses.replace(case, criteria={k: case.criteria[k] for k in keys})


def variants(case: Case, seeds: list[int]) -> dict[str, Case]:
    """{'orig', 'rev', 'perm<seed>'...} -> Case. Non-choice cases only get 'orig'."""
    out = {"orig": case}
    if case.type != "choice" or len(case.criteria) < 2:
        return out
    keys = list(case.criteria)
    out["rev"] = reorder(case, keys[::-1])
    for s in seeds:
        shuffled = keys[:]
        random.Random(f"{s}:{case.id}").shuffle(shuffled)
        out[f"perm{s}"] = reorder(case, shuffled)
    return out
