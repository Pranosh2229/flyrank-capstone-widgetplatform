"""A tiny deterministic stand-in for a geo provider, used only to prove the
fallback chain without depending on a real provider's live rate limit (see
EVIDENCE.md -- ipapi.co's shared free tier returned 429 from this
environment during manual testing, which is itself a real instance of "a
provider is down", but not a repeatable one to demonstrate against).

Mimics ipapi.co's response shape so GEO_PROVIDER_B_URL can point at this
instead of the real endpoint for a deterministic test run.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"country_name": "Mockland", "city": "Mock City", "error": False}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9999), Handler).serve_forever()
