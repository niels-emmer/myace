#!/usr/bin/env bash
# check-readme.sh — structural floor for README.md.
#
# Usage: bash scripts/check-readme.sh [path/to/README.md]
#
# Checks what a machine can check: the file exists, the required sections are
# present, no placeholder text survives, every relative link/image resolves, and
# every package.json script is mentioned. It cannot see a wrong port, a stale
# screenshot, or a command that no longer runs — run Quick Start for that.
#
# Exit 0 = pass (warnings allowed), 1 = errors found.

set -uo pipefail

readme="${1:-README.md}"
errors=0
warnings=0

err()  { printf 'ERROR  %s\n' "$*"; errors=$((errors + 1)); }
warn() { printf 'WARN   %s\n' "$*"; warnings=$((warnings + 1)); }

[ -f "$readme" ] || { printf 'ERROR  %s not found\n' "$readme"; exit 1; }
root=$(cd "$(dirname "$readme")" && pwd -P)

# --- required sections -------------------------------------------------------
has_heading() { grep -qiE "^#{1,6}[[:space:]]+.*($1)" "$readme"; }

has_heading 'quick[ -]?start|getting[ -]?started|installation|install' \
  || err 'missing section: Quick Start / Getting Started'
has_heading 'usage|examples?' || err 'missing section: Usage'
has_heading 'license|licence'  || err 'missing section: License'
has_heading 'features|overview|what (is|it)' \
  || warn 'no Features / Overview section'
has_heading 'structure|layout|architecture' \
  || warn 'no Repository structure / Architecture section'
has_heading 'config' || warn 'no Configuration section'
has_heading 'test'   || warn 'no Testing section'

# --- placeholder text --------------------------------------------------------
placeholders=$(grep -nEi 'TODO|TBD|FIXME|lorem ipsum|coming soon|<your[-_ ]|insert (here|name|url)' "$readme" || true)
if [ -n "$placeholders" ]; then
  printf '%s\n' "$placeholders"
  err 'placeholder text present (lines above)'
fi

# --- at least one code block -------------------------------------------------
grep -q '^[[:space:]]*```' "$readme" || warn 'no fenced code block (commands should be copy-pasteable)'

# --- relative links and images ----------------------------------------------
links=$(grep -oE '\]\([^)[:space:]]+\)' "$readme" | sed -E 's/^\]\(//; s/\)$//' || true)
if [ -n "$links" ]; then
  while IFS= read -r target; do
    [ -z "$target" ] && continue
    case "$target" in
      http://*|https://*|mailto:*|'#'*|/*) continue ;;
    esac
    path=${target%%#*}
    path=${path%%\?*}
    [ -z "$path" ] && continue
    [ -e "$root/$path" ] || err "broken relative link: $target"
  done <<< "$links"
fi

# --- package.json scripts ----------------------------------------------------
if [ -f "$root/package.json" ] && command -v python3 >/dev/null 2>&1; then
  scripts=$(python3 - "$root/package.json" <<'PY' 2>/dev/null || true
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for name in (data.get("scripts") or {}):
    print(name)
PY
)
  if [ -n "$scripts" ]; then
    while IFS= read -r name; do
      [ -z "$name" ] && continue
      grep -qF -- "$name" "$readme" || warn "package.json script not mentioned in README: $name"
    done <<< "$scripts"
  fi
fi

# --- size budget -------------------------------------------------------------
lines=$(wc -l < "$readme" | tr -d ' ')
if [ "$lines" -gt 400 ]; then
  warn "README is $lines lines — move detail into docs/ and link to it"
fi

# --- summary -----------------------------------------------------------------
if [ "$errors" -ne 0 ]; then
  printf '\nREADME check: FAIL (%d errors, %d warnings)\n' "$errors" "$warnings"
  exit 1
fi
if [ "$warnings" -ne 0 ]; then
  printf '\nREADME check: PASS with %d warning(s)\n' "$warnings"
  exit 0
fi
printf '\nREADME check: PASS\n'
