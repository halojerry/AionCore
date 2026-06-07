# AGENTS.md

<!-- Maintenance rule: Only add content that tells AI assistants WHAT TO DO or WHAT NOT TO DO.
     Implementation details, design rationale, and "how the system works" belong in ARCHITECTURE.md.
     If a section doesn't contain an actionable rule or constraint, it doesn't belong here. -->

Project-specific rules and conventions for AI assistants and contributors.

## High-Priority Rules

### Do NOT add fields to `AcpAgentManager` unless every alternative is exhausted

`AcpAgentManager` (in `crates/aionui-ai-agent/src/acp_agent.rs`) is already large and carries multiple overlapping state holders (e.g. `runtime_snapshot`, `state`, `preferred_mode`, `config`). New fields tend to duplicate semantics that `AcpRuntimeSnapshot` or `AcpState` already model, which fragments the source of truth and makes resume/new paths diverge.

Before adding a field:
1. Can the value live in `AcpRuntimeSnapshot`? (runtime/session-scoped state, including user-selected current_mode/current_model/config_selections)
2. Can it be derived from existing fields (`metadata`, `config`, `runtime_snapshot`, `state`)?
3. Can it be persisted via `acp_session.session_config` + `preload_persisted` instead of a new in-memory field?
4. If it must be in-memory and transient, can it be scoped to the call site (local variable, channel, task state) rather than the manager?

Only after exhausting the above — and explicitly documenting why each option is insufficient — add a new field. When doing so, also document its lifecycle (who writes, who reads, when it is invalidated) in a doc comment on the field.

### Logging

When planning or changing a critical path or hard-to-observe flow, evaluate whether logging needs to change. In implementation plans for such changes, briefly state whether logs will be added, existing observability is sufficient, or logs are intentionally unnecessary. Do not add logs for simple refactors, test-only changes, UI copy/style changes, or when existing tests, errors, metrics, or logs already provide enough observability.

Add structured logs only when they help verify behavior during development or locate production issues later:
- `debug` for development-only flow details and state transitions
- `info` for low-volume production lifecycle boundaries and important state changes
- `warn` for malformed or unexpected data that is safely handled
- `error` for contract violations or failed operations

Production-visible logs must not include sensitive payloads such as prompts, tool input/output, file contents, command bodies, tokens, secrets, or raw provider requests/responses. If such payloads are needed for local debugging, they must be behind explicit development-only guards and never enabled by default.

## Architecture

> For detailed background and design decisions, see [ARCHITECTURE.md](./ARCHITECTURE.md).

Cargo workspace organized in four layers: Foundation → Capability → Domain → Composition. Dependencies flow strictly downward.

### Crate Hierarchy & Dependencies

- ✅ Upper layers may depend on lower layers (including cross-layer)
- ✅ Same-layer interaction through trait abstractions only
- ❌ No lower-layer depending on upper-layer
- ❌ No circular dependencies
- Changes to foundation crates require impact assessment

### Domain Crate Structure

Every domain crate must follow:
- `lib.rs` — module exports only, no business logic
- `routes.rs` — export `domain_routes(state) -> Router`, handlers do request/response transformation only
- `service.rs` — sole location for business logic, must not import axum
- `state.rs` — `#[derive(Clone)]` RouterState holding Arc-wrapped dependencies

### API Conventions

- Route prefix: `/api/`
- Resource names: kebab-case
- Response format: `ApiResponse<T>` (success) / `ErrorResponse` (failure)
- All request/response types defined in `aionui-api-types`
- `aionui-api-types` must NOT depend on axum/tower or any HTTP framework
- Use `aionui_common::ApiError` only at API/HTTP boundaries such as routes and middleware. Service/domain code must prefer crate-owned errors (`ConversationError`, `TeamError`, etc.) and map them to `ApiError` in route modules. Do not introduce new `AppError` usages; it exists only as a temporary compatibility alias.

### WebSocket Events

- Format: `domain.camelCaseAction` (two-level structure)
- Message type: `WebSocketMessage<T>` (name + data)
- Existing kebab-case or three-level names are legacy — new events must follow the convention

### Data Layer

- Repository traits in `aionui-db`, prefixed with `I`
- Concrete implementations prefixed with `Sqlite`
- Row models in `aionui-db/src/models/`
- Params objects co-located in repository files
- Migrations: `NNN_descriptive_name.sql`, no manual DB modifications
- Services depend on traits, never on concrete implementations

### Dependency Injection

- `AppServices` is the sole service construction center
- Domain crates only define RouterState, never construct their own dependencies
- All assembly happens in `aionui-app`'s `build_*_state()` functions

### Security

- New endpoints must be evaluated for auth middleware requirement
- State-changing operations must be CSRF-protected
- Sensitive operations should have rate limiting
- Error responses must not leak internal details
- Secrets must never be hardcoded

## Code Style

- Rust 2024 edition, stable toolchain (pinned in `rust-toolchain.toml`)
- Comments in English, commit messages in English
- Each `.rs` file follows single responsibility — one module, one concern
- Max 1000 lines per `.rs` file; split into submodules when approaching the limit

## Development Workflow

### Subprocess Spawning

New subprocess spawn sites must use `aionui_runtime::Builder::agent(program)` or `aionui_runtime::Builder::clean_cli(program)`. Do NOT use raw `tokio::process::Command`. See [ARCHITECTURE.md § Runtime Infrastructure](./ARCHITECTURE.md#runtime-infrastructure) for details.

### Pushing Code

Always use `just push` instead of `git push`.
It runs fmt → clippy → test before pushing, preventing CI failures.
Supports the same arguments as `git push` (e.g. `just push -u origin feat/branch`).

### Add Endpoint to Existing Crate

1. Request/response types → `aionui-api-types/src/{domain}.rs`
2. Handler function → `crates/aionui-{domain}/src/routes.rs`
3. Business logic → `crates/aionui-{domain}/src/service.rs`
4. Register route in `domain_routes()` function
5. Add test → `crates/aionui-{domain}/tests/` or `crates/aionui-app/tests/`

### Add Migration

1. Next number → `ls crates/aionui-db/migrations/`
2. Create `NNN_descriptive_name.sql` with `IF NOT EXISTS`

### Add WebSocket Event

1. Event type → `aionui-api-types`
2. Emit via `event_bus.broadcast()` in service
3. Naming: `domain.camelCaseAction`

## Test Organization

| Location                                 | What goes there                        |
| ---------------------------------------- | -------------------------------------- |
| Inline `#[cfg(test)]` in each `.rs` file | Unit tests for that module's internals |
| `crates/<crate>/tests/`                  | Integration / E2E tests for that crate |

### Testing Rules

- Database tests use `init_database_memory()`
- Prefer real in-memory DB over mocks; mock only to isolate unneeded dependencies
- New features must include tests

### Test Scope Requirements

**Happy Path (Critical Paths)**

Every new or modified feature must have integration tests covering its normal flow. Critical paths that always require test coverage:
- Authentication flow (login, token refresh, permission checks)
- Message sending and retrieval
- Agent session creation and interaction
- File upload/download
- WebSocket connection and event delivery

**Bad Path (Error Paths)**

New endpoints or business logic must include tests for these scenarios:
- Invalid input (missing fields, wrong types, oversized content)
- Resource not found (404)
- Insufficient permissions (unauthenticated, accessing another user's resources)
- Business rule violations (duplicate creation, operations not allowed in current state)

Bad path tests must assert specific error codes or error messages — asserting merely "not success" is not acceptable.

**Security Tests**

Endpoints involving authentication, authorization, or data isolation must include security tests:
- Unauthenticated requests are rejected (401)
- Cross-user data isolation (user A cannot access user B's resources)
- State-changing requests are rejected when CSRF token is missing or invalid
- Sensitive fields (passwords, tokens) never appear in responses

**WebSocket Event Tests**

New WebSocket events must verify:
- The event is emitted after the correct business operation
- Event payload conforms to `WebSocketMessage<T>` structure
- Events are only delivered to authorized subscribers (no leakage to unrelated users)

### Test Failure Handling

When a test fails, do NOT modify the test to make it pass. First determine:

1. **Test assertion still represents correct behavior** → fix implementation, not the test
2. **Requirements/interface intentionally changed** → may update test, but must confirm:
   - The change is intentional (not an unintended side effect)
   - New assertions still validate meaningful behavior
3. **Uncertain** → stop, trace back the change, clarify before proceeding

Prohibited:
- ❌ Deleting failing tests to "fix" the problem
- ❌ Weakening specific assertions to vague ones (e.g., `assert_eq!(status, 201)` → `assert!(status.is_success())`)

## Verification Strategy

> ⚠️ **When to run what:**
> - During development: only test the crate you're working on → `cargo test -p aionui-<crate>`
> - After implementation complete: full verification → `cargo test --workspace`
> - Do NOT run `cargo test --workspace` at the start of a task.
>
> ⚠️ **Performance:**
> - `cargo clippy --workspace` takes several minutes — use `run_in_background: true`.
> - `cargo test --workspace` takes 10+ minutes. MUST use `run_in_background: true` when calling via Bash tool, otherwise it will timeout.
> - `cargo clippy -p aionui-<crate>` and `cargo test -p aionui-<crate>` typically complete in under 1 minute.

### During Development (fast feedback loop)

```bash
cargo test -p aionui-<crate>                          # Test the crate you changed
cargo clippy -p aionui-<crate> -- -D warnings         # Lint the crate you changed
```

### Before Commit (affected crates)

```bash
cargo fmt --all -- --check                                                      # Format gate (instant)
cargo clippy -p aionui-<crate1> -p aionui-<crate2> -- -D warnings              # Lint affected crates
cargo test -p aionui-<crate1> -p aionui-<crate2>                               # Test affected crates
```

### Before Push (full workspace)

```bash
just push                                             # fmt → clippy → test → git push
```

## POUNDING Fork: Branch Strategy

### Three-Tier Repository Structure

```
iOfficeAI/AionCore (上游)
    ↓ sync-upstream (此仓库的 workflow)
halojerry/AionCore (开发仓库 — 此仓库，POUNDING 保护层)
    ↓ sync-downstream (poundingcore 发布仓库的 workflow)
halojerry/poundingcore (发布仓库 — 最终产物，二进制发布)
```

**`halojerry/poundingcore` 是最终发布仓库**，只接收 `halojerry/AionCore` 的稳定代码。
**永远不要**从 `iOfficeAI/AionCore` 直接同步到 `halojerry/poundingcore`。

### Sync Downstream (Dev → Release)

代码从开发仓库同步到发布仓库由 `halojerry/poundingcore` 的 `sync-downstream.yml` 负责。
该 workflow 从 `halojerry/AionCore`（此仓库）拉取代码，经过 branding 检查后创建 PR。

**触发方式**: 在 `halojerry/poundingcore` 仓库手动 `workflow_dispatch` → `sync-downstream.yml`。

**流程**:
1. 验证目标分支（阻止直接同步到 main/dev）
2. 运行 `check-branding.sh` 作为预检门禁
3. Fast-forward 合并到 `feature/downstream-sync` 分支
4. 再次运行 branding 检查
5. 创建 PR 供人工审核

**发布仓库永远不直接从 iOfficeAI 同步** — 所有上游变更必须先经过此开发仓库处理。

**main is the stable POUNDING release branch. NEVER merge upstream directly into main.**

```
upstream (iOfficeAI/AionCore)
    ↓ manual fetch to feature branch
feature/upstream-sync
    ↓ manual PR (resolve conflicts, preserve POUNDING customizations)
dev (integration & verification)
    ↓
release/pounding-v*.*.x (final verification)
    ↓
main (stable — triggers release builds via tag)
```

**Rules for all agents:**
- Upstream syncs go to `feature/upstream-sync` — NEVER merge upstream into `main` or `dev` directly.
- After upstream sync, manually diff and restore all POUNDING customizations (see checklist below).
- POUNDING-specific features are developed on `feature/*` branches, PR'd to `dev`.
- Tag format: `v<version>-Pounding` (e.g. `v0.1.15-Pounding`).
- The AionUi desktop app uses this AionCore binary as its backend — version pinning is in AionUi's root `package.json` (`aioncoreVersion` field, value is a poundingcore release tag).

### Upstream Sync Process (detailed)

**Trigger**: Manual `workflow_dispatch` via GitHub Actions → `sync-upstream.yml`.

The `sync-upstream.yml` workflow blocks direct sync to `main`/`dev` via its `validate` job. Always use `feature/upstream-sync` as the target branch.

**What the workflow does automatically**:
1. Fetches from `iOfficeAI/AionCore` upstream
2. Fast-forward merges (`--ff-only`) into target branch (default: `main` — **override this!**)
3. If conflicts: job fails, manual resolution required
4. On success: creates a PR from sync branch with upstream commit summary

**Manual steps after sync (MANDATORY)**:
1. Check the auto-created PR diff — look for POUNDING customization overwrites
2. Run `bash scripts/check-branding.sh` locally
3. Run `cargo test -p aionui-assistant` to verify builtin assistant tests
4. Restore ALL items in the Branding Checklist below that were overwritten
5. Pay special attention to: `Cargo.toml` binary name (`poundingcore`), `cc_switch/` module, builtin skill directory, DB migrations
6. Rebuild and smoke-test: `cargo build --release -p aionui-app`
7. Delete runtime cache before testing: `rm -rf ~/Library/Application\ Support/POUNDING-Dev/pounding/builtin-skills/`
8. Merge PR to `dev` only after all checks pass

**Known pitfalls**:
- `Cargo.toml` binary name may revert to `aioncore` — check `crates/aionui-app/Cargo.toml`
- `cc_switch/` module files may be deleted or overwritten by upstream refactors
- Builtin skill directory name in AGENTS.md may be outdated (`pounding-ozon-v0.1.0-lite` → `pounding-ozon-assistant`)
- DB migration numbers may shift as upstream adds new migrations — verify POUNDING migrations still exist
- Asset file changes (skills) require `build.rs` recompile trigger + runtime cache deletion (see Troubleshooting)
- The `bundled-poundingcore/` directory name in AionUi must match `binaryResolver.ts`

**Before merging to main (release)**:
- Tag: `v<version>-Pounding`
- This builds the `poundingcore` binary that AionUi packages

## POUNDING Custom Features

Features unique to the POUNDING fork that must be preserved during upstream syncs:

| Feature | Key Files / Crates |
|---------|-------------------|
| CC-Switch model routing | `crates/aionui-ai-agent/src/cc_switch/` (mod.rs, model_info.rs, paths.rs, provider_env.rs) |
| POUNDING builtin skill | `crates/aionui-app/assets/builtin-skills/pounding-ozon-v0.1.0-lite/` |
| POUNDING DB migration | `crates/aionui-db/migrations/007_add_pounding_cli.sql` |
| Brand logo asset | `crates/aionui-assets/assets/logos/brand/pounding-heart-solid.png` |
| Binary name | Binary name is `poundingcore` |
| CC-Switch integration tests | `crates/aionui-ai-agent/tests/cc_switch_integration.rs` |

## POUNDING Branding Checklist

When merging ANY upstream changes, verify these are not overwritten:

- [ ] `007_add_pounding_cli.sql` migration exists
- [ ] `cc_switch/` module exists under `aionui-ai-agent/src/`
- [ ] `pounding-ozon-v0.1.0-lite/` builtin skill exists
- [ ] `pounding-heart-solid.png` brand asset exists
- [ ] Binary name is `poundingcore`
- [ ] Legacy DB name `aionui.db` preserved in copy/migration functions
- [ ] CC-Switch integration tests pass (`cargo test -p aionui-ai-agent --test cc_switch_integration`)

## Troubleshooting & Lessons Learned

Lessons from POUNDING development sessions. When debugging similar symptoms, check these first.

### EIO fix compilation error: `AcpError::Disconnected` has no field `message`

**Symptom**: `cargo build` fails with E0559 after EIO crash-guard changes.

**Root cause**: `agent_session_flow.rs:255` used `message:` but the `AcpError::Disconnected` variant (defined in `error.rs:103-107`) uses `stderr:`.

**Fix**: Changed `message:` → `stderr:`.

**Key files**: `crates/aionui-ai-agent/src/manager/acp/agent_session_flow.rs`, `crates/aionui-ai-agent/src/protocol/error.rs`

### Duplicate assistants: "Ozon Assistants" + "POUNDING Ozon Assistant"

**Symptom**: Two Ozon assistant entries appear in the UI.

**Root cause**: `assistants.json` had both legacy `ozon-assistants` (lite skill, emoji avatar) and new `pounding-ozon-assistant` (hybrid skill, branded avatar, officecli skills, preset:true). Both were registered as builtins.

**Fix**: Removed the legacy `ozon-assistants` entry from `assistants.json`. Updated Rust tests in `builtin.rs` and `service.rs` to reference `pounding-ozon-assistant`. Deleted orphaned `pounding-ozon-v0.1.0-lite/` skill bundle and `rules/ozon-assistants.zh-CN.md`.

**Key files**: `crates/aionui-app/assets/builtin-assistants/assistants.json`, `crates/aionui-assistant/src/builtin.rs`, `crates/aionui-assistant/src/service.rs`

### Skill updates not taking effect after rebuild

**Symptom**: Updated files in `crates/aionui-app/assets/builtin-skills/pounding-ozon-assistant/`, rebuilt with `cargo build --release`, but `bun run dev` still serves old skill version.

**Root cause (two locks)**:
1. **Incremental compilation blind spot**: `aionui-extension` crate uses `include_dir!` to embed `builtin-skills/` but had no `build.rs` with `cargo:rerun-if-changed`. Cargo only tracked `.rs` file changes, not asset file changes — so `include_dir!` was never re-evaluated.
2. **Runtime version-gated cache**: At startup, `startup_materialize.rs` extracts embedded skills to `{data_dir}/builtin-skills/`. A `.version` file (containing `CARGO_PKG_VERSION`) gates this: if the binary version matches the cache version, extraction is **skipped**. Updating skill content without bumping `Cargo.toml` version means the cache is never refreshed.

**Fix**: (a) Created `crates/aionui-extension/build.rs` with `cargo:rerun-if-changed=../aionui-app/assets/builtin-skills`; (b) Deleted the runtime cache directory to force re-extraction; (c) `touch`ed `asset_paths.rs` to force recompilation.

**Key files**: `crates/aionui-extension/build.rs`, `crates/aionui-app/src/bootstrap/startup_materialize.rs`, `crates/aionui-extension/src/asset_paths.rs`

**Runtime cache location**: `~/Library/Application Support/POUNDING-Dev/pounding/builtin-skills/` (macOS dev)

### Masked API key in config.json

**Symptom**: `~/.pounding/config.json` contains a masked/redacted key (`sk-***abcd`) that skills cannot use for LLM calls.

**Root cause**: `resolveManagedToken` in `NewApiDesktopAccountService.ts` had a fallback path: if `fetchFullTokenKey` failed, it fell back to `extractToken(existingChannelConnection)`, which could return a masked key from the token list response.

**Fix**: (a) Added `isMaskedToken()` guard (checks for `***`/`...`); (b) Removed the masked fallback from `resolveManagedToken` — if no full key is available, create a new token; (c) Added `isMaskedToken` guard to `writePoundingConfig` to never persist a masked key.

**Note**: This code lives in the AionUi desktop app (`NewApiDesktopAccountService.ts`), not in AionCore.

### Stale database causes 403 on `/api/providers` with `--local`

**Symptom**: `bun run dev` login shows 403 despite backend running with `--local` flag (which should skip auth).

**Root cause**: Stale `pounding-backend.db` files from earlier manual testing (without `--local`) had partially-set-up auth state (`needs_setup: true, user_count: 1`). The `--local` flag auto-creates a default user, but a stale DB with a different auth state overrides this behavior.

**Fix**: Deleted the 3 stale database files: `AionCore/data/pounding-backend.db`, `~/Library/Application Support/POUNDING-Dev/aionui/pounding-backend.db`, `~/Library/Application Support/POUNDING-Dev/pounding/pounding-backend.db`.

### `bundled-aioncore` vs `bundled-poundingcore` directory mismatch

**Symptom**: `bun run dev` falls back to system PATH binary instead of using the freshly-built bundled binary.

**Root cause**: The `binaryResolver.ts` code looks for `bundled-poundingcore/` (POUNDING branded), but the actual directory on disk was still named `bundled-aioncore` (upstream name). The resolver fell through to system PATH, which had a stale symlink to `target/debug/poundingcore`.

**Fix**: Renamed `resources/bundled-aioncore/` → `resources/bundled-poundingcore/`. Updated `~/.local/bin/poundingcore` symlink to point to `target/release/poundingcore`.

