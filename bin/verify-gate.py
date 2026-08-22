#!/usr/bin/env python3
"""Fail closed when the repository write gate or required surfaces drift."""

import hashlib
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROTECTED_EXECUTABLES = {
    Path("bin/repository-gate.py"): "955939936be81fb4ffdb979225dc29d23f6d58bca9f1c929c166d7da04a46a5e",
    Path("bin/install-guardrails.sh"): "efb07ed18f88750cb9aea2750cd247ee5af12f0ae52f818d3160946e690204f6",
}
MAX_PROTECTED_FILE_BYTES = 1_000_000

REQUIRED_SNIPPETS = {
    Path("README.md"): (
        "`bin/repository-gate.py`",
        "`bin/install-guardrails.sh`",
        "`bin/shoggoth-pr.sh`",
        "The gate and its installer are fixed boundaries.",
        "may neither change nor bypass either file.",
    ),
    Path("CLAUDE.md"): (
        "### The gate and installer are untouchable",
        "`bin/repository-gate.py`",
        "`bin/install-guardrails.sh`",
        "`bin/install-guardrails.sh <clone>`",
        "`bin/shoggoth-pr.sh --repo <owner/name> ...`",
        "`python3 bin/repository-gate.py init protect ORG`",
        "`python3 bin/repository-gate.py init exempt ORG/REPO`",
        "Only a human maintainer acting outside the Shoggoth may change either file.",
    ),
    Path("bin/install-guardrails.sh"): (
        # Adjacency, not mere presence: an unguarded verify call is a hook that
        # prints a digest mismatch and pushes anyway.
        'set -eu\n"$ROOT/bin/verify-gate.py"',
        'exec "$ROOT/bin/repository-gate.py"',
    ),
    Path("bin/shoggoth-pr.sh"): (
        '"$ROOT/bin/verify-gate.py"',
        '"$ROOT/bin/repository-gate.py" "$repo"',
        'exec gh pr create "$@"',
    ),
    Path("tests/test_guardrails.py"): (
        'GATE = REPO / "bin" / "repository-gate.py"',
    ),
    Path("tests/test_gate_integrity.py"): (
        'Path("bin/repository-gate.py")',
        'Path("bin/install-guardrails.sh")',
    ),
    Path("state/guardrails.json"): (
        "Default deny",
        '"protected"',
        '"protected-orgs"',
    ),
    Path(".github/workflows/gate-integrity.yml"): (
        "python3 bin/verify-gate.py",
        "python3 -m unittest tests.test_gate_integrity tests.test_guardrails",
    ),
}


def _read_regular_file(root: Path, relative: Path, errors: list[str]) -> bytes | None:
    path = root / relative
    try:
        info = path.lstat()
    except OSError:
        errors.append(f"missing protected file: {relative}")
        return None
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        errors.append(f"protected file is not regular: {relative}")
        return None
    if info.st_size > MAX_PROTECTED_FILE_BYTES:
        errors.append(f"protected file exceeds size limit: {relative}")
        return None
    try:
        return path.read_bytes()
    except OSError:
        errors.append(f"cannot read protected file: {relative}")
        return None


def verify(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative, expected_digest in PROTECTED_EXECUTABLES.items():
        protected_bytes = _read_regular_file(root, relative, errors)
        if protected_bytes is None:
            continue
        digest = hashlib.sha256(protected_bytes).hexdigest()
        if digest != expected_digest:
            errors.append(f"protected digest does not match the pinned value: {relative}")
        mode = (root / relative).stat().st_mode
        if not mode & stat.S_IXUSR:
            errors.append(f"protected file is not executable: {relative}")

    contents = {}
    for relative, snippets in REQUIRED_SNIPPETS.items():
        raw = _read_regular_file(root, relative, errors)
        if raw is None:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"protected file is not UTF-8: {relative}")
            continue
        contents[relative] = text
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"required gate reference missing from {relative}")

    installer = contents.get(Path("bin/install-guardrails.sh"), "")
    if installer:
        verify_at = installer.find('"$ROOT/bin/verify-gate.py"')
        gate_at = installer.find('exec "$ROOT/bin/repository-gate.py"')
        if not 0 <= verify_at < gate_at:
            errors.append("installed hook does not verify integrity before the gate")
    wrapper = contents.get(Path("bin/shoggoth-pr.sh"), "")
    if wrapper:
        verify_at = wrapper.find('"$ROOT/bin/verify-gate.py"')
        gate_at = wrapper.find('"$ROOT/bin/repository-gate.py" "$repo"')
        create_at = wrapper.find('exec gh pr create "$@"')
        if not 0 <= verify_at < gate_at < create_at:
            errors.append("pull-request wrapper does not preserve verifier and gate order")
    return errors


def main() -> int:
    errors = verify()
    for error in errors:
        print(f"gate integrity: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
