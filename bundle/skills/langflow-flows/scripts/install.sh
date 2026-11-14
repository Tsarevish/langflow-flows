#!/usr/bin/env bash
# Update packaged files; preserve installation-specific profiles and credentials.
set -euo pipefail
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:-$HOME/.dsh/skills/langflow-flows}"
mkdir -p "$target"
target="$(cd "$target" && pwd)"
case "$target/" in "$source_dir/"*) echo "Target must be outside source" >&2; exit 1;; esac
for name in SKILL.md README.md VERIFICATION.md NOTICE.md LICENSE; do
  [ ! -f "$source_dir/$name" ] || cp "$source_dir/$name" "$target/$name"
done
for folder in references examples scripts tests profiles/_template; do
  [ -d "$source_dir/$folder" ] || continue
  while IFS= read -r -d '' file; do
    relative="${file#"$source_dir/"}"
    mkdir -p "$target/$(dirname "$relative")"
    cp "$file" "$target/$relative"
  done < <(find "$source_dir/$folder" -type f ! -name '*.pyc' ! -path '*/__pycache__/*' -print0)
done
echo "Installed: $target (existing stand profiles preserved)"
