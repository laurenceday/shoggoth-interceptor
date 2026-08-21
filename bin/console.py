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
import os
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

    def _pipeline_keys(self, issue):
        """Both spellings a pipeline map may hold for one issue."""
        short = issue["repository"].split("/", 1)[1]
        return (issue["key"], f"{short}#{issue['number']}")

    def _pipeline_of(self, issue, pipelines):
        if not pipelines:
            return None
        mapping = pipelines.get("issues", {})
        for key in self._pipeline_keys(issue):
            if key in mapping:
                return mapping[key]
        return None

    def _position_of(self, issue, pipelines):
        """Board rank within the pipeline, or None when the board has no say.

        Absent is not zero. An issue outside the ZenHub workspace, or in a
        repository that is not a configured source, has no rank at all, and
        writing it as 0 would sort it above the thing the board actually
        ranked first.
        """
        if not pipelines:
            return None
        positions = pipelines.get("positions", {})
        for key in self._pipeline_keys(issue):
            if key in positions:
                return positions[key]
        return None

    def roster(self):
        board = self._load("board.json")
        if board is None:
            return {"error": "no board.json; refresh first", "candidates": []}
        pipelines = self._load("pipelines.json")
        repositories = board.get("repositories") or [board.get("repo")]
        selection = self._selection()
        # One pass resolves both: a second loop over the same entries drifted
        # from this one immediately, missing the keyless single-repository form
        # that the fallback below exists to handle.
        skip = set()
        excluded_by_repository = {}
        for entry in self.excluded():
            if isinstance(entry.get("key"), str):
                key = entry["key"].lower()
            elif len(repositories) == 1 and isinstance(entry.get("number"), int):
                key = f"{repositories[0]}#{entry['number']}".lower()
            else:
                continue
            skip.add(key)
            if "#" in key:
                repo = key.rsplit("#", 1)[0]
                excluded_by_repository[repo] = excluded_by_repository.get(repo, 0) + 1
        in_flight = board.get("in_flight") or {}
        rows = []
        for raw_issue in board["issues"]:
            issue = self._normalise_issue(raw_issue, board)
            labels = {label.lower() for label in issue.get("labels", [])}
            if issue["key"] in skip:
                continue
            # Same rule the ranker applies: an issue an open pull request
            # already points at is somebody's work in progress.
            if in_flight.get(issue["key"].lower()):
                continue
            if selection["unassigned_only"] and issue.get("assignees"):
                continue
            if selection["include_labels"] and not labels.intersection(selection["include_labels"]):
                continue
            if labels.intersection(selection["exclude_labels"]):
                continue
            pipe = self._pipeline_of(issue, pipelines)
            rows.append({
                "position": self._position_of(issue, pipelines),
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
        # Board order first, then issue number. Sorting by title read as random
        # to anyone who had put the issues in a deliberate order: five tickets
        # ranked one to five came back 5, 2, 3, 1, 4. Unranked issues sort after
        # ranked ones rather than at position zero.
        rows.sort(key=lambda r: (
            r["repository"],
            0 if r["position"] is not None else 1,
            r["position"] if r["position"] is not None else 0,
            r["number"],
        ))
        return {
            "fetched_at": board["fetched_at"],
            "pipelines_fetched_at": pipelines["fetched_at"] if pipelines else None,
            "excluded_count": len(skip),
            # The repositories actually present among the candidates, not every
            # configured source: a source whose issues are all excluded or
            # assigned would otherwise offer a filter that selects nothing.
            "repositories": sorted({row["repository"] for row in rows}),
            # Every category present, so the filter can offer one for issues
            # the board says nothing about rather than hiding them.
            "pipelines": sorted({row["pipeline"] for row in rows if row["pipeline"]}),
            # Per repository as well as in total, because a filtered console
            # showing a count drawn from repositories it is hiding reports an
            # exclusion the reader cannot see or act on.
            "excluded_by_repository": excluded_by_repository,
            "in_flight_count": sum(1 for raw in board["issues"]
                                   if in_flight.get(self._normalise_issue(raw, board)["key"].lower())),
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
        """Ranking documents only.

        `deliverables/` also holds loop notes and briefs. Those stay on disk as
        the archive of what a loop decided, and the console does not show them:
        the panel exists to answer what was ranked, and a brief alongside a
        ranking reads as though it were one.
        """
        if not self.deliverables.is_dir():
            return []
        rankings = [path for path in self.deliverables.glob("*.md")
                    if "ranking" in path.stem.lower()]
        if not rankings:
            return []
        # The most recently written one, by modification time rather than by a
        # number parsed out of the name: `loop-10` sorts before `loop-2` as text
        # and `loop-1-ranking-scoped` has no number of its own to compare.
        latest = max(rankings, key=lambda path: path.stat().st_mtime)
        return [{"name": latest.name, "text": latest.read_text()}]

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


# How much of a run log the console carries per poll. Large enough to follow a
# loop's reasoning, small enough that polling every few seconds stays cheap.
LOG_TAIL_CHARS = 20000

# Runs are launched with `--output-format stream-json`, which emits one JSON
# event per line as the work happens rather than a single blob at exit. The
# envelopes are far larger than what they say, so only the tail is read and
# only the useful part of each event is passed on.
LOG_TAIL_BYTES = 400_000
STREAM_MAX_EVENTS = 300

# Field that carries the point of each tool call. Bash says what it ran, the
# file tools say what they touched; without this the console can only report
# that some tool was used.
TOOL_SUBJECT = {
    "Bash": "command", "Read": "file_path", "Write": "file_path",
    "Edit": "file_path", "NotebookEdit": "notebook_path", "Glob": "pattern",
    "Grep": "pattern", "WebFetch": "url", "WebSearch": "query",
    "Task": "description", "Agent": "description", "Skill": "skill",
}
STREAM_EVENT_TYPES = {"system", "assistant", "user", "result", "rate_limit_event"}


def read_tail(path: Path, limit: int):
    """Return the last `limit` bytes as text, the full size, and whether it cut.

    A long loop writes megabytes and the console polls every few seconds, so
    the whole file is never read. Whether it seeked is what tells the parser
    its first line is debris: a line cut mid-object cannot be told from a
    genuine non-JSON one by looking, because the run's own stderr is prose too.
    """
    size = path.stat().st_size
    cut = size > limit
    with open(path, "rb") as handle:
        if cut:
            handle.seek(size - limit)
        raw = handle.read()
    return raw.decode("utf-8", errors="replace"), size, cut


def _shorten(value, limit=220):
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def _tool_subject(name, params):
    if not isinstance(params, dict):
        return ""
    field = TOOL_SUBJECT.get(name)
    if field and params.get(field):
        return _shorten(params[field])
    if params.get("description"):
        return _shorten(params["description"])
    for value in params.values():
        if isinstance(value, (str, int, float)) and str(value).strip():
            return _shorten(value)
    return ""


def summarise_stream(text, first_line_cut=False):
    """Turn stream-json log text into display events, or None if it is not.

    Returns None for the plain-text logs written before runs streamed, so the
    caller can fall back to showing them raw rather than showing nothing.

    Lines that are not JSON are kept as `stderr` events. The run's stderr
    shares this file, so those lines are how a crash, a missing binary or a
    permission refusal reaches the console; dropping them would hide exactly
    the failures worth seeing.
    """
    lines = text.split("\n")
    if first_line_cut and lines:
        # Read from the middle of the file, so line one is half an object.
        lines = lines[1:]
    events = []
    structured = 0
    for index, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if not line.startswith("{"):
            events.append({"kind": "stderr", "text": _shorten(line, 400)})
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # The last line may still be mid-write, which is not a fault.
            if index != len(lines) - 1:
                events.append({"kind": "stderr", "text": _shorten(line, 400)})
            continue
        if not isinstance(event, dict) or event.get("type") not in STREAM_EVENT_TYPES:
            continue
        structured += 1
        events.extend(_describe(event))
    if not structured:
        return None
    return events


def _describe(event):
    """One stream event to zero or more display lines."""
    kind = event.get("type")
    subtype = event.get("subtype")
    # A nested tool id means a subagent is speaking, not the loop itself.
    nested = bool(event.get("parent_tool_use_id"))
    if kind == "system" and subtype == "init":
        return [{"kind": "init", "text": f"session on {event.get('model') or 'unknown model'}",
                 "detail": _shorten(event.get("cwd") or "")}]
    if kind == "system" and subtype in ("task_summary", "post_turn_summary"):
        detail = event.get("detail") or event.get("status_detail")
        return [{"kind": "note", "text": _shorten(detail), "nested": nested}] if detail else []
    if kind == "rate_limit_event":
        info = event.get("rate_limit_info") or {}
        status = info.get("status") or info.get("state")
        return [{"kind": "note", "text": f"rate limit: {_shorten(status)}"}] if status else []
    if kind == "assistant":
        out = []
        for block in (event.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                out.append({"kind": "tool", "text": block.get("name") or "tool",
                            "detail": _tool_subject(block.get("name"), block.get("input")),
                            "nested": nested})
            elif block.get("type") == "text" and block.get("text", "").strip():
                out.append({"kind": "text", "text": _shorten(block["text"], 1200),
                            "nested": nested})
        return out
    if kind == "user":
        # Only failures: a successful tool result repeats what the tool
        # already announced, and there is one for every call.
        out = []
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
                out.append({"kind": "error", "text": _shorten(block.get("content"), 600),
                            "nested": nested})
        return out
    if kind == "result":
        parts = []
        if event.get("num_turns") is not None:
            parts.append(f"{event['num_turns']} turns")
        if event.get("duration_ms") is not None:
            parts.append(f"{event['duration_ms'] / 1000:.0f}s")
        if event.get("total_cost_usd") is not None:
            parts.append(f"${event['total_cost_usd']:.2f}")
        failed = bool(event.get("is_error")) or subtype != "success"
        return [{"kind": "error" if failed else "result",
                 "text": _shorten(event.get("result") or subtype or "finished", 1200),
                 "detail": " \u00b7 ".join(parts)}]
    return []


def pid_alive(pid: int) -> bool:
    import os
    # Reap first. The console spawns runs and never waits on them, so a
    # finished run stays a zombie, and a zombie answers `kill -0` exactly like
    # a live process -- which read as "still running" and jammed both `start()`
    # and `stop()`. Collecting it here is what makes the answer true. The wait
    # status is dropped on purpose: the wrapper already records the run's own
    # exit code, and that record is the one the console reports.
    try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except ChildProcessError:
        # Not ours -- the console restarted and this run was orphaned to init,
        # which also means no zombie can be attributed to us. `kill -0` is
        # then the whole answer.
        pass
    except (OSError, ValueError):
        pass
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
        # The console never waits on this child and may restart while it runs,
        # so the run records its own exit status instead of being observed. The
        # status path arrives as $0 and the command as "$@", so neither is
        # interpolated into the script text; argv is fixed by start() anyway.
        # The trap is what makes a killed run reportable. Without it SIGTERM
        # reaches the shell before the final printf and the status is never
        # written, so a terminated run reads as `unknown` and is
        # indistinguishable from one whose console died.
        script = ('set +e; '
                  'trap \'code=$?; printf %s "$code" > "$0"; exit "$code"\' TERM INT; '
                  '"$@"; '
                  'printf %s "$?" > "$0"')
        wrapper = ["/bin/sh", "-c", script,
                   str(log_path.with_suffix(".status")), *argv]
        with open(log_path, "ab") as log:
            proc = subprocess.Popen(
                wrapper, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return proc.pid

    def _running(self):
        for pidfile in sorted(self.loops_dir.glob("*.pid")):
            try:
                pid = int(pidfile.read_text().strip())
            except ValueError:
                continue
            # A recorded status means the run is over, whatever the pid says.
            # The console never reaps its children, so a finished run leaves a
            # zombie that still answers `kill -0`, and reading only the pid
            # jammed `start()` on "still running" for as long as the console
            # stayed up. Same rule `list()` applies.
            if pidfile.with_suffix(".status").exists():
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
        # stream-json so the log fills as the work happens. The default text
        # format prints one blob at exit, which left the console showing "no
        # output yet" for the whole of a run. `--verbose` is required with it.
        argv = ["claude", "-p", LAUNCH_MODES[mode],
                "--permission-mode", "acceptEdits",
                "--output-format", "stream-json", "--verbose"]
        pid = self.spawn(argv, log_path)
        (self.loops_dir / f"{name}.pid").write_text(str(pid))
        print(f"launched {name} (pid {pid}) -> {log_path}", file=sys.stderr)
        return {"ok": True, "name": name, "pid": pid,
                "log": f".loops/runs/{name}.log"}

    def stop(self):
        """Terminate the run this console launched, and nothing else.

        The client names no pid. The only killable process is the one whose
        pidfile this launcher wrote and whose pid is still alive, so a request
        cannot reach anything else on the machine.

        The whole process group goes, not just the leader: `start_new_session`
        put the run in its own session, and signalling only the shell wrapper
        would leave the agent it spawned running with nothing watching it.
        """
        import signal
        import time
        running = self._running()
        if not running:
            return {"ok": False, "error": "no launch is running"}
        pid = running["pid"]
        # Only ever signal a group the run leads. `start_new_session` makes the
        # child a session and group leader, but not instantly: for a moment
        # after the spawn `getpgid` still reports the console's own group, and
        # signalling that would kill the console and everything beside it.
        # Leadership is the proof the group belongs to the run.
        group = None
        for _ in range(20):
            try:
                candidate = os.getpgid(pid)
            except ProcessLookupError:
                return {"ok": False, "error": f"launch {running['name']} is already gone"}
            except PermissionError as error:
                return {"ok": False, "error": f"cannot resolve process group: {error}"}
            if candidate == pid:
                group = candidate
                break
            time.sleep(0.05)
        if group is None:
            return {"ok": False,
                    "error": f"launch {running['name']} never led its own process "
                             "group; refusing to signal a group it may share"}
        status_path = self.loops_dir / f"{running['name']}.status"

        def signal_group():
            """Send SIGTERM to the run's group. True if it was there to take it.

            SIGTERM only. The wrapper traps it and records the exit status on
            the way out, so a terminated run reports as failed with a signal
            code rather than vanishing into `unknown`; SIGKILL would deny it
            that. The group and not the leader alone: the shell defers its
            trap until the foreground command returns, so signalling only the
            wrapper leaves both it and the agent running until the command
            ends on its own.
            """
            try:
                os.killpg(group, signal.SIGTERM)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                # A group holding nothing but the zombie leader refuses
                # signals on macOS. That is what a group that has already
                # taken the signal looks like, not a failure to deliver.
                return False

        def settled(deadline):
            while time.monotonic() < deadline:
                if status_path.exists() or not pid_alive(pid):
                    return True
                time.sleep(0.05)
            return status_path.exists()

        delivered = signal_group()
        if not settled(time.monotonic() + 2.0):
            # The trap is not installed instantly, and a signal landing between
            # exec and the trap takes the default action and leaves no status.
            # By now the trap is long installed, so try once more.
            delivered = signal_group() or delivered
            settled(time.monotonic() + 2.0)
        if not status_path.exists() and not pid_alive(pid):
            # The run died without recording anything. The trap is installed by
            # the first line of the wrapper but not instantly, and a signal
            # landing between exec and the trap takes SIGTERM's default action:
            # the shell dies before it can write, and the retry above finds
            # nothing left to signal. The console records it instead. 143 is
            # not a guess -- it is the wait status of a process terminated by
            # SIGTERM, which is exactly what happened, and without it a
            # deliberate kill would read as `unknown` and be indistinguishable
            # from a run whose console died under it.
            status_path.write_text(str(128 + int(signal.SIGTERM)))
        print(f"terminated {running['name']} (pid {pid})", file=sys.stderr)
        return {"ok": True, "name": running["name"], "pid": pid, "signal": "SIGTERM",
                "group": group, "delivered": delivered,
                "status_recorded": status_path.exists()}

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
            # Never the whole file: a streaming run writes megabytes and this
            # is polled every few seconds.
            raw, size, cut = read_tail(log_path, LOG_TAIL_BYTES)
            found = summarise_stream(raw, first_line_cut=cut)
            # `None` means a plain-text log from before runs streamed. Those
            # still have to render, so they keep the raw tail they always had.
            if found is None:
                events, tail = [], raw[-LOG_TAIL_CHARS:]
                shown = len(tail.encode("utf-8", errors="replace"))
                clipped = False
            else:
                events, tail = found[-STREAM_MAX_EVENTS:], ""
                shown = len(raw.encode("utf-8", errors="replace"))
                clipped = len(events) < len(found)
            exit_code = None
            status_path = log_path.with_suffix(".status")
            if status_path.exists():
                try:
                    exit_code = int(status_path.read_text().strip())
                except ValueError:
                    exit_code = None
            # A recorded status outranks a live-looking pid. The console never
            # waits on its children, so a finished run leaves a zombie whose
            # pid still answers `kill -0` and would otherwise read as running
            # for as long as the console stays up.
            if exit_code is not None:
                running = False
                outcome = "succeeded" if exit_code == 0 else "failed"
            else:
                running = bool(pid and pid_alive(pid))
                # `unknown` is its own answer, not a quiet success: a run
                # predating the status file, or one whose shell was killed
                # outright, leaves no evidence and is not drawn as though it
                # passed.
                outcome = "running" if running else "unknown"
            launches.append({
                "name": log_path.stem,
                "running": running,
                "outcome": outcome,
                "exit_code": exit_code,
                "size": size,
                # True whenever the console is showing less than the run
                # produced -- either the file outran the tail read, or the
                # events outran the cap.
                "truncated": size > shown or clipped,
                "log_tail": tail,
                "events": events,
                "streaming": found is not None,
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
        if path == "/api/stop-loop":
            return self._send_json(self.launcher.stop())
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
