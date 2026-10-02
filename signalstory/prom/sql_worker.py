"""Single-query subprocess. No application state, credentials, or filesystem tables."""

import json
import sys

import duckdb
import pyarrow as pa

from signalstory.prom.data import samples
from signalstory.prom.security import validate_sql


def execute(query: str, at: int) -> dict:
    validate_sql(query)
    con = duckdb.connect(
        ":memory:",
        config={
            "enable_external_access": False,
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
            "allow_unsigned_extensions": False,
            "memory_limit": "128MB",
            "threads": 1,
        },
    )
    try:
        con.register("_fixtures", pa.Table.from_pylist(list(samples())))
        con.execute("CREATE TABLE samples AS SELECT * FROM _fixtures")
        con.unregister("_fixtures")
        # Only the trusted integer is interpolated; it is never sourced from model text.
        con.execute(f"CREATE VIEW snapshot AS SELECT * FROM samples WHERE timestamp = {int(at)}")
        con.execute("SET lock_configuration = true")
        cursor = con.execute(query)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(201)
        return {"columns": columns, "rows": rows[:200], "truncated": len(rows) > 200}
    finally:
        con.close()


def main():
    try:
        request = json.loads(sys.stdin.read(5000))
        result = execute(request["query"], int(request["at"]))
    except Exception as exc:
        result = {"error": str(exc)[:400]}
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
