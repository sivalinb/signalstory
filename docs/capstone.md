# The unfamiliar checkout

Complete this after Mission 22 without opening its solution. Keep your observations and hypotheses separate. Save the JSON evidence and write a short explanation for a teammate.

1. Run `python -m scripts.http_demo` and `python -m scripts.http_demo --failure`. Name the services, identify the shared trace ID, and explain which span starts the failure and how it appears upstream.
2. Temporarily remove context injection in a private copy of `scripts/http_demo.py`. Predict the trace change before running it. Restore propagation, rerun, and point to the evidence that the repair worked.
3. In the PromQL lab, compare normal and incident traffic for the error fraction by service. Explain the denominator and labels. Check availability separately and explain why an absent series would require additional evidence.
4. Compare a per-service p95 query with the SQL example. Explain cumulative buckets, why rates happen before aggregation, why `le` survives, and why an exact raw-observation SQL percentile is not universally identical to a histogram estimate.
5. Write a handoff note with four parts: what the data shows; what you infer; what remains uncertain; what additional measurement you would collect next. Do not claim that a short fixture incident proves a monthly SLO breach.

You have demonstrated transfer when another person can follow your reasoning, reproduce your observations, and understand at least one limitation. This independent exercise is not automatically graded and does not award an additional verified badge.
