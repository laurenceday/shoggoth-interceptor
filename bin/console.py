#!/usr/bin/env python3
"""Shoggoth operator console — a local, read-mostly window onto the loop state.

Serves the board roster, ticket detail, rankings, exclusions, and deliverables
as JSON over 127.0.0.1 only. Credentials are never read here; only
bin/shoggoth.py touches .env, and no endpoint serialises anything outside the
state/ and deliverables/ trees. Board text is returned as JSON strings and must
be rendered as text by any client, never as HTML.

Run: python3 bin/console.py [--port 8737]
"""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8737
DEFAULT_PIPELINES = ("Icebox", "Product Backlog")
REPO_SHORT = "product"


class Api:
    """Answers console queries from a state directory. No network, no secrets."""

    def __init__(self, root: Path):
        self.root = root
        self.state = root / "state"
        self.deliverables = root / "deliverables"

    def _load(self, name: str):
        path = self.state / name
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def health(self):
        import time
        ages = {}
        for name in ("board.json", "pipelines.json", "excluded.json"):
            path = self.state / name
            ages[name] = round(time.time() - path.stat().st_mtime) if path.exists() else None
        return {"ok": True, "state_age_seconds": ages}

    def excluded(self):
        return self._load("excluded.json") or []

    def _pipeline_of(self, number: int, pipelines) -> str:
        if not pipelines:
            return "(no pipeline data)"
        return pipelines["issues"].get(f"{REPO_SHORT}#{number}", "(unmapped)")

    def roster(self, wanted_pipelines=DEFAULT_PIPELINES):
        board = self._load("board.json")
        if board is None:
            return {"error": "no board.json; refresh first", "candidates": []}
        pipelines = self._load("pipelines.json")
        skip = {e["number"] for e in self.excluded()}
        wanted = {p.lower() for p in wanted_pipelines} if wanted_pipelines else None
        rows = []
        for issue in board["issues"]:
            if issue["number"] in skip:
                continue
            pipe = self._pipeline_of(issue["number"], pipelines)
            if wanted is not None and pipe.lower() not in wanted:
                continue
            rows.append({
                "number": issue["number"],
                "title": issue["title"],
                "labels": issue["labels"],
                "pipeline": pipe,
                "comments_count": issue["comments_count"],
                "updated_at": issue["updated_at"],
                "html_url": issue["html_url"],
            })
        rows.sort(key=lambda r: (r["pipeline"], -r["number"]))
        return {
            "fetched_at": board["fetched_at"],
            "pipelines_fetched_at": pipelines["fetched_at"] if pipelines else None,
            "filter": sorted(wanted) if wanted else None,
            "excluded_count": len(skip),
            "candidates": rows,
        }

    def issue(self, number: int):
        board = self._load("board.json")
        if board is None:
            return None
        for issue in board["issues"]:
            if issue["number"] == number:
                out = dict(issue)
                out["pipeline"] = self._pipeline_of(number, self._load("pipelines.json"))
                out["deliverables"] = self.deliverable_files(number)
                return out
        return None

    def deliverable_files(self, number: int):
        folder = self.deliverables / f"issue-{int(number)}"
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_file())

    def rankings(self):
        if not self.deliverables.is_dir():
            return []
        docs = []
        for path in sorted(self.deliverables.glob("*.md")):
            docs.append({"name": path.name, "text": path.read_text()})
        return docs


class Handler(BaseHTTPRequestHandler):
    server_version = "ShoggothConsole/1"
    api: Api = None  # set by serve()

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, indent=1).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        api = self.api
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._send_json(api.health())
        if path == "/api/roster":
            return self._send_json(api.roster())
        if path == "/api/rankings":
            return self._send_json(api.rankings())
        if path == "/api/excluded":
            return self._send_json(api.excluded())
        match = re.fullmatch(r"/api/issue/(\d{1,6})", path)
        if match:
            issue = api.issue(int(match.group(1)))
            if issue is None:
                return self._send_json({"error": "unknown issue"}, 404)
            return self._send_json(issue)
        match = re.fullmatch(r"/api/deliverables/(\d{1,6})", path)
        if match:
            return self._send_json(api.deliverable_files(int(match.group(1))))
        return self._send_json({"error": "not found"}, 404)


def serve(port: int = DEFAULT_PORT):
    Handler.api = Api(ROOT)
    server = ThreadingHTTPServer((BIND_HOST, port), Handler)
    print(f"shoggoth console on http://{BIND_HOST}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("bye", file=sys.stderr)


if __name__ == "__main__":
    port = DEFAULT_PORT
    args = sys.argv[1:]
    if args[:1] == ["--port"] and len(args) > 1:
        port = int(args[1])
    serve(port)
