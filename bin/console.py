#!/usr/bin/env python3
"""Shoggoth operator console — a local, read-mostly window onto the loop state.

Serves the issue roster, detail, rankings, exclusions, and deliverables
as JSON over 127.0.0.1 only. Credentials are never read here; only
bin/shoggoth.py touches .env, and no endpoint serialises anything outside the
`.loops/` tree. Board text is returned as JSON strings and must be rendered as
text by any client, never as HTML.

Run: python3 bin/console.py [--port 8737]
"""

import json
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8737
MAX_REASON_LENGTH = 300
ISSUE_KEY_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}#[1-9][0-9]{0,8}$"
)


def host_allowed(host: str) -> bool:
    """Pin the Host header so a DNS-rebound origin cannot reach the API."""
    if not host:
        return False
    name = host.rsplit(":", 1)[0] if ":" in host else host
    return name in ("127.0.0.1", "localhost")


def run_argv(argv):
    """Default subprocess runner: fixed argv, no shell, bounded output."""
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    print(f"ran {argv[0]} {argv[1:]}: exit {proc.returncode}", file=sys.stderr)
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


class Api:
    """Answers console queries from a state directory. No network, no secrets."""

    def __init__(self, root: Path, runner=run_argv):
        self.root = root
        self.state = root / ".loops"
        self.deliverables = self.state / "deliverables"
        self.runner = runner
        self.shoggoth = root / "bin" / "shoggoth.py"
        self.archive_script = root / "bin" / "archive.sh"

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

    def _selection(self):
        path = self.root / "config" / "resolver.json"
        if not path.exists():
            return {"unassigned_only": True, "include_labels": set(), "exclude_labels": set()}
        if path.stat().st_size > 1_000_000:
            raise ValueError("resolver config exceeds size limit")
        config = json.loads(path.read_text(encoding="utf-8"))
        selection = config.get("selection", {})
        include = selection.get("include_labels", [])
        exclude = selection.get("exclude_labels", [])
        unassigned = selection.get("unassigned_only", True)
        if (not isinstance(unassigned, bool) or not isinstance(include, list)
                or not isinstance(exclude, list)
                or any(not isinstance(value, str) for value in include + exclude)):
            raise ValueError("invalid resolver selection")
        return {
            "unassigned_only": unassigned,
            "include_labels": {value.lower() for value in include},
            "exclude_labels": {value.lower() for value in exclude},
        }

    def _normalise_issue(self, issue, board):
        out = dict(issue)
        repository = out.get("repository") or board.get("repo")
        if not isinstance(repository, str) or "/" not in repository:
            raise ValueError("invalid issue repository")
        out["repository"] = repository.lower()
        out["key"] = out.get("key") or f"{out['repository']}#{int(out['number'])}"
        if not ISSUE_KEY_RE.fullmatch(out["key"]):
            raise ValueError("invalid issue key")
        return out

    def _pipeline_of(self, issue, pipelines):
        if not pipelines:
            return None
        short = issue["repository"].split("/", 1)[1]
        return (pipelines.get("issues", {}).get(issue["key"])
                or pipelines.get("issues", {}).get(f"{short}#{issue['number']}"))

    def roster(self):
        board = self._load("board.json")
        if board is None:
            return {"error": "no board.json; refresh first", "candidates": []}
        pipelines = self._load("pipelines.json")
        repositories = board.get("repositories") or [board.get("repo")]
        selection = self._selection()
        skip = set()
        for entry in self.excluded():
            if isinstance(entry.get("key"), str):
                skip.add(entry["key"].lower())
            elif len(repositories) == 1 and isinstance(entry.get("number"), int):
                skip.add(f"{repositories[0]}#{entry['number']}".lower())
        rows = []
        for raw_issue in board["issues"]:
            issue = self._normalise_issue(raw_issue, board)
            labels = {label.lower() for label in issue.get("labels", [])}
            if issue["key"] in skip:
                continue
            if selection["unassigned_only"] and issue.get("assignees"):
                continue
            if selection["include_labels"] and not labels.intersection(selection["include_labels"]):
                continue
            if labels.intersection(selection["exclude_labels"]):
                continue
            pipe = self._pipeline_of(issue, pipelines)
            rows.append({
                "key": issue["key"],
                "repository": issue["repository"],
                "number": issue["number"],
                "title": issue["title"],
                "labels": issue["labels"],
                "pipeline": pipe,
                "comments_count": issue["comments_count"],
                "updated_at": issue["updated_at"],
                "html_url": issue["html_url"],
            })
        rows.sort(key=lambda r: (r["repository"], r["title"].lower(), r["number"]))
        return {
            "fetched_at": board["fetched_at"],
            "pipelines_fetched_at": pipelines["fetched_at"] if pipelines else None,
            "excluded_count": len(skip),
            "candidates": rows,
        }

    def issue(self, key):
        if not isinstance(key, str) or not ISSUE_KEY_RE.fullmatch(key):
            return None
        board = self._load("board.json")
        if board is None:
            return None
        for raw_issue in board["issues"]:
            issue = self._normalise_issue(raw_issue, board)
            if issue["key"] == key.lower():
                out = dict(issue)
                out["pipeline"] = self._pipeline_of(issue, self._load("pipelines.json"))
                out["deliverables"] = self.deliverable_files(key)
                return out
        return None

    def deliverable_files(self, key):
        if not isinstance(key, str) or not ISSUE_KEY_RE.fullmatch(key):
            raise ValueError("invalid issue key")
        repository, number = key.rsplit("#", 1)
        canonical = "issue-" + re.sub(r"[^a-z0-9.-]+", "-", repository.lower()) + f"-{number}"
        folder = self.deliverables / canonical
        if not folder.is_dir():
            legacy = self.deliverables / f"issue-{number}"
            folder = legacy if legacy.is_dir() else folder
        if not folder.is_dir() or not folder.resolve().is_relative_to(self.deliverables.resolve()):
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_file())

    def rankings(self):
        if not self.deliverables.is_dir():
            return []
        docs = []
        for path in sorted(self.deliverables.glob("*.md")):
            docs.append({"name": path.name, "text": path.read_text()})
        return docs

    # --- mutations: fixed argv only, validated input only ---

    def refresh(self):
        code, output = self.runner([sys.executable, str(self.shoggoth), "fetch"])
        results = [{"command": "fetch", "exit": code, "output": output}]
        return {"ok": all(r["exit"] == 0 for r in results), "results": results}

    def exclude(self, key, reason):
        if not isinstance(key, str) or not ISSUE_KEY_RE.fullmatch(key):
            return {"ok": False, "error": "issue must be owner/repo#number"}
        if not isinstance(reason, str) or not reason.strip():
            return {"ok": False, "error": "reason required"}
        if len(reason) > MAX_REASON_LENGTH:
            return {"ok": False, "error": f"reason longer than {MAX_REASON_LENGTH} chars"}
        code, output = self.runner(
            [sys.executable, str(self.shoggoth), "exclude", key, reason.strip()])
        return {"ok": code == 0, "exit": code, "output": output}

    def archive(self):
        code, output = self.runner([str(self.archive_script)])
        return {"ok": code == 0, "exit": code, "output": output}


SMOKE_PROMPT = (
    "This is a Shoggoth Interceptor launch smoke test. Do not use any tools. "
    "Reply with exactly SHOGGOTH-SMOKE-OK and nothing else."
)
LOOP_PROMPT = (
    "Run one Shoggoth Interceptor loop for the repositories in config/resolver.json. "
    "Follow CLAUDE.md in this repository exactly: refresh GitHub intake, rank "
    "the eligible candidates, record the ranking in .loops/deliverables/, "
    "run the /hexaemeron:fiat delivery on the top pick with stacked PRs left "
    "open for review, write the deliverables summary, exclude the ticket, "
    "and run bin/archive.sh. Then stop."
)
LAUNCH_MODES = {"smoke": SMOKE_PROMPT, "loop": LOOP_PROMPT}


def pid_alive(pid: int) -> bool:
    import os
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, ValueError):
        return False


class Launcher:
    """Spawns detached headless Claude Code sessions with fixed prompts.

    Only the two hard-coded prompts above are ever launched; no request data
    reaches the argv. One launch at a time: a live pidfile refuses the next.
    """

    def __init__(self, root: Path, spawn=None):
        self.loops_dir = root / ".loops" / "runs"
        self.spawn = spawn or self._spawn_detached

    def _spawn_detached(self, argv, log_path: Path) -> int:
        import subprocess
        with open(log_path, "ab") as log:
            proc = subprocess.Popen(
                argv, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return proc.pid

    def _running(self):
        for pidfile in sorted(self.loops_dir.glob("*.pid")):
            try:
                pid = int(pidfile.read_text().strip())
            except ValueError:
                continue
            if pid_alive(pid):
                return {"name": pidfile.stem, "pid": pid}
        return None

    def start(self, mode):
        if mode not in LAUNCH_MODES:
            return {"ok": False, "error": "mode must be 'smoke' or 'loop'"}
        running = self._running()
        if running:
            return {"ok": False,
                    "error": f"launch {running['name']} is still running"}
        self.loops_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone
        name = f"{mode}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        log_path = self.loops_dir / f"{name}.log"
        argv = ["claude", "-p", LAUNCH_MODES[mode],
                "--permission-mode", "acceptEdits"]
        pid = self.spawn(argv, log_path)
        (self.loops_dir / f"{name}.pid").write_text(str(pid))
        print(f"launched {name} (pid {pid}) -> {log_path}", file=sys.stderr)
        return {"ok": True, "name": name, "pid": pid,
                "log": f".loops/runs/{name}.log"}

    def list(self):
        launches = []
        if not self.loops_dir.is_dir():
            return launches
        for log_path in sorted(self.loops_dir.glob("*.log"), reverse=True):
            pidfile = log_path.with_suffix(".pid")
            pid = None
            if pidfile.exists():
                try:
                    pid = int(pidfile.read_text().strip())
                except ValueError:
                    pid = None
            text = log_path.read_text(errors="replace")
            launches.append({
                "name": log_path.stem,
                "running": bool(pid and pid_alive(pid)),
                "log_tail": text[-2000:],
            })
        return launches


class Handler(BaseHTTPRequestHandler):
    server_version = "ShoggothConsole/1"
    api: Api = None  # set by serve()
    launcher: "Launcher" = None  # set by serve()

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, indent=1).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 10_000:
            return None
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return None

    def do_POST(self):
        if not host_allowed(self.headers.get("Host", "")):
            return self._send_json({"error": "bad host"}, 403)
        # The custom header forces a CORS preflight, which no endpoint answers,
        # so a hostile page in the same browser cannot fire these blind.
        if self.headers.get("X-Shoggoth") != "1":
            return self._send_json({"error": "missing X-Shoggoth header"}, 403)
        path = self.path.split("?", 1)[0]
        if path == "/api/refresh":
            return self._send_json(self.api.refresh())
        if path == "/api/archive":
            return self._send_json(self.api.archive())
        if path == "/api/start-loop":
            body = self._read_body()
            if body is None:
                return self._send_json({"error": "bad body"}, 400)
            result = self.launcher.start(body.get("mode", "loop"))
            return self._send_json(result, 200 if result["ok"] else 409)
        if path == "/api/exclude":
            body = self._read_body()
            if body is None:
                return self._send_json({"error": "bad body"}, 400)
            result = self.api.exclude(body.get("key"), body.get("reason"))
            return self._send_json(result, 200 if result["ok"] else 400)
        return self._send_json({"error": "not found"}, 404)

    def do_GET(self):
        if not host_allowed(self.headers.get("Host", "")):
            return self._send_json({"error": "bad host"}, 403)
        api = self.api
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            page = (ROOT / "bin" / "console.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
                             "connect-src 'self'; img-src 'self'")
            self.end_headers()
            self.wfile.write(page)
            return
        if path == "/console.js":
            body = (ROOT / "bin" / "console.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/assets/shoggoth.png":
            body = (ROOT / "assets" / "shoggoth.png").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/health":
            return self._send_json(api.health())
        if path == "/api/loops":
            return self._send_json(self.launcher.list())
        if path == "/api/roster":
            return self._send_json(api.roster())
        if path == "/api/rankings":
            return self._send_json(api.rankings())
        if path == "/api/excluded":
            return self._send_json(api.excluded())
        match = re.fullmatch(
            r"/api/issue/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})/(\d{1,9})",
            path,
        )
        if match:
            issue = api.issue(f"{match.group(1)}/{match.group(2)}#{match.group(3)}".lower())
            if issue is None:
                return self._send_json({"error": "unknown issue"}, 404)
            return self._send_json(issue)
        match = re.fullmatch(
            r"/api/deliverables/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})/(\d{1,9})",
            path,
        )
        if match:
            key = f"{match.group(1)}/{match.group(2)}#{match.group(3)}".lower()
            return self._send_json(api.deliverable_files(key))
        return self._send_json({"error": "not found"}, 404)


def serve(port: int = DEFAULT_PORT):
    Handler.api = Api(ROOT)
    Handler.launcher = Launcher(ROOT)
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
