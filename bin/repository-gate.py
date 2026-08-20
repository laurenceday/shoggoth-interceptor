#!/usr/bin/env python3
"""Fail-closed repository write policy and first-run setup."""

import json
import os
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
    override = os.environ.get("SHOGGOTH_GUARDRAILS_FILE")
    if override:
        return Path(override)
    return LOCAL_POLICY if LOCAL_POLICY.exists() else DEFAULT_POLICY


def validate_policy(raw):
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("policy version must be 1")
    organisations = raw.get("organizations")
    if not isinstance(organisations, dict):
        raise ValueError("organizations must be an object")
    clean = {}
    for raw_org, entry in organisations.items():
        if not isinstance(raw_org, str) or not ORG_RE.fullmatch(raw_org) or not isinstance(entry, dict):
            raise ValueError("invalid organization policy")
        org = raw_org.lower()
        if org in clean or entry.get("mode") != "sandbox-only":
            raise ValueError("invalid organization policy")
        sandbox = normalize_repo(entry.get("sandbox"))
        if sandbox.split("/", 1)[0] != org:
            raise ValueError("sandbox must belong to its organization")
        login = entry.get("github_login")
        if not isinstance(login, str) or not ORG_RE.fullmatch(login):
            raise ValueError("organization policy needs github_login")
        clean[org] = {"mode": "sandbox-only", "sandbox": sandbox, "github_login": login}
    return {"version": 1, "organizations": clean}


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


def decide(target, policy, login):
    repo = normalize_repo(target)
    org = repo.split("/", 1)[0]
    entry = policy["organizations"].get(org)
    if not entry:
        return False, f"organization '{org}' has no write policy"
    if repo != entry["sandbox"]:
        return False, f"only sandbox '{entry['sandbox']}' is write-enabled for '{org}'"
    if login.lower() != entry["github_login"].lower():
        return False, f"active GitHub login '{login}' does not match configured login"
    return True, f"sandbox write allowed for {repo}"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def init_policy(org, sandbox):
    if not ORG_RE.fullmatch(org or ""):
        raise ValueError("invalid organization")
    org = org.lower()
    sandbox = normalize_repo(sandbox)
    if sandbox.split("/", 1)[0] != org:
        raise ValueError("sandbox must belong to the organization")
    answer = input(
        f"Treat every repository in {org} as write-protected, allowing writes only to {sandbox}? [y/N] "
    ).strip().lower()
    if answer not in ("y", "yes"):
        raise ValueError("setup aborted; no write access was granted")
    login = active_login()
    path = policy_path()
    if path == DEFAULT_POLICY:
        path = LOCAL_POLICY
    if path.exists():
        policy = load_policy(path)
    else:
        policy = {"version": 1, "organizations": {}}
    policy["organizations"][org] = {
        "mode": "sandbox-only",
        "sandbox": sandbox,
        "github_login": login,
    }
    atomic_write(path, json.dumps(policy, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path}: {org} is off-limits except {sandbox} for {login}")


def main():
    args = sys.argv[1:]
    try:
        if len(args) == 3 and args[0] == "init":
            init_policy(args[1], args[2])
            return 0
        if len(args) != 1:
            raise ValueError("usage: repository-gate.py <owner/repo> | init <org> <org/sandbox>")
        policy = load_policy()
        login = active_login()
        allowed, reason = decide(args[0], policy, login)
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
