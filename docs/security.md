# Data and tutor boundaries

API keys belong in server environment variables or an ignored `.env`. They never go to teaching components or GitHub Pages. The repository contains only empty credential placeholders. Prometheus and SQL child processes receive a clean environment, without the tutor's provider keys.

Progress uses randomly generated recovery codes. SQLite stores their SHA-256 identity, owned attempts, badges, reviews and notes. The browser holds the recovery code in local storage so refresh can resume. Treat it like a password. Shared-machine users should use a private browser profile; this is not a full account-authentication system.

The server selects assessment questions, computes scores, checks both lab scenarios and awards idempotent badges. The AI model has no grading, shell, browser, network-fetch or equipment-control tool. A restricted question pattern blocks common instruction-override/secret requests; this is not comprehensive prompt-injection protection. Course evidence is allowlisted by concept ID, structured model output is validated, and remote model image/HTML markup is stripped.

AI consent is visible at the question form. Generation sends the question and public excerpts to Nebius, or Gemini on fallback. Pinecone receives the retrieval question and stores public course excerpts. Braintrust receives a question hash and operational metadata, not the full question, answer or notebook. Hashes can still reveal predictable questions through guessing, so they are not anonymous identifiers.

SQL allows one parsed, read-only query, selected functions and only fixture tables. External data access/extensions are disabled; results and runtime are bounded. Subprocess/environment restrictions are not a hardened hostile-code sandbox. Prometheus enforces query timeout and sample limits. SDK plans use bounded, allowlisted controls. Public multi-tenant deployment needs stronger identity, isolation and cost controls than the local edition.
