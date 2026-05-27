# Maintainer Checklist — POUNDING Fork (AionCore)

## 1. Upstream Sync
- [ ] `git fetch upstream`
- [ ] `git checkout upstream-sync/main && git merge upstream/main`
- [ ] Resolve conflicts, push to `origin upstream-sync/main`
- [ ] If needed, merge `upstream-sync/main` into `main`

## 2. Daily Dev
- [ ] Branch from `main` for features: `git checkout main && git checkout -b feat/my-change`
- [ ] PR back to `main` after validation

## 3. Release
- [ ] `git checkout -b release/pounding-v0.1.x main` (from latest `main`)
- [ ] Run: `cargo fmt --all -- --check && cargo clippy --workspace -- -D warnings && cargo nextest run --workspace`
- [ ] Tag and trigger release workflow

## 4. Hotfix
- [ ] Branch from release branch: `fix/critical-bug`
- [ ] PR → release branch, must back-merge to `main`

## Config Check
| Item | Value | Status |
|------|-------|--------|
| upstream mirror | `upstream-sync/main` | ✅ |
| release branch | `release/pounding-v0.1.x` | ✅ |
| CI target | `main` | ✅ |
