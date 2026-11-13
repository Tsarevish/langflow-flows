#!/usr/bin/env bash
# Install or update the skill into a DSH skills directory (macOS / Linux).
#
#   ./scripts/install.sh
#   ./scripts/install.sh ~/.claude/skills/langflow-flows
#
# DSH scans <dshHome>/skills for one directory per skill: <name>/SKILL.md.
set -euo pipefail

source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:-$HOME/.dsh/skills/langflow-flows}"

if [ ! -f "$source_dir/SKILL.md" ]; then
  echo "SKILL.md not found next to this script: $source_dir" >&2
  exit 1
fi

rm -rf "$target"
mkdir -p "$target"
cp -R "$source_dir"/. "$target"/
find "$target" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$target" -name '*.pyc' -delete

files=$(find "$target" -type f | wc -l | tr -d ' ')
echo "installed: $target ($files files)"
echo "check: call the skill tool with name 'langflow-flows'"
