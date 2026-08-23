#!/usr/bin/env python3
"""Refuse runtime-host authorship in one exact Interceptor branch range."""

from __future__ import annotations

import argparse
import os
import re
import selectors
import subprocess
import sys
import time


TIMEOUT_SECONDS = 15
MAX_OUTPUT_BYTES = 1_000_000
MAX_COMMITS = 500
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
COAUTHOR_RE = re.compile(
    r"^Co-authored-by:\s*(?P<name>.+?)\s*<(?P<email>[^<>]+)>$",
    re.IGNORECASE,
)
HOST_BYLINE_RE = re.compile(
    r"(?:generated|authored|co-authored)\s+by\s+"
    r"(?:\[(?:claude(?: code)?|codex|chatgpt|copilot|gemini(?: code assist)?)\]"
    r"\([^\)]+\)|claude(?: code)?|codex|chatgpt|copilot|gemini(?: code assist)?)",
    re.IGNORECASE,
)
HOST_NAMES = frozenset(
    {
        "aider",
        "anthropic",
        "chatgpt",
        "claude",
        "claude code",
        "claude[bot]",
        "codex",
        "copilot",
        "cursor",
        "devin",
        "gemini",
        "gemini code assist",
        "github copilot",
        "openai",
    }
)
HOST_EMAILS = frozenset({"noreply@anthropic.com", "noreply@openai.com"})


class GateError(ValueError):
    """A bounded authorship check could not establish an acceptable range."""


def checked_ref(value: str, label: str) -> str:
    if (
        not REF_RE.fullmatch(value)
        or ".." in value
        or "//" in value
        or "@{" in value
        or value.endswith(("/", ".lock"))
    ):
        raise GateError(f"{label} is not a safe Git ref")
    return value


def bounded_git(argv: list[str]) -> bytes:
    """Run Git without a shell, bounding time and captured output."""
    process = subprocess.Popen(
        ["git", *argv],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None
    output = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise GateError("Git authorship inspection timed out")
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [
                    (key, selectors.EVENT_READ) for key in selector.get_map().values()
                ]
            for key, _ in events:
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > MAX_OUTPUT_BYTES:
                    process.kill()
                    process.wait()
                    raise GateError("Git authorship inspection exceeded its output cap")
        returncode = process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise GateError("Git authorship inspection timed out") from None
    finally:
        selector.close()
        process.stdout.close()
    if returncode != 0:
        raise GateError("Git authorship inspection failed")
    return bytes(output)


def text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise GateError("Git authorship data is not UTF-8") from None


def resolved(ref: str, label: str) -> str:
    checked_ref(ref, label)
    lines = [
        line.strip()
        for line in text(bounded_git(["rev-parse", "--verify", f"{ref}^{{commit}}"]))
        .splitlines()
        if line.strip()
    ]
    if len(lines) != 1 or not COMMIT_RE.fullmatch(lines[0]):
        raise GateError(f"{label} does not resolve to one commit")
    return lines[0]


def is_host(name: str, email: str) -> bool:
    return name.strip().casefold() in HOST_NAMES or email.strip().casefold() in HOST_EMAILS


def inspect_commit(commit: str) -> None:
    raw = text(
        bounded_git(
            ["show", "-s", "--no-show-signature", "--format=%an%x00%ae%x00%B", commit]
        )
    )
    fields = raw.rstrip("\n").split("\0", 2)
    if len(fields) != 3 or not fields[0].strip() or not fields[1].strip():
        raise GateError(f"commit {commit} has malformed authorship data")
    name, email, body = fields
    if is_host(name, email):
        raise GateError(f"commit {commit} uses a runtime host as author")
    for line in body.splitlines():
        match = COAUTHOR_RE.fullmatch(line)
        if match and is_host(match.group("name"), match.group("email")):
            raise GateError(f"commit {commit} uses a runtime host as co-author")
    if HOST_BYLINE_RE.search(body):
        raise GateError(f"commit {commit} carries a runtime-host byline")


def inspect_range(base_ref: str, head_ref: str) -> list[str]:
    base = resolved(base_ref, "base")
    head = resolved(head_ref, "head")
    bounded_git(["merge-base", "--is-ancestor", base, head])
    lines = [
        line.strip()
        for line in text(
            bounded_git(
                [
                    "rev-list",
                    "--reverse",
                    f"--max-count={MAX_COMMITS + 1}",
                    f"{base}..{head}",
                ]
            )
        ).splitlines()
        if line.strip()
    ]
    if not lines or lines[-1] != head:
        raise GateError("authorship range is empty or does not end at head")
    if len(lines) > MAX_COMMITS:
        raise GateError(f"authorship range exceeds {MAX_COMMITS} commits")
    if any(not COMMIT_RE.fullmatch(commit) for commit in lines):
        raise GateError("authorship range returned a malformed commit")
    for commit in lines:
        inspect_commit(commit)
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        inspect_range(args.base, args.head)
    except GateError as error:
        print(f"authorship gate: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
