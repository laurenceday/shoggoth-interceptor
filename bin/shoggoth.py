#!/usr/bin/env python3
"""Shoggoth Interceptor — board reader and loop state for the wildcat-finance product board.

The "ZenHub product board" is backed by GitHub issues in wildcat-finance/product.
The PAT in .env (GITHUB_READ_PAT) is read-only: it fetches issues and comments,
nothing else. GITHUB_ISSUE_REPLY_PAT is kept separate and is not loaded by this
program. All writes (branches, PRs) go through the operator's own `gh` auth,
never the read token.

Pipeline data (Icebox / Product Backlog / ToDo ...) lives in ZenHub, not GitHub.
If ZENHUB_API_KEY is present in .env, `fetch-pipelines` pulls the real mapping;
otherwise loops/pipelines.json holds a manually seeded map (source: "screenshot").

Subcommands:
  fetch                 Pull all open issues + comments into loops/board.json
  fetch-pipelines       Pull issue -> pipeline map from ZenHub (needs ZENHUB_API_KEY)
  roster [pipeline...]  Print candidates, optionally filtered to named pipelines
  show <n>              Print one issue in full (body + all comments)
  exclude <n> <reason>  Add an issue to the exclusion list after a loop completes
  excluded              Print the exclusion list
"""

import importlib.util
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "loops"
BOARD = STATE / "board.json"
EXCLUDED = STATE / "excluded.json"
PIPELINES = STATE / "pipelines.json"
LOOP_STATE = STATE / "loop.json"
README = ROOT / "README.md"
README_VIDEO_URL = "https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a"
REPO = "wildcat-finance/product"
API = "https://api.github.com"
ZENHUB_API = "https://api.zenhub.com/public/graphql"
WORKSPACE_ID = "660c35a2ab6252068500579b"  # wildcat.finance / Product Planning
ZALGO_SCRIPT = Path(__file__).resolve().parent / "zalgo.py"
README_INTRO = """The board is full. The loop is hungry.

Shoggoth reads the Wildcat ZenHub Product Planning board, ranks the open tickets, and takes them one at a time through a Fiat delivery. Deliverables stay local. The ticket goes on the exclusion list. Then it starts again.

The whole loop protocol, including the sharp edges, lives in CLAUDE.md."""


def env_var(name: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} not found in .env")


def github_read_pat() -> str:
    return env_var("GITHUB_READ_PAT")


def get(url: str):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {github_read_pat()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch():
    issues = []
    page = 1
    while True:
        batch = get(f"{API}/repos/{REPO}/issues?state=open&per_page=100&page={page}")
        if not batch:
            break
        issues.extend(i for i in batch if "pull_request" not in i)
        if len(batch) < 100:
            break
        page += 1

    slim = []
    for i in issues:
        entry = {
            "number": i["number"],
            "title": i["title"],
            "body": i["body"] or "",
            "labels": [l["name"] for l in i["labels"]],
            "author": i["user"]["login"],
            "assignees": [a["login"] for a in i["assignees"]],
            "milestone": i["milestone"]["title"] if i["milestone"] else None,
            "created_at": i["created_at"],
            "updated_at": i["updated_at"],
            "comments_count": i["comments"],
            "html_url": i["html_url"],
            "comments": [],
        }
        if i["comments"] > 0:
            for c in get(f"{API}/repos/{REPO}/issues/{i['number']}/comments?per_page=100"):
                entry["comments"].append({
                    "author": c["user"]["login"],
                    "created_at": c["created_at"],
                    "body": c["body"] or "",
                })
        slim.append(entry)
        print(f"\rfetched {len(slim)}/{len(issues)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    STATE.mkdir(exist_ok=True)
    BOARD.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "repo": REPO,
        "issues": slim,
    }, indent=1))
    print(f"wrote {BOARD} ({len(slim)} open issues)")


def zenhub(query: str, variables: dict):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(ZENHUB_API, data=payload, headers={
        "Authorization": f"Bearer {env_var('ZENHUB_API_KEY')}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        out = json.load(resp)
    if out.get("errors"):
        sys.exit(f"zenhub error: {out['errors']}")
    return out["data"]


def fetch_pipelines():
    pipes = zenhub("""
        query ($wid: ID!) {
          workspace(id: $wid) { pipelinesConnection(first: 20) { nodes { id name } } }
        }""", {"wid": WORKSPACE_ID})["workspace"]["pipelinesConnection"]["nodes"]

    mapping = {}   # "repo#number" -> pipeline name
    for p in pipes:
        cursor = None
        while True:
            page = zenhub("""
                query ($pid: ID!, $after: String) {
                  searchIssuesByPipeline(pipelineId: $pid, filters: {}, first: 100, after: $after) {
                    nodes { number repository { name } }
                    pageInfo { hasNextPage endCursor }
                  }
                }""", {"pid": p["id"], "after": cursor})["searchIssuesByPipeline"]
            for n in page["nodes"]:
                mapping[f"{n['repository']['name']}#{n['number']}"] = p["name"]
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
        print(f"  {p['name']}: {sum(1 for v in mapping.values() if v == p['name'])} issues", file=sys.stderr)

    STATE.mkdir(exist_ok=True)
    PIPELINES.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "zenhub",
        "workspace_id": WORKSPACE_ID,
        "pipelines": [p["name"] for p in pipes],
        "issues": mapping,
    }, indent=1))
    print(f"wrote {PIPELINES} ({len(mapping)} issues mapped)")


def load_pipelines():
    if PIPELINES.exists():
        return json.loads(PIPELINES.read_text())
    return None


def load_board():
    if not BOARD.exists():
        sys.exit("no loops/board.json — run `shoggoth.py fetch` first")
    return json.loads(BOARD.read_text())


def load_excluded():
    if EXCLUDED.exists():
        return json.loads(EXCLUDED.read_text())
    return []


def load_loop_state():
    if not LOOP_STATE.exists():
        return {"completed_loops": 0}
    try:
        state = json.loads(LOOP_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        sys.exit("invalid completion state")
    if not isinstance(state, dict):
        sys.exit("invalid completion state")
    completed = state.get("completed_loops")
    if isinstance(completed, bool) or not isinstance(completed, int) or completed < 0:
        sys.exit("invalid completion state")
    return state


def atomic_write(path: Path, text: str):
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def render_readme_intro(number: int):
    if not ZALGO_SCRIPT.is_file():
        sys.exit("text renderer unavailable")
    spec = importlib.util.spec_from_file_location("shoggoth_zalgo", ZALGO_SCRIPT)
    if spec is None or spec.loader is None:
        sys.exit("text renderer unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    content = README.read_text(encoding="utf-8")
    video = content.find(README_VIDEO_URL)
    section = content.find("\n## ")
    if (
        not content.startswith("# Shoggoth Interceptor\n")
        or video == -1
        or section == -1
        or video > section
    ):
        sys.exit("README structure not recognised")
    intro_start = video + len(README_VIDEO_URL)
    prefix = content[:intro_start].rstrip()
    rendered = module.zalgo(README_INTRO, min(number, 100))
    atomic_write(README, f"{prefix}\n\n{rendered}\n{content[section:]}")


def complete_loop(number: int):
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        sys.exit("invalid completion number")
    state = load_loop_state()
    completed = state["completed_loops"]
    if number == completed:
        return
    if number != completed + 1:
        sys.exit("completion out of sequence")

    render_readme_intro(number)
    STATE.mkdir(exist_ok=True)
    atomic_write(LOOP_STATE, json.dumps({
        "completed_loops": number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=1) + "\n")


def roster(pipeline_filter=None):
    board = load_board()
    skip = {e["number"] for e in load_excluded()}
    pl = load_pipelines()
    repo_short = REPO.split("/")[1]

    def pipe_of(num):
        if not pl:
            return "?"
        return pl["issues"].get(f"{repo_short}#{num}", "(unmapped)")

    rows = [i for i in board["issues"] if i["number"] not in skip]
    if pipeline_filter:
        wanted = {p.lower() for p in pipeline_filter}
        rows = [i for i in rows if pipe_of(i["number"]).lower() in wanted]
    rows.sort(key=lambda i: (pipe_of(i["number"]), -i["number"]))
    src = f", pipelines via {pl['source']} {pl['fetched_at']}" if pl else ", no pipeline data"
    print(f"board fetched {board['fetched_at']}{src} — {len(rows)} candidates ({len(skip)} excluded)\n")
    for i in rows:
        labels = ",".join(i["labels"]) or "-"
        print(f"#{i['number']:>4} | {pipe_of(i['number']):<17} | c:{i['comments_count']:>2} | {labels:<16} | {i['title']}")


def show(number: int):
    board = load_board()
    for i in board["issues"]:
        if i["number"] == number:
            print(f"#{i['number']}: {i['title']}")
            print(f"url: {i['html_url']}")
            print(f"author: {i['author']}  labels: {i['labels']}  created: {i['created_at']}  updated: {i['updated_at']}")
            print("\n--- body ---\n")
            print(i["body"] or "(empty)")
            for c in i["comments"]:
                print(f"\n--- comment by {c['author']} at {c['created_at']} ---\n")
                print(c["body"])
            return
    sys.exit(f"issue #{number} not in board.json (run fetch, or it may be closed)")


def exclude(number: int, reason: str):
    entries = load_excluded()
    if any(e["number"] == number for e in entries):
        print(f"#{number} already excluded")
        return
    entries.append({
        "number": number,
        "reason": reason,
        "excluded_at": datetime.now(timezone.utc).isoformat(),
    })
    STATE.mkdir(exist_ok=True)
    tmp = EXCLUDED.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, indent=1))
    tmp.replace(EXCLUDED)
    print(f"excluded #{number}: {reason}")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]
    if cmd == "fetch":
        fetch()
    elif cmd == "fetch-pipelines":
        fetch_pipelines()
    elif cmd == "roster":
        roster(args[1:] or None)
    elif cmd == "show":
        show(int(args[1]))
    elif cmd == "exclude":
        exclude(int(args[1]), " ".join(args[2:]) or "completed")
    elif cmd == "excluded":
        print(json.dumps(load_excluded(), indent=1))
    elif cmd == "complete-loop":
        complete_loop(int(args[1]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
