"""Small, deterministic synthetic service metrics shared by Prometheus and SQL."""

import csv
import math
from functools import lru_cache
from pathlib import Path

START = 1735689600  # 2025-01-01 00:00:00 UTC; intentionally fixed for reproducibility.
CALM_TIME = START + 1800
BURST_TIME = START + 5400
EVALUATION_TIMES = (CALM_TIME, BURST_TIME)
FIELDS = ["timestamp", "metric", "service", "instance", "environment", "status", "le", "team", "value"]


@lru_cache
def samples() -> tuple[dict, ...]:
    rows = []

    def add(ts, metric, value, service, instance="", status="", le="", team=""):
        rows.append(
            dict(
                timestamp=ts,
                metric=metric,
                service=service,
                instance=instance,
                environment="prod",
                status=status,
                le=le,
                team=team,
                value=float(value),
            )
        )

    for scenario, offset in enumerate((0, 3600)):
        multiplier = 1 + scenario * 2
        for step in range(61):
            ts = START + offset + step * 30
            for service, base, team in [("api", 10, "platform"), ("web", 6, "experience")]:
                add(ts, "service_info", 1, service, team=team)
                for n, instance in enumerate(("a", "b")):
                    active = base * multiplier + n * 3 + round(3 * math.sin(step / 6))
                    add(ts, "app_active_sessions", active, service, instance)
                    add(ts, "queue_depth", max(0, active - 4), service, instance)
                    add(
                        ts,
                        "up",
                        0 if scenario == 1 and service == "web" and instance == "b" else 1,
                        service,
                        instance,
                    )
                    # A real reset in api/b. Rates must be calculated before aggregation.
                    elapsed = step if not (service == "api" and instance == "b" and step >= 30) else step - 30
                    requests = (base + n) * multiplier * (elapsed * 30 + 10)
                    errors = requests * (0.08 if scenario else 0.01)
                    add(ts, "http_requests_total", requests - errors, service, instance, status="200")
                    add(ts, "http_requests_total", errors, service, instance, status="500")
                    # Classic histogram buckets are cumulative in le and counters in time.
                    total = (base + n) * multiplier * (step * 30 + 10)
                    fractions = (0.20, 0.55, 0.85, 0.98, 1.0) if scenario else (0.65, 0.88, 0.97, 0.995, 1.0)
                    for edge, fraction in zip(("0.1", "0.25", "0.5", "1.0", "+Inf"), fractions):
                        add(
                            ts,
                            "http_request_duration_seconds_bucket",
                            total * fraction,
                            service,
                            instance,
                            le=edge,
                        )
                    add(ts, "http_request_duration_seconds_count", total, service, instance)
                    add(
                        ts,
                        "http_request_duration_seconds_sum",
                        total * (0.32 if scenario else 0.12),
                        service,
                        instance,
                    )
    return tuple(rows)


def export_csv(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(samples())


def openmetrics(path: Path):
    # promtool's backfill input uses seconds, not exposition-format milliseconds.
    grouped = {}
    for row in samples():
        grouped.setdefault(row["metric"], []).append(row)
    with path.open("w") as file:
        for metric, records in grouped.items():
            kind = "counter" if metric.endswith(("_total", "_count", "_sum", "_bucket")) else "gauge"
            file.write(f"# TYPE {metric} {kind}\n")
            for row in records:
                labels = ",".join(f'{k}="{row[k]}"' for k in FIELDS[2:-1] if row[k] != "")
                file.write(f"{metric}{{{labels}}} {row['value']} {row['timestamp']}\n")
        file.write("# EOF\n")
