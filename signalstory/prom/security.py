"""Enforce query and tool boundaries independently of the language model."""

import re

import sqlglot
from sqlglot import exp

MAX_QUERY_LENGTH = 3000
MAX_QUESTION_LENGTH = 2500
ALLOWED_TABLES = {"samples", "snapshot"}
ALLOWED_FUNCTIONS = {
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "COUNT",
    "ABS",
    "ROUND",
    "COALESCE",
    "NULLIF",
    "IF",
    "CASE",
    "LAG",
    "LEAD",
    "ROW_NUMBER",
    "RANK",
    "DENSE_RANK",
    "FIRST_VALUE",
    "LAST_VALUE",
    "CAST",
    "TRY_CAST",
    "PERCENTILE_CONT",
    "QUANTILE_CONT",
    "STDDEV",
    "STDDEV_POP",
    "SQRT",
    "POWER",
    "LOWER",
    "UPPER",
    "REGEXP_LIKE",
    "REGEXP_FULL_MATCH",
    "GREATEST",
    "LEAST",
    "EXTRACT",
    "AND",
    "OR",
    "NOT",
}


class RejectedQuery(ValueError):
    pass


def validate_sql(query: str) -> str:
    if not query.strip() or len(query) > MAX_QUERY_LENGTH:
        raise RejectedQuery("Enter a SELECT query shorter than 3,000 characters.")
    try:
        trees = sqlglot.parse(query, read="duckdb")
    except sqlglot.errors.ParseError as exc:
        raise RejectedQuery("SQL syntax could not be parsed. Check the example and try again.") from exc
    if len(trees) != 1 or not isinstance(trees[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise RejectedQuery("The learning sandbox accepts one read-only SELECT query.")
    tree = trees[0]
    if any(
        tree.find_all(
            exp.Command,
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Create,
            exp.Drop,
            exp.Copy,
            exp.Attach,
            exp.Into,
        )
    ):
        raise RejectedQuery("This operation is outside the learning sandbox.")
    if any(cte.args.get("recursive") for cte in tree.find_all(exp.With)):
        raise RejectedQuery("Recursive queries are disabled in this playground.")
    aliases = {cte.alias for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier) or table.name.lower() not in ALLOWED_TABLES | aliases:
            raise RejectedQuery("Only the samples and snapshot fixture tables are available.")
        if table.db or table.catalog:
            raise RejectedQuery("External databases are unavailable.")
    for func in tree.find_all(exp.Func):
        name = func.name.upper() if isinstance(func, exp.Anonymous) else func.sql_name().upper()
        if name not in ALLOWED_FUNCTIONS:
            raise RejectedQuery(f"Function {name} is not enabled in this learning sandbox.")
    return query


def validate_promql(query: str) -> str:
    if not query.strip() or len(query) > MAX_QUERY_LENGTH:
        raise RejectedQuery("Enter a PromQL expression shorter than 3,000 characters.")
    # The real Prometheus parser validates syntax. Bound every range/offset literal as well as
    # enforcing engine-side timeouts and sample limits (the latter also covers subqueries).
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(ms|[smhdwy])\b", query):
        seconds = (
            float(amount)
            * {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}[unit]
        )
        if seconds > 86400:
            raise RejectedQuery("Use time windows of one day or less in the learning lab.")
    return query


def validate_question(question: str) -> str:
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_LENGTH:
        raise ValueError("Ask a question between 1 and 2,500 characters.")
    return question


def plain_model_text(text: str) -> str:
    """Model text never becomes HTML or remote image/link markup."""
    text = re.sub(r"!\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])?", "", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}\[[^\]]+\]:.*$", "", text)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    return re.sub(r"<[^>]+>", "", text)
