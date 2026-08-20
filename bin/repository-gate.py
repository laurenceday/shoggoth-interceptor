#!/usr/bin/env python3
"""Fail-closed repository write policy and consent-driven setup.

Mode `protected-orgs`: organisations named by the policy are write-protected,
their recorded exemptions are permitted, and any organisation the policy does
not name is permitted. Every write is bound to the GitHub login recorded at
consent time, no write is permitted before consent is recorded, and a merge is
never permitted. `init` is the only writer of policy.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "state" / "guardrails.json"
LOCAL_POLICY = ROOT / ".loops" / "guardrails.json"
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})$")
ORG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,99})$")
MAX_POLICY_BYTES = 1_000_000
POLICY_KEYS = {"version", "mode", "github_login", "protected", "note"}
ENTRY_KEYS = {"exempt"}
OPERATIONS = ("push", "pull-request", "merge")
MERGE_REASON = "a merge is never gate-approved; a human merges after review"


def normalize_repo(raw):
    if not isinstance(raw, str):
        raise ValueError("invalid repository target")
    value = raw.strip()
    for prefix in ("git@github.com:", "https://github.com/", "ssh://git@github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    if value.endswith(".git"):
        value = value[:-4]
    value = value.strip("/")
    if not REPO_RE.fullmatch(value):
        raise ValueError("invalid repository target")
    return value.lower()


def policy_path():
    return LOCAL_POLICY if LOCAL_POLICY.exists() else DEFAULT_POLICY


def validate_policy(raw):
    if not isinstance(raw, dict) or raw.get("version") != 2:
        raise ValueError("policy version must be 2")
    if raw.get("mode") != "protected-orgs":
        raise ValueError("policy mode must be protected-orgs")
    if set(raw) - POLICY_KEYS:
        raise ValueError("policy carries unknown fields")
    login = raw.get("github_login")
    if login is not None and (not isinstance(login, str) or not ORG_RE.fullmatch(login)):
        raise ValueError("github_login must be a GitHub login or null")
    protected = raw.get("protected")
    if not isinstance(protected, dict):
        raise ValueError("protected must be an object")
    clean = {}
    for raw_org, entry in protected.items():
        if not isinstance(raw_org, str) or not ORG_RE.fullmatch(raw_org) or not isinstance(entry, dict):
            raise ValueError("invalid protected organization")
        org = raw_org.lower()
        if org in clean or set(entry) != ENTRY_KEYS:
            raise ValueError("invalid protected organization")
        if not isinstance(entry["exempt"], list):
            raise ValueError("exempt must be a list of repositories")
        exempt = []
        for item in entry["exempt"]:
            repo = normalize_repo(item)
            if repo.split("/", 1)[0] != org:
                raise ValueError("exempt repository must belong to its organization")
            if repo in exempt:
                raise ValueError("exempt repository listed twice")
            exempt.append(repo)
        clean[org] = {"exempt": exempt}
    # `init protect` records the login and the first protected organisation in
    # one consent event; neither half exists alone in anything init writes.
    if login is None and clean:
        raise ValueError("protection without a recorded login records no consent")
    if login is not None and not clean:
        raise ValueError("a recorded login without a protected organization is not consent")
    return {"version": 2, "mode": "protected-orgs", "github_login": login, "protected": clean}


def load_policy(path=None):
    path = Path(path or policy_path())
    try:
        if path.stat().st_size > MAX_POLICY_BYTES:
            raise ValueError("policy exceeds size limit")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read repository policy: {error}") from None
    except json.JSONDecodeError:
        raise ValueError("repository policy is invalid JSON") from None
    return validate_policy(raw)


def active_login():
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    login = result.stdout.strip()
    if result.returncode or not ORG_RE.fullmatch(login):
        raise ValueError("cannot establish active GitHub login")
    return login


def decide(target, policy, login, operation="push"):
    repo = normalize_repo(target)
    if operation not in OPERATIONS:
        raise ValueError("unknown operation")
    if operation == "merge":
        return False, MERGE_REASON
    recorded = policy["github_login"]
    if recorded is None:
        return False, "no consent recorded; run repository-gate.py init protect <org>"
    if login.lower() != recorded.lower():
        return False, f"active GitHub login '{login}' does not match configured login"
    org = repo.split("/", 1)[0]
    entry = policy["protected"].get(org)
    if entry is None:
        return True, f"organization '{org}' is not protected; write allowed for {repo}"
    if repo in entry["exempt"]:
        return True, f"exempt write allowed for {repo}"
    return False, f"organization '{org}' is write-protected and '{repo}' is not exempt"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _local_policy():
    path = policy_path()
    if path == DEFAULT_POLICY:
        path = LOCAL_POLICY
    if path.exists():
        return path, load_policy(path)
    return path, {"version": 2, "mode": "protected-orgs", "github_login": None, "protected": {}}


def _consent_login(policy):
    active = active_login()
    recorded = policy["github_login"]
    if recorded is not None and recorded.lower() != active.lower():
        raise ValueError(f"policy is bound to '{recorded}' but the active login is '{active}'")
    return active


def _record(path, policy):
    validate_policy(policy)
    atomic_write(path, json.dumps(policy, indent=2, sort_keys=True) + "\n")


def init_protect(org):
    if not isinstance(org, str) or not ORG_RE.fullmatch(org):
        raise ValueError("invalid organization")
    org = org.lower()
    path, policy = _local_policy()
    answer = input(
        f"Write-protect every repository in {org}, denying pushes and pull requests "
        f"except recorded exemptions, while organisations this policy does not name "
        f"stay permitted for the active GitHub login? [y/N] "
    ).strip().lower()
    if answer not in ("y", "yes"):
        raise ValueError("setup aborted; nothing was recorded")
    login = _consent_login(policy)
    policy["github_login"] = login
    policy["protected"].setdefault(org, {"exempt": []})
    _record(path, policy)
    print(f"wrote {path}: {org} is write-protected except {policy['protected'][org]['exempt'] or 'nothing'} for {login}")


def init_exempt(target):
    repo = normalize_repo(target)
    org = repo.split("/", 1)[0]
    path, policy = _local_policy()
    if org not in policy["protected"]:
        raise ValueError(f"organization '{org}' is not protected; run init protect {org} first")
    answer = input(
        f"Exempt {repo} from {org}'s write protection, permitting pushes and pull "
        f"requests to it? [y/N] "
    ).strip().lower()
    if answer not in ("y", "yes"):
        raise ValueError("setup aborted; no exemption was recorded")
    login = _consent_login(policy)
    exempt = policy["protected"][org]["exempt"]
    if repo not in exempt:
        exempt.append(repo)
        exempt.sort()
    _record(path, policy)
    print(f"wrote {path}: {repo} is exempt from {org}'s protection for {login}")


USAGE = (
    "usage: repository-gate.py <owner/repo> | merge <owner/repo> | "
    "init protect <org> | init exempt <org/repo>"
)


def main():
    args = sys.argv[1:]
    try:
        if args and args[0] == "init":
            if len(args) == 3 and args[1] == "protect":
                init_protect(args[2])
                return 0
            if len(args) == 3 and args[1] == "exempt":
                init_exempt(args[2])
                return 0
            raise ValueError(USAGE)
        if len(args) == 2 and args[0] == "merge":
            # Unconditional: refused before the policy or login is even read,
            # so a broken policy or a missing gh cannot soften the statement.
            normalize_repo(args[1])
            print(f"repository-gate: DENIED: {MERGE_REASON}", file=sys.stderr)
            return 1
        if len(args) != 1:
            raise ValueError(USAGE)
        policy = load_policy()
        login = active_login()
        allowed, reason = decide(args[0], policy, login, "push")
        if not allowed:
            print(f"repository-gate: DENIED: {reason}", file=sys.stderr)
            return 1
        print(f"repository-gate: {reason}", file=sys.stderr)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"repository-gate: DENIED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
