#!/usr/bin/env python3
"""Shoggoth Interceptor — configurable GitHub issue intake and loop state.

The read credential fetches issues and comments only. Git and pull-request
writes use the operator's `gh` identity and the repository gate.

Subcommands:
  fetch                 Fetch open issues from every configured repository
  fetch-pipelines       Fetch optional ZenHub metadata when configured
  roster [pipeline...]  Print eligible, non-excluded candidates
  show <ref>            Print one issue; ref is owner/repo#number
  target <ref>          Print the configured implementation repository
  exclude <ref> <why>   Exclude one issue after its loop completes
  excluded              Print the exclusion list
  complete-loop <n>     Advance the local completion counter
"""

import importlib.util
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".loops"
BOARD = STATE / "board.json"
EXCLUDED = STATE / "excluded.json"
PIPELINES = STATE / "pipelines.json"
LOOP_STATE = STATE / "loop.json"
CONFIG = ROOT / "config" / "resolver.json"
README = ROOT / "README.md"
README_VIDEO_URL = "https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a"
REPO = "wildcat-finance/product"  # legacy state compatibility only
API = "https://api.github.com"
TOKEN_ENV_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
ZENHUB_API = "https://api.zenhub.com/public/graphql"
WORKSPACE_ID = "660c35a2ab6252068500579b"
ZALGO_SCRIPT = Path(__file__).resolve().parent / "zalgo.py"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 100
MAX_COMMENTS = 1_000
MAX_REASON_LENGTH = 1_000
HTTP_TIMEOUT = 30
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})$")
ISSUE_REF_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99})#([1-9][0-9]{0,8})$")
README_INTRO = """The issues are full. The loop is hungry.

Shoggoth reads configured GitHub repositories, ranks eligible issues, and takes them one at a time through a Fiat delivery. Deliverables stay local unless the repository policy permits a pull request. The issue goes on the exclusion list. Then it starts again.

The whole loop protocol, including the sharp edges, lives in CLAUDE.md."""


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def env_var(name: str) -> str:
    path = ROOT / ".env"
    try:
        if path.stat().st_size > 1_000_000:
            raise OSError
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        sys.exit(f"{name} not found in .env")
    for line in lines:
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    sys.exit(f"{name} not found in .env")


def github_read_pat() -> str:
    return env_var("GITHUB_READ_PAT")


def validate_repo(value, field="repository") -> str:
    if not isinstance(value, str) or not REPO_RE.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value.lower()


def _string_list(value, field):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"invalid {field}")
    return list(dict.fromkeys(item.lower() for item in value))


def validate_config(raw):
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("resolver config version must be 1")
    sources = raw.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("resolver config needs at least one source")
    clean_sources = []
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("invalid source")
        repo = validate_repo(source.get("repo"), "source repository")
        if repo in seen:
            raise ValueError("duplicate source repository")
        seen.add(repo)
        target = source.get("default_target")
        token_env = source.get("token_env")
        if token_env is not None and not TOKEN_ENV_RE.fullmatch(str(token_env)):
            raise ValueError("invalid source token_env")
        clean_sources.append({
            "token_env": token_env,
            "repo": repo,
            "default_target": validate_repo(target, "default target") if target else repo,
        })

    selection = raw.get("selection", {})
    if not isinstance(selection, dict):
        raise ValueError("invalid selection")
    unassigned = selection.get("unassigned_only", True)
    if not isinstance(unassigned, bool):
        raise ValueError("invalid unassigned_only")
    clean_selection = {
        "unassigned_only": unassigned,
        "include_labels": _string_list(selection.get("include_labels", []), "include_labels"),
        "exclude_labels": _string_list(selection.get("exclude_labels", []), "exclude_labels"),
    }

    routes = raw.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("invalid routes")
    clean_routes = []
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError("invalid route")
        source = validate_repo(route.get("source"), "route source")
        if source not in seen:
            raise ValueError("route source is not configured")
        labels = _string_list(route.get("labels_any", []), "route labels_any")
        if not labels:
            raise ValueError("route needs labels_any")
        clean_routes.append({
            "source": source,
            "target": validate_repo(route.get("target"), "route target"),
            "labels_any": labels,
        })

    zenhub = raw.get("zenhub")
    clean_zenhub = None
    if zenhub is not None:
        if not isinstance(zenhub, dict):
            raise ValueError("invalid zenhub config")
        workspace = zenhub.get("workspace_id")
        if not isinstance(workspace, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", workspace):
            raise ValueError("invalid zenhub workspace_id")
        clean_zenhub = {"workspace_id": workspace}
    return {
        "version": 1,
        "sources": clean_sources,
        "selection": clean_selection,
        "routes": clean_routes,
        "zenhub": clean_zenhub,
    }


def load_config(path=None):
    config_path = Path(path or os.environ.get("SHOGGOTH_CONFIG", CONFIG))
    try:
        if config_path.stat().st_size > 1_000_000:
            raise ValueError("resolver config exceeds size limit")
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read resolver config: {error}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid resolver config JSON: {error}") from None
    return validate_config(raw)


def issue_key(repo: str, number: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("invalid issue number")
    return f"{validate_repo(repo)}#{number}"


def parse_issue_ref(value: str):
    match = ISSUE_REF_RE.fullmatch(value)
    if not match:
        raise ValueError("issue ref must be owner/repo#number")
    repo = validate_repo(match.group(1))
    number = int(match.group(2))
    return repo, number, issue_key(repo, number)


def _read_json_response(response):
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("GitHub response exceeds size limit")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("GitHub returned invalid JSON") from None


def get(url: str, token: str | None = None):
    """One GitHub read. `token` overrides the default read PAT.

    A fine-grained PAT is scoped to a single resource owner, so a private
    repository under a different owner needs its own token rather than a wider
    grant on the existing one. The source names which variable holds it.
    """
    if not isinstance(url, str) or not url.startswith(f"{API}/"):
        raise ValueError("GitHub URL is not allowed")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token or github_read_pat()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
        return _read_json_response(response)


def _required_string(value, field, max_length=1_000_000):
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"invalid GitHub {field}")
    return value


def _issue_entry(repo, item, comments):
    if not isinstance(item, dict):
        raise ValueError("invalid GitHub issue")
    number = item.get("number")
    github_id = item.get("id")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("invalid GitHub issue number")
    if github_id is not None and (isinstance(github_id, bool) or not isinstance(github_id, int)):
        raise ValueError("invalid GitHub issue id")
    labels = item.get("labels", [])
    assignees = item.get("assignees", [])
    if (not isinstance(labels, list) or not isinstance(assignees, list)
            or any(not isinstance(label, dict) for label in labels)
            or any(not isinstance(user, dict) for user in assignees)):
        raise ValueError("invalid GitHub issue labels or assignees")
    label_names = [_required_string(label.get("name"), "label", 200) for label in labels]
    assignee_names = [_required_string(user.get("login"), "assignee", 200) for user in assignees]
    user = item.get("user")
    if not isinstance(user, dict):
        raise ValueError("invalid GitHub issue author")
    milestone = item.get("milestone")
    if milestone is not None and not isinstance(milestone, dict):
        raise ValueError("invalid GitHub issue milestone")
    return {
        "key": issue_key(repo, number),
        "repository": repo,
        "github_id": github_id,
        "number": number,
        "title": _required_string(item.get("title"), "title", 10_000),
        "body": _required_string(item.get("body") or "", "body"),
        "labels": label_names,
        "author": _required_string(user.get("login"), "author", 200),
        "assignees": assignee_names,
        "milestone": _required_string(milestone.get("title"), "milestone", 1_000) if milestone else None,
        "created_at": _required_string(item.get("created_at"), "created_at", 100),
        "updated_at": _required_string(item.get("updated_at"), "updated_at", 100),
        "comments_count": len(comments),
        "html_url": _required_string(item.get("html_url"), "html_url", 2_000),
        "comments": comments,
    }


def _fetch_comments(repo, number, expected, token=None):
    comments = []
    page = 1
    while len(comments) < expected and page <= MAX_PAGES:
        batch = get(f"{API}/repos/{repo}/issues/{number}/comments?per_page=100&page={page}",
                    token)
        if not isinstance(batch, list):
            raise ValueError("invalid GitHub comments response")
        for comment in batch:
            if not isinstance(comment, dict) or not isinstance(comment.get("user"), dict):
                raise ValueError("invalid GitHub comment")
            comments.append({
                "author": _required_string(comment["user"].get("login"), "comment author", 200),
                "created_at": _required_string(comment.get("created_at"), "comment created_at", 100),
                "body": _required_string(comment.get("body") or "", "comment body"),
            })
            if len(comments) > MAX_COMMENTS:
                raise ValueError("GitHub issue exceeds comment limit")
        if len(batch) < 100:
            break
        page += 1
    if len(comments) < expected:
        raise ValueError("GitHub comments response is incomplete")
    return comments


def fetch():
    config = load_config()
    entries = []
    in_flight = {}
    for source in config["sources"]:
        repo = source["repo"]
        token = env_var(source["token_env"]) if source.get("token_env") else None
        page = 1
        while page <= MAX_PAGES:
            batch = get(f"{API}/repos/{repo}/issues?state=open&per_page=100&page={page}", token)
            if not isinstance(batch, list):
                raise ValueError("invalid GitHub issues response")
            for item in batch:
                if "pull_request" in item:
                    # The issues endpoint returns pull requests too, and the
                    # walk used to drop them. They are the trail CLAUDE.md rule
                    # (c) asks about, and reading them here costs nothing: the
                    # bytes have already been fetched. A token scoped to Issues
                    # cannot reach /pulls at all, so this is also the only way
                    # to see them.
                    for number in _referenced_numbers(item):
                        in_flight.setdefault(f"{repo}#{number}".lower(), []).append(item["number"])
                    continue
                expected = item.get("comments", 0)
                if isinstance(expected, bool) or not isinstance(expected, int) or not 0 <= expected <= MAX_COMMENTS:
                    raise ValueError("invalid GitHub comment count")
                comments = _fetch_comments(repo, item["number"], expected, token) if expected else []
                entries.append(_issue_entry(repo, item, comments))
                print(f"\rfetched {len(entries)}", end="", file=sys.stderr)
            if len(batch) < 100:
                break
            page += 1
        if page > MAX_PAGES:
            raise ValueError(f"GitHub repository exceeds page limit: {repo}")
    print(file=sys.stderr)
    entries.sort(key=lambda item: item["key"])
    if len({item["key"] for item in entries}) != len(entries):
        raise ValueError("duplicate GitHub issue identity")
    atomic_write(BOARD, json.dumps({
        "version": 2,
        "complete": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "repositories": [source["repo"] for source in config["sources"]],
        # Issues an open pull request already points at, so ranking can skip
        # work someone else has in flight.
        "in_flight": {key: sorted(set(pulls)) for key, pulls in sorted(in_flight.items())},
        "issues": entries,
    }, indent=1) + "\n")
    print(f"wrote {BOARD} ({len(entries)} open issues across {len(config['sources'])} repositories)")


# CLAUDE.md rule (c) says to skip a ticket when its branch or pull request trail
# shows someone is already working on it. Only the assignee half was ever
# mechanised, so a Fiat run mid-flight went on offering its own issue: the
# branches are slugged from the title and carry no number, and GitHub's
# `closingIssuesReferences` stays empty for a step PR that references without
# closing. What is reliable is the reference itself.
ISSUE_REFERENCE_RE = re.compile(r"#(\d{1,9})\b")


def _referenced_numbers(pull) -> set:
    """Issue numbers an open pull request points at, from every trail it leaves."""
    numbers = set()
    for text in (pull.get("body") or "", pull.get("title") or ""):
        numbers.update(int(match) for match in ISSUE_REFERENCE_RE.findall(text))
    return numbers



def zenhub(query: str, variables: dict):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(ZENHUB_API, data=payload, headers={
        "Authorization": f"Bearer {env_var('ZENHUB_API_KEY')}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
        out = _read_json_response(response)
    if not isinstance(out, dict) or out.get("errors") or not isinstance(out.get("data"), dict):
        raise ValueError("invalid ZenHub response")
    return out["data"]


def fetch_pipelines():
    config = load_config()
    if not config["zenhub"]:
        sys.exit("ZenHub metadata is not configured; GitHub intake does not require it")
    workspace_id = config["zenhub"]["workspace_id"]
    pipes = zenhub("""
        query ($wid: ID!) {
          workspace(id: $wid) { pipelinesConnection(first: 20) { nodes { id name } } }
        }""", {"wid": workspace_id})["workspace"]["pipelinesConnection"]["nodes"]
    # Only a configured source gets a recorded rank. A repository that merely
    # shares the ZenHub workspace is mapped to its pipeline like any other and
    # carries no position, because nothing here acts on it.
    ranked_repos = {source["repo"].lower() for source in config["sources"]}
    mapping = {}
    positions = {}
    unranked = set()
    for pipeline in pipes:
        cursor = None
        # Board rank is the order searchIssuesByPipeline yields, so the index is
        # taken as the pages are walked. Nothing reconstructs it afterwards.
        rank = 0
        while True:
            page = zenhub("""
                query ($pid: ID!, $after: String) {
                  searchIssuesByPipeline(pipelineId: $pid, filters: {}, first: 100, after: $after) {
                    nodes { number repository { name ownerName } }
                    pageInfo { hasNextPage endCursor }
                  }
                }""", {"pid": pipeline["id"], "after": cursor})["searchIssuesByPipeline"]
            for node in page["nodes"]:
                repo = node["repository"]["name"]
                owner = node["repository"].get("ownerName") or ""
                key = f"{repo}#{node['number']}".lower()
                mapping[key] = pipeline["name"]
                qualified = f"{owner}/{repo}".lower()
                if qualified in ranked_repos:
                    positions[key] = rank
                    rank += 1
                else:
                    unranked.add(qualified)
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
    atomic_write(PIPELINES, json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "zenhub",
        "workspace_id": workspace_id,
        "pipelines": [pipeline["name"] for pipeline in pipes],
        "issues": mapping,
        "positions": positions,
    }, indent=1) + "\n")
    print(f"wrote {PIPELINES} ({len(mapping)} issues mapped, "
          f"{len(positions)} ranked)")
    if unranked:
        print(f"unranked, not a configured source: {', '.join(sorted(unranked))}")


def load_pipelines():
    if PIPELINES.exists():
        return json.loads(PIPELINES.read_text(encoding="utf-8"))
    return None


def _normalise_board(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("issues"), list):
        raise ValueError("invalid board state")
    if raw.get("version") == 2:
        if raw.get("complete") is not True:
            raise ValueError("incomplete board state")
        issues = raw["issues"]
    else:
        legacy_repo = validate_repo(raw.get("repo", REPO))
        issues = []
        for issue in raw["issues"]:
            if not isinstance(issue, dict):
                raise ValueError("invalid legacy issue state")
            item = dict(issue)
            item["repository"] = legacy_repo
            item["key"] = issue_key(legacy_repo, item.get("number"))
            item.setdefault("github_id", None)
            issues.append(item)
        raw = dict(raw)
        raw.update({"version": 2, "complete": True, "repositories": [legacy_repo], "issues": issues})
    keys = set()
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("invalid board issue")
        key = issue.get("key")
        repo = issue.get("repository")
        number = issue.get("number")
        if issue_key(repo, number) != key or key in keys:
            raise ValueError("invalid or duplicate issue identity")
        keys.add(key)
    return raw


def load_board():
    if not BOARD.exists():
        sys.exit("no .loops/board.json — run `shoggoth.py fetch` first")
    try:
        return _normalise_board(json.loads(BOARD.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        sys.exit(f"invalid board state: {error}")


def load_excluded():
    if not EXCLUDED.exists():
        return []
    try:
        entries = json.loads(EXCLUDED.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        sys.exit("invalid exclusion state")
    if not isinstance(entries, list):
        sys.exit("invalid exclusion state")
    return entries


def excluded_keys(board, entries=None):
    entries = load_excluded() if entries is None else entries
    repositories = board.get("repositories", [])
    keys = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid exclusion entry")
        if isinstance(entry.get("key"), str):
            parse_issue_ref(entry["key"])
            keys.add(entry["key"].lower())
        elif len(repositories) == 1 and isinstance(entry.get("number"), int):
            keys.add(issue_key(repositories[0], entry["number"]))
        else:
            raise ValueError("legacy exclusion is ambiguous across repositories")
    return keys


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
    if not content.startswith("# Shoggoth Interceptor\n") or video == -1 or section == -1 or video > section:
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
    atomic_write(LOOP_STATE, json.dumps({
        "completed_loops": number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=1) + "\n")


def pipeline_of(issue, pipelines):
    if not pipelines:
        return None
    keys = (issue["key"], f"{issue['repository'].split('/', 1)[1]}#{issue['number']}")
    for key in keys:
        if key.lower() in pipelines.get("issues", {}):
            return pipelines["issues"][key.lower()]
    return None


def is_eligible(issue, config, in_flight=None):
    selection = config["selection"]
    labels = {label.lower() for label in issue.get("labels", [])}
    if selection["unassigned_only"] and issue.get("assignees"):
        return False, "assigned"
    # CLAUDE.md rule (c): skip a ticket whose pull request trail shows somebody
    # is already on it. Assignment was the only half ever mechanised, so a run
    # in flight kept being offered its own issue.
    pulls = (in_flight or {}).get(issue["key"].lower())
    if pulls:
        return False, "in flight: PR " + ", ".join(f"#{n}" for n in pulls)
    if selection["include_labels"] and not labels.intersection(selection["include_labels"]):
        return False, "missing required label"
    if labels.intersection(selection["exclude_labels"]):
        return False, "excluded label"
    return True, "eligible"


def candidate_rows(board=None, config=None, pipeline_filter=None):
    board = board or load_board()
    config = config or load_config()
    skip = excluded_keys(board)
    pipelines = load_pipelines()
    wanted = {value.lower() for value in pipeline_filter} if pipeline_filter else None
    in_flight = board.get("in_flight") or {}
    rows = []
    for issue in board["issues"]:
        if issue["key"] in skip:
            continue
        eligible, reason = is_eligible(issue, config, in_flight)
        if not eligible:
            continue
        pipeline = pipeline_of(issue, pipelines)
        if wanted is not None and (pipeline or "").lower() not in wanted:
            continue
        row = dict(issue)
        row["pipeline"] = pipeline
        row["selection_reason"] = reason
        rows.append(row)
    rows.sort(key=lambda item: (item["repository"], item["title"].lower(), item["number"]))
    return rows


def roster(pipeline_filter=None):
    board = load_board()
    rows = candidate_rows(board, pipeline_filter=pipeline_filter)
    print(f"issues fetched {board['fetched_at']} — {len(rows)} candidates ({len(excluded_keys(board))} excluded)\n")
    for issue in rows:
        labels = ",".join(issue["labels"]) or "-"
        metadata = issue["pipeline"] or "github"
        print(f"{issue['key']:<45} | {metadata:<17} | c:{issue['comments_count']:>2} | {labels:<16} | {issue['title']}")


def find_issue(ref, board=None):
    board = board or load_board()
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        number = int(ref)
        matches = [issue for issue in board["issues"] if issue["number"] == number]
        if len(matches) != 1:
            raise ValueError("numeric issue reference is ambiguous; use owner/repo#number")
        return matches[0]
    _, _, key = parse_issue_ref(str(ref))
    for issue in board["issues"]:
        if issue["key"] == key:
            return issue
    raise ValueError(f"issue {key} not in board state")


def show(ref):
    try:
        issue = find_issue(ref)
    except ValueError as error:
        sys.exit(str(error))
    print(f"{issue['key']}: {issue['title']}")
    print(f"url: {issue['html_url']}")
    print(f"author: {issue['author']}  labels: {issue['labels']}  created: {issue['created_at']}  updated: {issue['updated_at']}")
    print("\n--- body ---\n")
    print(issue["body"] or "(empty)")
    for comment in issue["comments"]:
        print(f"\n--- comment by {comment['author']} at {comment['created_at']} ---\n")
        print(comment["body"])


def target_for(issue, config=None):
    config = config or load_config()
    labels = {label.lower() for label in issue.get("labels", [])}
    matches = {
        route["target"] for route in config["routes"]
        if route["source"] == issue["repository"] and labels.intersection(route["labels_any"])
    }
    if len(matches) > 1:
        raise ValueError("ambiguous target routes")
    if matches:
        return matches.pop()
    for source in config["sources"]:
        if source["repo"] == issue["repository"]:
            return source["default_target"]
    raise ValueError("issue repository is not configured")


def exclude(ref, reason: str):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON_LENGTH:
        sys.exit(f"exclusion reason must be 1-{MAX_REASON_LENGTH} characters")
    reason = reason.strip()
    try:
        issue = find_issue(ref)
    except ValueError as error:
        sys.exit(str(error))
    entries = load_excluded()
    board = load_board()
    if issue["key"] in excluded_keys(board, entries):
        print(f"{issue['key']} already excluded")
        return
    entries.append({
        "key": issue["key"],
        "repository": issue["repository"],
        "number": issue["number"],
        "reason": reason,
        "excluded_at": datetime.now(timezone.utc).isoformat(),
    })
    atomic_write(EXCLUDED, json.dumps(entries, indent=1) + "\n")
    print(f"excluded {issue['key']}: {reason}")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    try:
        cmd = args[0]
        if cmd == "fetch":
            fetch()
        elif cmd == "fetch-pipelines":
            fetch_pipelines()
        elif cmd == "roster":
            roster(args[1:] or None)
        elif cmd == "show" and len(args) == 2:
            show(args[1])
        elif cmd == "target" and len(args) == 2:
            print(target_for(find_issue(args[1])))
        elif cmd == "exclude" and len(args) >= 2:
            exclude(args[1], " ".join(args[2:]) or "completed")
        elif cmd == "excluded":
            print(json.dumps(load_excluded(), indent=1))
        elif cmd == "complete-loop" and len(args) == 2:
            complete_loop(int(args[1]))
        else:
            sys.exit(__doc__)
    except (ValueError, OSError) as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
