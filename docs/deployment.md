# Running and sharing SignalStory

The full product is a Python/Streamlit server. The GitHub Pages playground is a static, credential-free preview built from the same course and animation sources. It has no Python backend and awards no practical badges.

## Local or container deployment

`python3 scripts/bootstrap.py` starts the native app at localhost:8530 and fixture Prometheus at localhost:9108. `docker compose up --build` exposes only localhost:8530 and uses a persistent volume for progress. Back up `.runtime/progress.sqlite3` using SQLite's backup API; do not copy an active WAL database's main file alone.

To include optional Pinecone/Braintrust SDKs in Docker, build with `docker build --build-arg REQUIREMENTS=requirements-ai.txt -t signalstory .`. Inject provider secrets through your host's secret manager or an ignored environment file. Do not bake keys into images. Nebius/Gemini HTTP generation works with base dependencies; Pinecone and Braintrust require the optional SDK dependencies.

For a shared server, put the app behind HTTPS and a reverse proxy. Preserve Streamlit's default CORS/XSRF checks. Persist the progress directory; use one app instance per SQLite database and its global quota. Restrict learner access to that database and the Prometheus endpoint. Use a separate credential-free OS/container boundary for the SQL process if you expect hostile users. Add real authentication and account-level cost caps before granting wider access. Recovery codes are bearer credentials for one profile on one server.

## Publishing the playground

Run `python -m scripts.build_preview` whenever course or component code changes. Publish `docs/` using GitHub Pages, from `main /docs`. The static output contains curated public course content, copied teaching components, and illustrations. It never reads `.env`, `.runtime`, or personal notes.

To test locally: `python -m http.server 8531 --bind 127.0.0.1 --directory docs`. Notes are stored in browser local storage under per-concept keys. Browser storage can be cleared, so copy important explanations elsewhere.

The preview serves a lesson URL such as `#lesson=v2-2-2`; copying a lesson link preserves the chosen concept. No visitor analytics or tracking scripts are installed. GitHub repository traffic and learning-server event counts measure different things; neither by itself proves learning. Choose analytics and consent deliberately when planning the launch.
