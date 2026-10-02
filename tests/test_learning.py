import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from signalstory import labs
from signalstory.course import concepts, missions
from signalstory.progress import Progress


@pytest.fixture
def store(tmp_path):
    return Progress(tmp_path / "progress.sqlite3")


def test_complete_curriculum_and_evidence():
    assert len(missions()) == 22 and len(concepts()) == 70
    for m in missions():
        assert m["objective"] and m["lab"]["goal"] and len(m["questions"]) >= 5
        for c in m["concepts"]:
            assert c["sources"] and c["explanation"] and c["analogy"]
            assert len(c["animation"].get("steps", c["animation"].get("frames", []))) >= 4
            assert c["check"]["concept"] == c["id"]


def test_profiles_are_private_and_recoverable(store):
    alice, token = store.create("Alice")
    bob, _ = store.create("Bob")
    assert store.resume(token) == alice
    assert store.resume("unknown") is None
    ident = next(iter(concepts()))
    store.note(alice, ident, "My private explanation")
    assert store.summary(bob)["notes"] == []
    assert token not in json.dumps(store.report(alice))
    attempt = store.attempt(alice, missions()[0]["id"])
    with pytest.raises(PermissionError):
        store.grade(bob, attempt["id"], {}, "")
    with pytest.raises(PermissionError):
        store.note("unknown", ident, "test")


def test_early_repetition_does_not_fake_spaced_learning(store):
    profile, _ = store.create()
    ident = next(iter(concepts()))
    right = concepts()[ident]["check"]["answer"]
    first = store.answer(profile, ident, right, now=1000)
    repeated = store.answer(profile, ident, right, now=1001)
    assert first["repetitions"] == repeated["repetitions"] == 1
    assert repeated["due"] == first["due"] == 87400
    second = store.answer(profile, ident, right, now=first["due"])
    assert second["repetitions"] == 2 and second["due"] == 346600
    third = store.answer(profile, ident, right, now=second["due"])
    assert third["repetitions"] == 3
    assert store.summary(profile)["retained"] == 1
    wrong = (right + 1) % len(concepts()[ident]["check"]["options"])
    missed = store.answer(profile, ident, wrong, now=third["due"])
    assert missed["repetitions"] == 0 and missed["due"] == third["due"] + 600


def test_grade_is_server_owned_gated_and_idempotent(store, monkeypatch):
    profile, _ = store.create()
    first, second = missions()[:2]
    with pytest.raises(PermissionError):
        store.attempt(profile, second["id"])
    monkeypatch.setattr(labs, "grade", lambda m, p: {"passed": p == "evidence", "reports": []})
    attempt = store.attempt(profile, first["id"])
    q = {x["id"]: x for x in first["questions"]}
    answers = {ident: q[ident]["answer"] for ident in json.loads(attempt["questions"])}
    bad = store.grade(profile, attempt["id"], answers, "bad")
    assert bad["score"] == 100 and not bad["passed"] and store.summary(profile)["xp"] == 0
    attempt = store.attempt(profile, first["id"])
    answers = {ident: q[ident]["answer"] for ident in json.loads(attempt["questions"])}
    result = store.grade(profile, attempt["id"], answers, "evidence")
    assert result["passed"] and store.summary(profile)["xp"] == 100
    assert store.grade(profile, attempt["id"], {}, "bad") == result
    assert store.summary(profile)["xp"] == 100
    assert store.attempt(profile, second["id"])["mission"] == second["id"]


def test_ai_call_reservations_are_atomic(store):
    profile, _ = store.create()
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: store.reserve_call(profile, per_profile=4), range(20)))
    assert sum(results) == 4
    other, _ = store.create()
    assert not store.reserve_call(other, global_limit=4)


def test_external_plan_fields_rejected():
    m = next(m for m in missions() if m["kind"] == "otel")
    with pytest.raises(ValueError):
        labs.run(m, {"api_key": "invented"})
