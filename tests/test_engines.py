import pytest

from signalstory import labs
from signalstory.course import missions
from signalstory.prom.data import EVALUATION_TIMES
from signalstory.prom.engine import prom_query, query_rows, ready, results_equal, sql_query


@pytest.mark.parametrize("m", missions(), ids=lambda m: m["id"])
def test_every_authored_solution_in_two_scenarios(m):
    if m["kind"] == "promql":
        assert ready(), "Run python -m scripts.engine_setup before the full test suite"
    assert labs.grade(m, m["lab"]["solution"])["passed"]


@pytest.mark.parametrize("m", [m for m in missions() if m["kind"] == "promql"], ids=lambda m: m["id"])
def test_all_sql_connections_are_executable(m):
    for at in EVALUATION_TIMES:
        answer = sql_query(m["lab"]["sql"], at)
        assert "columns" in answer and "rows" in answer


def test_equivalent_syntax_is_accepted_but_wrong_shape_is_not():
    correct = prom_query("sum by(service)(app_active_sessions)")
    assert results_equal(correct, prom_query("sum(app_active_sessions) by(service)"))
    assert not results_equal(correct, prom_query("23"))
    assert not results_equal(correct, prom_query("sum(app_active_sessions)"))


def test_counter_reset_and_incident_evidence():
    assert all(r["value"] >= 0 for r in query_rows(prom_query("rate(http_requests_total[20m])")))
    m = missions()[10]
    assert query_rows(prom_query(m["lab"]["solution"], EVALUATION_TIMES[0])) == []
    assert query_rows(prom_query(m["lab"]["solution"], EVALUATION_TIMES[1]))
    assert not labs.grade(m, "vector(0)")["passed"]


def test_sdk_propagation_redaction_and_remediation():
    m = missions()[13]
    data = labs.run(m, m["lab"]["solution"])["data"]
    assert len({s["trace_id"] for s in data["spans"]}) == 3
    assert all("traceparent" in carrier for carrier in data["carriers"])
    privacy = missions()[19]
    data = labs.run(privacy, privacy["lab"]["solution"])["data"]
    assert all("user.email" not in log["attributes"] for log in data["logs"])
    recovery = missions()[-1]
    data = labs.run(recovery, recovery["lab"]["solution"], 1)["data"]
    assert any(s["status"] == "ERROR" for s in data["before"]["spans"])
    assert all(s["status"] != "ERROR" for s in data["after"]["spans"])
