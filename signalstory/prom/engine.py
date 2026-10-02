from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

import httpx

from signalstory.course import ROOT
from signalstory.prom.data import CALM_TIME
from signalstory.prom.security import validate_promql, validate_sql


class EngineUnavailable(RuntimeError):
    pass


def prometheus_url() -> str:
    url = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9108").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
        raise EngineUnavailable("Invalid administrator-configured Prometheus endpoint.")
    return url


def ready() -> bool:
    try:
        return httpx.get(prometheus_url() + "/-/ready", timeout=1, trust_env=False).status_code == 200
    except (httpx.HTTPError, EngineUnavailable):
        return False


def start_local_engine() -> bool:
    """Start only our installed local fixture engine. Never download during an app request."""
    if ready():
        return True
    if prometheus_url() != "http://127.0.0.1:9108":
        return False
    binary = ROOT / ".tools/prometheus"
    data = ROOT / ".runtime/prometheus"
    if not binary.is_file() or not (data / ".seeded").exists():
        return False
    config = ROOT / ".runtime/prometheus.yml"
    config.write_text("global:\n  scrape_interval: 30s\nscrape_configs: []\n")
    with (ROOT / ".runtime/prometheus.log").open("ab") as log:
        process = subprocess.Popen(
            [
                str(binary),
                "--config.file=" + str(config),
                "--storage.tsdb.path=" + str(data),
                "--web.listen-address=127.0.0.1:9108",
                "--query.timeout=3s",
                "--query.max-samples=100000",
                "--query.max-concurrency=4",
                "--storage.tsdb.retention.time=36500d",
            ],
            stdout=log,
            stderr=log,
            start_new_session=True,
            env={"PATH": os.defpath},
        )
    (ROOT / ".runtime/prometheus.pid").write_text(str(process.pid))
    for _ in range(30):
        if ready():
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.1)
    return False


def prom_query(query: str, at: int = CALM_TIME, *, range_seconds: int = 0) -> dict:
    validate_promql(query)
    if range_seconds < 0 or range_seconds > 3600:
        raise ValueError("The chart window must be between 0 and 3,600 seconds.")
    parameters = {"query": query, "time": str(at), "timeout": "3s", "limit": "100"}
    endpoint = "/api/v1/query"
    if range_seconds:
        endpoint += "_range"
        parameters = {
            "query": query,
            "start": str(at - range_seconds),
            "end": str(at),
            "step": "30",
            "timeout": "3s",
            "limit": "100",
        }
    try:
        response = httpx.get(
            prometheus_url() + endpoint, params=parameters, timeout=5, follow_redirects=False, trust_env=False
        )
    except httpx.HTTPError as exc:
        raise EngineUnavailable("Start the fixture engine with python scripts/bootstrap.py.") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise EngineUnavailable("The query endpoint did not return a Prometheus response.") from exc
    if payload.get("status") != "success":
        raise ValueError(str(payload.get("error", "Prometheus could not evaluate that expression."))[:500])
    return payload["data"]


def query_rows(data: dict) -> list[dict]:
    kind, result = data["resultType"], data["result"]
    if kind in ("scalar", "string"):
        return [{"timestamp": result[0], "value": float(result[1]) if kind == "scalar" else result[1]}]
    rows = []
    for series in result:
        for timestamp, value in series.get("values", [series.get("value")]):
            rows.append({**series["metric"], "timestamp": timestamp, "value": float(value)})
    return rows


def results_equal(actual: dict, expected: dict) -> bool:
    """Compare type, complete label sets, timestamps, and values, independent of result order."""
    if actual["resultType"] != expected["resultType"]:
        return False

    def normalized(data):
        output = {}
        for row in query_rows(data):
            key = tuple(sorted((k, v) for k, v in row.items() if k != "value"))
            output[key] = row["value"]
        return output

    left, right = normalized(actual), normalized(expected)
    if left.keys() != right.keys():
        return False
    for key, value in left.items():
        other = right[key]
        if isinstance(value, (int, float)) and isinstance(other, (int, float)):
            if math.isnan(value) and math.isnan(other):
                continue
            if not math.isclose(value, other, rel_tol=1e-5, abs_tol=1e-7):
                return False
        elif value != other:
            return False
    return True


def sql_query(query: str, at: int = CALM_TIME) -> dict:
    validate_sql(query)
    endpoint = os.getenv("SQL_RUNNER_URL", "").rstrip("/")
    if endpoint:
        try:
            response = httpx.post(
                endpoint + "/query",
                json={"query": query, "at": at},
                timeout=8,
                trust_env=False,
                follow_redirects=False,
            )
            response.raise_for_status()
            answer = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EngineUnavailable("The SQL worker is unavailable. Check the SQL runner service.") from exc
    else:
        # A clean environment prevents API keys reaching the SQL worker. The Docker
        # version uses the same bounded subprocess; this is not an OS security boundary.
        try:
            result = subprocess.run(
                [sys.executable, "-m", "signalstory.prom.sql_worker"],
                input=json.dumps({"query": query, "at": at}),
                text=True,
                capture_output=True,
                timeout=6,
                cwd=ROOT,
                env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Query exceeded the six-second sandbox limit.") from exc
        if result.returncode:
            raise ValueError("The isolated SQL worker stopped. Simplify the query and try again.")
        answer = json.loads(result.stdout)
    if "error" in answer:
        raise ValueError(answer["error"])
    return answer
