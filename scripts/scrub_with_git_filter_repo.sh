#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scrub_with_git_filter_repo.sh /path/to/local/mirror/repo replacements.txt
# Example:
#   ./scrub_with_git_filter_repo.sh /tmp/seekphony.git /tmp/replacements.txt
# Where replacements.txt contains lines like:
#   ACTUAL_SECRET==>REDACTED

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <mirror-repo-path> <replacements-file>"
  echo "Example: $0 /tmp/seekphony.git /tmp/replacements.txt" >&2
  exit 2
fi

MIRROR_REPO="$1"
REPLACEMENTS="$2"

if [ ! -d "$MIRROR_REPO" ]; then
  echo "Mirror repo not found at $MIRROR_REPO" >&2
  exit 2
fi

if [ ! -f "$REPLACEMENTS" ]; then
  echo "Replacements file not found at $REPLACEMENTS" >&2
  exit 2
fi

echo "Running git-filter-repo on mirror repo: $MIRROR_REPO"

# Make a safety copy of the mirror
cp -a "$MIRROR_REPO" "${MIRROR_REPO}.backup.$(date +%s)"

# Run git-filter-repo with replace-text
cd "$MIRROR_REPO"

# Ensure git-filter-repo is installed. See SCRUB_README.md for install instructions.
if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo is not installed. Install with: pip install git-filter-repo" >&2
  exit 2
fi

# Run the rewrite
git-filter-repo --replace-text "$REPLACEMENTS"

echo "Repository rewritten. Performing garbage collection and cleanup."

git reflog expire --expire=now --all || true
git gc --prune=now --aggressive || true

echo "You must now push the rewritten refs to origin with force."
echo "Commands to run from a separate clone or coordinate with collaborators:" 
cat <<'EOF'
# From a separate local clone (not the mirror):
# 1. Make a fresh clone of the remote repo (this will still have the old history until we force-push):
#    git clone git@github.com:McloiGG/Seekphony.git
# 2. Add the mirror as a remote (if needed) and fetch rewritten refs, or push from the mirror itself:
#    cd Seekphony
#    git fetch --all
#    git push --force --all
#    git push --force --tags
# 3. Inform all collaborators to re-clone after the force-push (see SCRUB_README.md for details)
EOF

echo "Completed local rewrite. Follow the instructions above to push and coordinate with collaborators."
