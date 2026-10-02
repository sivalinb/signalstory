"""Internal-only HTTP adapter; every query runs in a fresh, time-bounded subprocess."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from signalstory.prom.data import EVALUATION_TIMES
from signalstory.prom.engine import sql_query


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        payload = json.dumps(body, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.reply(200 if self.path == "/health" else 404, {"status": "ready"})

    def do_POST(self):
        if self.path != "/query":
            return self.reply(404, {"error": "Unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16000:
                raise ValueError("Request is too large or empty")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request.get("query"), str) or request.get("at") not in EVALUATION_TIMES:
                raise ValueError("Use a query and a supported fixture evaluation time")
            self.reply(200, sql_query(request["query"], request["at"]))
        except (ValueError, RuntimeError, KeyError) as exc:
            self.reply(400, {"error": str(exc)[:400]})

    def log_message(self, *_):
        pass  # Queries and learner content are not written to HTTP access logs.


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
