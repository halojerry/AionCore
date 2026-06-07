#!/usr/bin/env bash
# scripts/check-branding.sh
#
# Verify POUNDING branding is preserved in the poundingcore RELEASE repo.
# Run this before merging any sync PR from the dev repo.
#
# This release repo receives code from halojerry/AionCore (dev).
# It must NEVER sync from iOfficeAI directly.
#
# Exit 0 = all checks pass, Exit 1 = branding violations found.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
ERRORS=()

check() {
  local label="$1"
  local pattern="$2"
  local file="$3"
  local context="${4:-}"

  if [ ! -e "$file" ]; then
    echo -e "${RED}FAIL${NC} $label: not found — $file"
    FAIL=$((FAIL + 1))
    ERRORS+=("$label: not found: $file")
    return
  fi

  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC} $label"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}FAIL${NC} $label — expected pattern not found in $file"
    if [ -n "$context" ]; then
      echo -e "  ${YELLOW}context: $context${NC}"
    fi
    FAIL=$((FAIL + 1))
    ERRORS+=("$label: pattern '$pattern' not found in $file")
  fi
}

check_exists() {
  local label="$1"
  local path="$2"

  if [ -e "$path" ]; then
    echo -e "${GREEN}PASS${NC} $label"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}FAIL${NC} $label: not found — $path"
    FAIL=$((FAIL + 1))
    ERRORS+=("$label: not found: $path")
  fi
}

check_not_exists() {
  local label="$1"
  local path="$2"

  if [ ! -e "$path" ]; then
    echo -e "${GREEN}PASS${NC} $label"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}FAIL${NC} $label: should not exist — $path"
    FAIL=$((FAIL + 1))
    ERRORS+=("$label: should not exist: $path")
  fi
}

echo "=== POUNDING Core Release Repo Branding Check ==="
echo ""

# ---- Binary Name ----
check "Cargo.toml: binary name poundingcore" 'name[[:space:]]*=[[:space:]]*"poundingcore"' "$ROOT/crates/aionui-app/Cargo.toml"

# ---- CC-Switch Module ----
check_exists "cc_switch module" "$ROOT/crates/aionui-ai-agent/src/cc_switch/mod.rs"
check_exists "cc_switch model_info" "$ROOT/crates/aionui-ai-agent/src/cc_switch/model_info.rs"
check_exists "cc_switch paths" "$ROOT/crates/aionui-ai-agent/src/cc_switch/paths.rs"
check_exists "cc_switch provider_env" "$ROOT/crates/aionui-ai-agent/src/cc_switch/provider_env.rs"

# ---- Builtin Skills ----
check_exists "pounding-ozon-assistant skill" "$ROOT/crates/aionui-app/assets/builtin-skills/pounding-ozon-assistant/SKILL.md"

# ---- Brand Logo Asset ----
check_exists "pounding heart logo" "$ROOT/crates/aionui-assets/assets/logos/brand/pounding-heart-solid.png"

# ---- POUNDING CLI Migrations ----
check "pounding CLI migration 1" 'pounding' "$ROOT/crates/aionui-db/migrations/010_add_pounding_cli.sql"
check "pounding CLI migration 2" 'pounding' "$ROOT/crates/aionui-db/migrations/011_add_pounding_cli.sql"

# ---- Legacy DB Name Preserved ----
check "database.rs: aionui.db preserved" 'aionui\.db' "$ROOT/crates/aionui-db/src/database.rs"

# ---- CC-Switch Integration Tests ----
check_exists "cc_switch integration tests" "$ROOT/crates/aionui-ai-agent/tests/cc_switch_integration.rs"

# ---- Release Repo Safety: NO sync-upstream.yml (should not sync from iOfficeAI) ----
check_not_exists "no sync-upstream.yml (release repo must NOT sync from iOfficeAI)" "$ROOT/.github/workflows/sync-upstream.yml"

# ---- Must have sync-downstream.yml ----
check_exists "sync-downstream.yml exists" "$ROOT/.github/workflows/sync-downstream.yml"
check "sync-downstream.yml: source is halojerry/AionCore" 'halojerry/AionCore' "$ROOT/.github/workflows/sync-downstream.yml"

# ---- Repo Config ----
check "version.rs: DEFAULT_REPO is halojerry" 'halojerry/AionCore' "$ROOT/crates/aionui-system/src/version.rs"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo -e "${RED}Branding violations found:${NC}"
  for err in "${ERRORS[@]}"; do
    echo -e "  ${RED}•${NC} $err"
  done
  exit 1
fi

echo -e "${GREEN}All branding checks passed.${NC}"
