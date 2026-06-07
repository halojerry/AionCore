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

## Release Repo: Sync Strategy

**⚠️ This is a RELEASE repository (`halojerry/poundingcore`). Code comes from the dev repo (`halojerry/AionCore`).**

### Three-Tier Architecture

```
iOfficeAI/AionCore (上游)
    ↓ sync-upstream (AionCore dev repo's workflow)
halojerry/AionCore (开发仓库 — 唯一代码入口)
    ↓ sync-downstream (poundingcore release repo's workflow)
halojerry/poundingcore (发布仓库 — 此仓库，只接收稳定代码)
```

**This release repo must NEVER sync from `iOfficeAI/AionCore` directly.**
All upstream changes must go through `halojerry/AionCore` dev repo first, where POUNDING branding is protected.

### Sync Downstream Process

**Trigger**: Manual `workflow_dispatch` via GitHub Actions → `sync-downstream.yml`.

**What the workflow does**:
1. Validates target branch (blocks `main`/`dev` direct sync)
2. Runs `scripts/check-branding.sh` as a pre-sync gate
3. Fetches from `halojerry/AionCore` (dev repo)
4. Fast-forward merges (`--ff-only`) into target branch (default: `feature/downstream-sync`)
5. Re-runs branding check on the sync result
6. If conflicts or branding failure: job fails, manual resolution required
7. On success: creates a PR for manual review

**Manual steps after sync**:
1. Review the auto-created PR diff
2. Verify `bash scripts/check-branding.sh` passes
3. Run `cargo test -p aionui-assistant` to verify builtin tests
4. Merge PR to `main` only after all checks pass

### Binary Releases

This repo hosts release binaries built by `halojerry/AionCore`'s `release.yml`.
The dev repo builds `poundingcore` binaries and uploads them to this repo's GitHub Releases.
This repo's own `release.yml` is **deprecated** — releases come from the dev repo.

### Rules for all agents:
- Syncs from dev go to `feature/downstream-sync` — NEVER sync dev/main into main directly.
- This repo does NOT have `sync-upstream.yml` — it must never sync from iOfficeAI.
- POUNDING-specific customizations are preserved in the dev repo before syncing here.
- Tag format: `v<version>-Pounding` (e.g. `v0.1.22-Pounding`).
- The AionUi desktop app downloads poundingcore binaries from this repo's releases.

## POUNDING Custom Features

Features unique to the POUNDING release that must be preserved:

| Feature | Key Files / Crates |
|---------|-------------------|
| CC-Switch model routing | `crates/aionui-ai-agent/src/cc_switch/` (mod.rs, model_info.rs, paths.rs, provider_env.rs) |
| POUNDING builtin skill | `crates/aionui-app/assets/builtin-skills/pounding-ozon-assistant/` |
| POUNDING DB migrations | `crates/aionui-db/migrations/010_add_pounding_cli.sql`, `011_add_pounding_cli.sql` |
| Brand logo asset | `crates/aionui-assets/assets/logos/brand/pounding-heart-solid.png` |
| Binary name | Binary name is `poundingcore` (in `crates/aionui-app/Cargo.toml`) |
| CC-Switch integration tests | `crates/aionui-ai-agent/tests/cc_switch_integration.rs` |
| Dev repo source | `halojerry/AionCore` (in `crates/aionui-system/src/version.rs`) |

## POUNDING Branding Checklist

When merging ANY sync from the dev repo, verify these are not overwritten:

- [ ] `010_add_pounding_cli.sql` and `011_add_pounding_cli.sql` migrations exist
- [ ] `cc_switch/` module exists under `aionui-ai-agent/src/`
- [ ] `pounding-ozon-assistant/` builtin skill exists
- [ ] `pounding-heart-solid.png` brand asset exists
- [ ] Binary name is `poundingcore` (NOT `aioncore`)
- [ ] Legacy DB name `aionui.db` preserved in copy/migration functions
- [ ] CC-Switch integration tests pass (`cargo test -p aionui-ai-agent --test cc_switch_integration`)
- [ ] `DEFAULT_REPO` is `halojerry/AionCore` (not `iOfficeAI`)
- [ ] Run `bash scripts/check-branding.sh` before merging
