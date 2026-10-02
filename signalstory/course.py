"""Versioned, authored curriculum: executable models never create course answers."""

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def course():
    data = json.loads((ROOT / "content/course.json").read_text())
    missions = data["missions"]
    assert len(missions) == 22
    ids = [m["id"] for m in missions]
    assert len(ids) == len(set(ids))
    concept_ids = [c["id"] for m in missions for c in m["concepts"]]
    assert len(concept_ids) == len(set(concept_ids))
    for m in missions:
        assert len(m["questions"]) >= 5
        for q in m["questions"] + [c["check"] for c in m["concepts"]]:
            assert type(q["answer"]) is int and 0 <= q["answer"] < len(q["options"])
            assert q["explanation"]
    return data


def missions():
    return course()["missions"]


def mission(identity):
    return next(m for m in missions() if m["id"] == identity)


def concepts():
    return {c["id"]: c for m in missions() for c in m["concepts"]}


def sources_for(value):
    return [
        {"title": s.rsplit("/", 2)[-2].replace("_", " ").title(), "url": s} if isinstance(s, str) else s
        for s in value.get("sources", [])
    ]
