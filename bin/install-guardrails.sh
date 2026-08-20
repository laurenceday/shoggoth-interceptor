#!/bin/sh
# Installs the repository gate pre-push hook into a clone. Worktrees share the
# parent clone's hooks directory, so one install covers them all. Run this as
# part of the clone step of every loop; re-running is harmless.
#
# Usage: install-guardrails.sh <path-to-clone-or-worktree>
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO_PATH="${1:?usage: install-guardrails.sh <repo path>}"

hooks_dir=$(cd "$REPO_PATH" && cd "$(git rev-parse --git-common-dir)" && pwd)/hooks
mkdir -p "$hooks_dir"

cat > "$hooks_dir/pre-push" <<EOF
#!/bin/sh
# Installed by shoggoth-interceptor. Repositories in a protected organisation
# may not receive a push unless recorded as exempt, and every push requires
# the configured GitHub login.
#
# set -eu is load-bearing. Without it a failing verify-gate.py only prints, and
# the push carries on into a gate whose digest no longer matches the pin, which
# is the one case the pin exists for. The integrity check must abort the push,
# not annotate it.
set -eu
"$ROOT/bin/verify-gate.py"
exec "$ROOT/bin/repository-gate.py" "\${2:-\$(git remote get-url "\$1")}"
EOF
chmod +x "$hooks_dir/pre-push"
echo "guardrail pre-push hook installed at $hooks_dir/pre-push"
