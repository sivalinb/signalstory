import json

from . import otel_labs
from .prom.data import EVALUATION_TIMES
from .prom.engine import prom_query, results_equal


def run(mission, plan, variant=0):
    if variant not in (0, 1):
        raise ValueError("Unknown scenario")
    if mission["kind"] == "promql":
        if not isinstance(plan, str):
            raise ValueError("Enter a PromQL expression")
        return {"data": prom_query(plan, EVALUATION_TIMES[variant]), "kind": "promql"}
    if not isinstance(plan, dict) or len(json.dumps(plan)) > 8000:
        raise ValueError("Use a small experiment configuration")
    allowed = {f["name"] for f in mission["lab"]["fields"]}
    if set(plan) - allowed:
        raise ValueError("Only this mission’s experiment controls are accepted")
    return dict(otel_labs.run(mission["number"], plan, variant), kind="otel")


def grade(mission, plan):
    reports = []
    for variant in (0, 1):
        try:
            actual = run(mission, plan, variant)
            passed = (
                results_equal(
                    actual["data"], prom_query(mission["lab"]["solution"], EVALUATION_TIMES[variant])
                )
                if mission["kind"] == "promql"
                else actual["passed"]
            )
            reports.append(
                {
                    "scenario": variant + 1,
                    "passed": passed,
                    "message": "Evidence meets the goal."
                    if passed
                    else "Inspect the values, identities, and mission goal.",
                }
            )
        except (ValueError, RuntimeError, KeyError, TypeError, IndexError) as exc:
            reports.append({"scenario": variant + 1, "passed": False, "message": str(exc)[:350]})
    return {"passed": all(r["passed"] for r in reports), "reports": reports}
