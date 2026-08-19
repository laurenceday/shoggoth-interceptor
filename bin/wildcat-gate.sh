#!/bin/sh
# Guardrail (a): pushes and pull requests into wildcat-finance/* are refused
# unless the target is wildcat-finance/skills or the active gh credential is
# the shoggoth account recorded in state/guardrails.json. Any other user or
# organisation passes untouched.
#
# Usage: wildcat-gate.sh <github-repo-url-or-slug>
# Exit 0 = allowed, exit 1 = denied (with the reason on stderr).
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
GUARDRAILS="${SHOGGOTH_GUARDRAILS_FILE:-$ROOT/state/guardrails.json}"
TARGET="${1:?usage: wildcat-gate.sh <repo url or owner/name>}"

# Normalise: accept https://github.com/o/r(.git), git@github.com:o/r(.git), o/r
slug=$(printf '%s' "$TARGET" \
  | sed -e 's#^git@github\.com:##' -e 's#^https://github\.com/##' \
        -e 's#^ssh://git@github\.com/##' -e 's#\.git$##' \
  | cut -d/ -f1,2)
owner=$(printf '%s' "$slug" | cut -d/ -f1 | tr '[:upper:]' '[:lower:]')
repo=$(printf '%s' "$slug" | cut -d/ -f2 | tr '[:upper:]' '[:lower:]')

if [ "$owner" != "wildcat-finance" ]; then
    exit 0
fi
if [ "$repo" = "skills" ]; then
    exit 0
fi

allowed_login=$(python3 - "$GUARDRAILS" <<'EOF' 2>/dev/null || true
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("wildcat_gh_login") or "")
except Exception:
    print("")
EOF
)

if [ -z "$allowed_login" ]; then
    echo "wildcat-gate: DENIED push/PR to $slug." >&2
    echo "wildcat-gate: no shoggoth credential is configured; only" >&2
    echo "wildcat-gate: wildcat-finance/skills is allowed until one exists." >&2
    echo "wildcat-gate: (set wildcat_gh_login in state/guardrails.json once" >&2
    echo "wildcat-gate: the shoggoth@wildcat.finance gh account is issued.)" >&2
    exit 1
fi

active_login=$(gh api user --jq .login 2>/dev/null || echo "")
if [ "$active_login" != "$allowed_login" ]; then
    echo "wildcat-gate: DENIED push/PR to $slug." >&2
    echo "wildcat-gate: active gh login '$active_login' is not the shoggoth" >&2
    echo "wildcat-gate: credential '$allowed_login'." >&2
    exit 1
fi
exit 0
