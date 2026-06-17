#!/usr/bin/env bash
# scripts/apply-branding.sh
#
# One-click POUNDING branding restore for AionCore.
# Run after upstream sync to re-apply all POUNDING branding.
#
# Categories:
#   1. Text replacements (aioncore→poundingcore)
#   2. Feature file existence (CC-Switch, Ozon skill, migration, etc.)
#   3. Config value verification (delegates to check-branding.sh)
#
# Usage:
#   bash scripts/apply-branding.sh          # apply all branding
#   bash scripts/apply-branding.sh --check  # dry-run

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="apply"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check|--dry-run) MODE="check"; shift ;;
    --help|-h) echo "Usage: bash scripts/apply-branding.sh [--check]"; exit 0 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COUNT=0

replace() {
  local file="$1" pattern="$2" replacement="$3" label="$4"
  if [ ! -f "$file" ]; then
    echo -e "  ${RED}SKIP${NC} $label: not found"
    return 0
  fi
  if [ "$MODE" = "check" ]; then
    if grep -q "$replacement" "$file" 2>/dev/null; then
      echo -e "  ${GREEN}OK${NC}   $label"
    elif grep -q "$pattern" "$file" 2>/dev/null; then
      echo -e "  ${YELLOW}FIX${NC}  $label"
    else
      echo -e "  ${BLUE}N/A${NC}  $label"
    fi
  else
    if grep -q "$pattern" "$file" 2>/dev/null; then
      sed -i '' "s|$pattern|$replacement|g" "$file"
      echo -e "  ${GREEN}DONE${NC} $label"
      COUNT=$((COUNT + 1))
    else
      echo -e "  ${BLUE}N/A${NC}  $label"
    fi
  fi
}

replace_in_dir() {
  local dir="$1" pattern="$2" replacement="$3" label="$4"
  if [ ! -d "$dir" ]; then echo -e "  ${RED}SKIP${NC} $label: $dir"; return 1; fi
  if [ "$MODE" = "check" ]; then
    if grep -rq "$pattern" "$dir" --include="*.rs" --include="*.toml" --include="*.md" --include="*.sql" 2>/dev/null; then
      echo -e "  ${YELLOW}FIX${NC}  $label"
    else
      echo -e "  ${GREEN}OK${NC}   $label"
    fi
  else
    local files
    files=$(grep -rl "$pattern" "$dir" --include="*.rs" --include="*.toml" --include="*.md" --include="*.sql" 2>/dev/null || true)
    if [ -n "$files" ]; then
      echo "$files" | while IFS= read -r f; do sed -i '' "s|$pattern|$replacement|g" "$f"; done
      echo -e "  ${GREEN}DONE${NC} $label"
      COUNT=$((COUNT + 1))
    else
      echo -e "  ${BLUE}N/A${NC}  $label"
    fi
  fi
}

file_exists() {
  if [ -e "$1" ]; then echo -e "  ${GREEN}OK${NC}   $2"; else echo -e "  ${RED}MISS${NC} $2: $1"; fi
}

# ----------------------------------------------------------------
# Category 1: Text Replacements
# ----------------------------------------------------------------
apply_text_replacements() {
  echo ""
  echo -e "${BLUE}== Category 1: Text Replacements ==${NC}"

  # --- Cargo.toml binary name ---
  replace "$ROOT/crates/aionui-app/Cargo.toml" \
    'name = "aioncore"' 'name = "poundingcore"' "binary name"

  # --- User-Agent header ---
  replace "$ROOT/crates/aionui-system/src/version.rs" \
    '"aioncore"' '"poundingcore"' "user-agent"

  # --- Default data dir ---
  replace "$ROOT/crates/aionui-app/src/router/state.rs" \
    '"aioncore"' '"poundingcore"' "default data dir"

  # --- "aioncore" → "poundingcore" across source (binary references only) ---
  # Replace in server commands, startup, diagnostics
  replace_in_dir "$ROOT/crates" "bundled-aioncore" "bundled-poundingcore" "bundled dir refs"
}

# ----------------------------------------------------------------
# Category 2: Feature File Existence
# ----------------------------------------------------------------
check_feature_files() {
  echo ""
  echo -e "${BLUE}== Category 2: Feature File Existence ==${NC}"

  # CC-Switch module
  file_exists "$ROOT/crates/aionui-ai-agent/src/cc_switch/mod.rs"        "cc_switch/mod.rs"
  file_exists "$ROOT/crates/aionui-ai-agent/src/cc_switch/model_info.rs"  "cc_switch/model_info.rs"
  file_exists "$ROOT/crates/aionui-ai-agent/src/cc_switch/paths.rs"       "cc_switch/paths.rs"
  file_exists "$ROOT/crates/aionui-ai-agent/src/cc_switch/provider_env.rs" "cc_switch/provider_env.rs"

  # POUNDING migration
  file_exists "$ROOT/crates/aionui-db/migrations/013_add_pounding_cli.sql" "013_add_pounding_cli.sql"
  file_exists "$ROOT/crates/aionui-db/migrations/014_native_cli_managed_tools.sql" "014_native_cli_managed_tools.sql"

  # POUNDING builtin skill
  file_exists "$ROOT/crates/aionui-app/assets/builtin-skills/pounding-ozon-assistant" "ozon skill bundle"
  file_exists "$ROOT/crates/aionui-app/assets/builtin-skills/pounding-ozon-assistant"   "ozon assistant skill"

  # Brand assets
  file_exists "$ROOT/crates/aionui-assets/assets/logos/brand/pounding-heart-solid.png" "pounding heart logo"

  # CC-Switch tests
  file_exists "$ROOT/crates/aionui-ai-agent/tests/cc_switch_integration.rs" "cc_switch integration tests"

  # check-branding.sh
  file_exists "$ROOT/scripts/check-branding.sh" "check-branding.sh"

  # POUNDING assistants config
  file_exists "$ROOT/crates/aionui-app/assets/builtin-assistants/assistants.json" "assistants.json"
}

# ----------------------------------------------------------------
# Category 3: Config Verification
# ----------------------------------------------------------------
check_config_values() {
  echo ""
  echo -e "${BLUE}== Category 3: Config Verification (check-branding.sh) ==${NC}"
  if [ -f "$ROOT/scripts/check-branding.sh" ]; then
    echo ""
    bash "$ROOT/scripts/check-branding.sh"
  else
    echo -e "  ${RED}MISS${NC} scripts/check-branding.sh not found"
  fi
}

# ================================================================
# Main
# ================================================================
echo -e "=== POUNDING Branding: $( [ "$MODE" = "check" ] && echo "DRY-RUN" || echo "APPLY" ) ==="
apply_text_replacements
check_feature_files
check_config_values
echo ""
if [ "$MODE" = "check" ]; then
  echo -e "${BLUE}Dry-run complete. Run without --check to apply.${NC}"
elif [ "$COUNT" -gt 0 ]; then
  echo -e "${GREEN}Applied $COUNT branding replacements.${NC}"
else
  echo -e "${BLUE}Branding already applied — nothing to do.${NC}"
fi
