#!/usr/bin/env sh
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd)
chmod +x "${repo_root}/.githooks/"* || true
git -c "safe.directory=${repo_root}" -C "${repo_root}" config core.hooksPath .githooks

echo "Installed Seekphony Git hooks from .githooks"
