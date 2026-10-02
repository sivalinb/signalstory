from . import otel


def run(level, plan, variant):
    scenario = "healthy" if not variant else "database_error"
    if level == 9:
        scenario = "n_plus_one"
    cfg = {
        k: plan[k]
        for k in (
            "service",
            "requests",
            "propagate",
            "sample_ratio",
            "redact",
            "batch_query",
            "label_policy",
        )
        if k in plan
    }
    data = otel.experiment(scenario=scenario, **cfg)
    if level == 0:
        passed = plan.get("signal") == "trace" and len(data["spans"]) >= 3
    elif level == 1:
        passed = cfg.get("propagate") is True and any(s["parent_id"] for s in data["spans"])
    elif level == 2:
        passed = (
            cfg.get("propagate") is True
            and all("traceparent" in c for c in data["carriers"])
            and len({s["trace_id"] for s in data["spans"]}) == data["requests"]
        )
    elif level == 3:
        passed = cfg.get("service") == "checkout" and {s["service"] for s in data["spans"]} == {
            "checkout",
            "payment",
            "database",
        }
    elif level == 4:
        counter = sum(m.get("value", 0) for m in data["metrics"] if m["name"] == "checkout.requests")
        hist = sum(m.get("count", 0) for m in data["metrics"] if m["name"] == "checkout.duration")
        passed = cfg.get("requests") == 5 and counter == 5 and hist == 5
    elif level == 5:
        failed = [s for s in data["spans"] if s["status"] == "ERROR" and s["events"]]
        passed = (
            plan.get("root_service") == "database"
            and cfg.get("propagate") is True
            and (not variant or any(s["service"] == "database" for s in failed))
        )
    elif level == 6:
        collector = otel.collector_config(
            plan.get("collector_redact", False),
            plan.get("collector_batch", False),
            plan.get("memory_limit_mib", 128),
        )
        otel.validate_collector(collector)
        passed = all(
            set(p["processors"]) == {"memory_limiter", "attributes/redact", "batch"}
            for p in collector["service"]["pipelines"].values()
        )
        data["collector"] = collector
    elif level == 7:
        passed = cfg.get("sample_ratio") == 0.2 and cfg.get("propagate") is True
    elif level == 8:
        points = [m for m in data["metrics"] if m["name"] == "checkout.requests"]
        passed = (
            cfg.get("redact") is True
            and cfg.get("label_policy") == "bounded"
            and all("user.email" not in log["attributes"] for log in data["logs"])
            and all("training.request_id" not in p["attributes"] for p in points)
        )
    elif level == 9:
        queries = [s for s in data["spans"] if s["service"] == "database"]
        passed = cfg.get("batch_query") is True and len(queries) == data["requests"]
    else:
        before = data
        if plan.get("remediation") == "restore_database":
            data = {"before": before, "after": otel.experiment(scenario="healthy", **cfg)}
        else:
            data = {"before": before, "after": before}
        after = data["after"]
        passed = (
            plan.get("remediation") == "restore_database"
            and cfg.get("propagate") is True
            and cfg.get("redact") is True
            and cfg.get("sample_ratio", 1.0) == 1
            and bool(after["spans"])
            and all(s["status"] != "ERROR" for s in after["spans"])
        )
    return {
        "passed": passed,
        "message": "Your SDK evidence satisfies the lab goal."
        if passed
        else "Inspect the trace, metric, or log evidence and adjust the experiment to satisfy the lab goal.",
        "data": data,
    }
