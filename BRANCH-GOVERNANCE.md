# Branch Governance — AionCore (POUNDING Fork)

## Phase 1 (current)

| Branch | Role | Base | Merge Direction |
|--------|------|------|----------------|
| `upstream-sync/main` | Upstream mirror | upstream `main` | upstream → `upstream-sync/main` |
| `main` | Team stable integration | `upstream-sync/main` + branding | `feat/*` / `fix/*` → `main` |
| `release/pounding-v0.1.x` | Release freeze / validation | `main` | Validation-only; no feature work |
| `feat/*` | Feature branches | `main` | feature → `main` |
| `fix/*` | Bugfix branches | owning target | fix → owning branch |

## Rules
1. `release/pounding-*` is **validation-only** — no feature work
2. Urgent `fix/*` on release requires approval + merge-back to `main`
3. Upstream intake only via `upstream-sync/main`

## Phase 2 (future)
- AionUi unifies to same model
