#!/usr/bin/env bash
# scripts/test-apply-branding.sh
#
# Test that apply-branding.sh correctly restores POUNDING branding for text replacements.
# Full file-existence and config checks require the complete repo structure;
# this test focuses on Category 1 (text replacements) which is the critical path.
#
# Usage:
#   bash scripts/test-apply-branding.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR=$(mktemp -d /tmp/poundingcore-branding-test-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Test: apply-branding.sh (AionCore) ===${NC}"
echo ""

# Step 1: Copy key branding files
echo "Step 1: Copying source files..."
mkdir -p "$TMPDIR/crates/aionui-app"
mkdir -p "$TMPDIR/crates/aionui-system/src"
mkdir -p "$TMPDIR/crates/aionui-app/src/router"
mkdir -p "$TMPDIR/scripts"

cp "$ROOT/crates/aionui-app/Cargo.toml"         "$TMPDIR/crates/aionui-app/" 2>/dev/null || true
cp "$ROOT/crates/aionui-system/src/version.rs"   "$TMPDIR/crates/aionui-system/src/" 2>/dev/null || true
cp "$ROOT/crates/aionui-app/src/router/state.rs" "$TMPDIR/crates/aionui-app/src/router/" 2>/dev/null || true
echo "  Files copied to $TMPDIR"

# Step 2: Revert to upstream branding (simulate post-sync state)
echo ""
echo "Step 2: Reverting to upstream branding..."
find "$TMPDIR" -type f | while IFS= read -r f; do
  sed -i '' \
    -e 's|poundingcore|aioncore|g' \
    -e 's|pounding|aionui|g' \
    -e 's|POUNDING|AionUi|g' \
    -e 's|halojerry|iOfficeAI|g' \
    "$f" 2>/dev/null || true
done

# Verify reversion
if grep -q 'name = "aioncore"' "$TMPDIR/crates/aionui-app/Cargo.toml" 2>/dev/null; then
  echo -e "  ${GREEN}OK${NC}   reverted binary name"
else
  echo -e "  ${RED}FAIL${NC} could not revert binary name"
  exit 1
fi

# Step 3: Run apply-branding.sh
echo ""
echo "Step 3: Running apply-branding.sh..."
cp "$ROOT/scripts/apply-branding.sh" "$TMPDIR/scripts/"
(cd "$TMPDIR" && bash "$TMPDIR/scripts/apply-branding.sh" 2>&1 | head -20) || {
  echo -e "${RED}FAIL: apply-branding.sh returned non-zero${NC}"
  exit 1
}

# Step 4: Verify text replacements
echo ""
echo "Step 4: Verifying key text replacements..."
FAILS=0

check_str() {
  local file="$1" pattern="$2" label="$3"
  if [ -f "$file" ] && grep -q "$pattern" "$file" 2>/dev/null; then
    echo -e "  ${GREEN}PASS${NC} $label"
  else
    echo -e "  ${RED}FAIL${NC} $label"
    FAILS=$((FAILS + 1))
  fi
}

check_str "$TMPDIR/crates/aionui-app/Cargo.toml" 'name = "poundingcore"' "binary name → poundingcore"
check_str "$TMPDIR/crates/aionui-system/src/version.rs" '"poundingcore"' "user-agent → poundingcore"
check_str "$TMPDIR/crates/aionui-app/src/router/state.rs" '"poundingcore"' "data dir → poundingcore"

echo ""
if [ "$FAILS" -eq 0 ]; then
  echo -e "${GREEN}=== PASS: apply-branding.sh correctly restored Category 1 branding ===${NC}"
  echo -e "${BLUE}(Category 2 & 3 require full repo — run check-branding.sh separately)${NC}"
else
  echo -e "${RED}=== FAIL: $FAILS branding check(s) failed ===${NC}"
  exit 1
fi
