#!/bin/sh
# Installs the wildcat-gate pre-push hook into a clone. Worktrees share the
# parent clone's hooks directory, so one install covers them all. Run this as
# part of the clone step of every loop; re-running is harmless.
#
# Usage: install-guardrails.sh <path-to-clone-or-worktree>
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO_PATH="${1:?usage: install-guardrails.sh <repo path>}"

hooks_dir=$(git -C "$REPO_PATH" rev-parse --git-common-dir)/hooks
hooks_dir=$(cd "$REPO_PATH" && cd "$(git rev-parse --git-common-dir)" && pwd)/hooks
mkdir -p "$hooks_dir"

cat > "$hooks_dir/pre-push" <<EOF
#!/bin/sh
# Installed by shoggoth-interceptor bin/install-guardrails.sh. Blocks pushes
# to wildcat-finance/* (except skills) without the shoggoth credential.
exec "$ROOT/bin/wildcat-gate.sh" "\${2:-\$(git remote get-url "\$1")}"
EOF
chmod +x "$hooks_dir/pre-push"
echo "guardrail pre-push hook installed at $hooks_dir/pre-push"
