use std::fs;
use std::path::Path;
use std::sync::Arc;

use crate::agent_task::AgentInstance;
use crate::factory::AgentFactoryDeps;
use crate::factory::acp_assembler::{WorkspaceInfo, assemble_acp_params};
use crate::factory::context::FactoryContext;
use crate::manager::acp::{AcpAgentManager, CatalogForwarder};
use crate::types::BuildTaskOptions;
use aionui_api_types::AcpBuildExtra;
use aionui_common::{AppError, CommandSpec};
use tracing::{debug, info, warn};

fn ensure_managed_claude_wrapper(data_dir: &Path, claude_path: &Path) -> Result<String, AppError> {
    let wrapper_dir = data_dir.join("managed-runtime").join("claude");
    fs::create_dir_all(&wrapper_dir)
        .map_err(|e| AppError::Internal(format!("Failed to create Claude wrapper dir: {e}")))?;

    let wrapper_path = if cfg!(windows) {
        wrapper_dir.join("claude-bare-wrapper.cmd")
    } else {
        wrapper_dir.join("claude-bare-wrapper.sh")
    };

    let script = if cfg!(windows) {
        format!("@echo off\r\n\"{}\" --bare %*\r\n", claude_path.display())
    } else {
        format!("#!/bin/sh\nexec {} --bare \"$@\"\n", shell_escape_path(claude_path))
    };

    fs::write(&wrapper_path, script).map_err(|e| AppError::Internal(format!("Failed to write Claude wrapper: {e}")))?;

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(&wrapper_path)
            .map_err(|e| AppError::Internal(format!("Failed to stat Claude wrapper: {e}")))?
            .permissions();
        perms.set_mode(0o755);
        fs::set_permissions(&wrapper_path, perms)
            .map_err(|e| AppError::Internal(format!("Failed to chmod Claude wrapper: {e}")))?;
    }

    Ok(wrapper_path.to_string_lossy().into_owned())
}

fn shell_escape_path(path: &Path) -> String {
    let raw = path.to_string_lossy();
    format!("'{}'", raw.replace('\'', "'\''"))
}

/// Ensure OpenCode's managed config directory and config file exist,
/// then return the env vars that redirect OpenCode to the managed
/// paths instead of the OS default `~/.config/opencode/`.
///
/// This is a belt-and-suspenders complement to the shell shim written
/// by the AionUi desktop layer (`writeOpencodeShim`).  The shim
/// intercepts terminal launches; this function guarantees that
/// AionCore-spawned OpenCode processes also use the managed config,
/// even when the shim is missing or PATH bypasses it.
fn ensure_managed_opencode_env(data_dir: &Path) -> Result<Vec<aionui_common::EnvVar>, AppError> {
    let opencode_config_dir = data_dir.join("managed-opencode");
    let opencode_config_path = opencode_config_dir.join("opencode.json");
    let xdg_config_home = data_dir.join("xdg-config");
    let opencode_xdg_dir = xdg_config_home.join("opencode");

    fs::create_dir_all(&opencode_config_dir)
        .map_err(|e| AppError::Internal(format!("Failed to create managed OpenCode config dir: {e}")))?;
    fs::create_dir_all(&opencode_xdg_dir)
        .map_err(|e| AppError::Internal(format!("Failed to create managed OpenCode XDG dir: {e}")))?;
    if !opencode_config_path.exists() {
        fs::write(&opencode_config_path, "{}\n")
            .map_err(|e| AppError::Internal(format!("Failed to write managed OpenCode config: {e}")))?;
    }

    Ok(vec![
        aionui_common::EnvVar {
            name: "OPENCODE_CONFIG".into(),
            value: opencode_config_path.to_string_lossy().into_owned(),
        },
        aionui_common::EnvVar {
            name: "XDG_CONFIG_HOME".into(),
            value: xdg_config_home.to_string_lossy().into_owned(),
        },
    ])
}

pub(super) async fn build(
    deps: Arc<AgentFactoryDeps>,
    options: BuildTaskOptions,
    ctx: FactoryContext,
) -> Result<AgentInstance, AppError> {
    let belongs_to_team = options
        .extra
        .get("teamId")
        .and_then(serde_json::Value::as_str)
        .is_some_and(|s| !s.is_empty());

    let mut config: AcpBuildExtra = serde_json::from_value(options.extra)
        .map_err(|e| AppError::BadRequest(format!("Invalid ACP build options: {e}")))?;

    // Resolve the catalog row — prefer explicit agent_id, fall
    // back to a vendor-label match for legacy payloads.
    let meta = if let Some(ref agent_id) = config.agent_id {
        deps.agent_registry.get(agent_id).await
    } else if let Some(ref vendor) = config.backend {
        deps.agent_registry.find_builtin_by_backend(vendor).await
    } else {
        None
    }
    .ok_or_else(|| AppError::BadRequest("ACP agent requires either agent_id or backend in extra".into()))?;

    // Trust the catalog row over the client-supplied `backend` when an
    // `agent_id` was provided. The frontend collapses row-scoped rows
    // (custom ACP / remote) to a shared `custom`/`remote` slot string,
    // which downstream consumers (MCP injection, preset-context
    // composition) would mis-interpret. When the caller only supplied a
    // vendor label (builtin path), we preserve it as-is.
    if config.agent_id.is_some() || config.backend.is_none() {
        config.backend.clone_from(&meta.backend);
    }

    // Inject Guide MCP config for solo (non-team) sessions.
    // Team sessions already carry `team_mcp_stdio_config`; the
    // two are mutually exclusive per the build_new_session_request guard.
    if config.team_mcp_stdio_config.is_some() {
        debug!(ctx.conversation_id, "guide_mcp: skipped: has team_mcp");
    } else if belongs_to_team {
        debug!(
            ctx.conversation_id,
            "guide_mcp: skipped: conversation belongs to a team (extra.teamId)"
        );
    } else if config.guide_mcp_config.is_some() {
        debug!(
            ctx.conversation_id,
            "guide_mcp: skipped: caller already set guide_mcp_config"
        );
    } else if deps.guide_mcp_config.is_none() {
        debug!(ctx.conversation_id, "guide_mcp: skipped: guide server not running");
    } else {
        config.guide_mcp_config.clone_from(&deps.guide_mcp_config);
        info!(
            ctx.conversation_id,
            guide_mcp_port = deps.guide_mcp_config.as_ref().map(|c| c.port),
            "guide_mcp: injected into solo session"
        );
    }

    // Registry resolved the spawn command via `which()` at
    // hydrate time. A missing `resolved_command` means either the
    // CLI was uninstalled between hydrate and now, or the row
    // never had a command (e.g. remote-only). Either way the
    // caller needs to see a BadRequest, not a confusing
    // spawn-time error.
    let (command, args, mut env, cwd) = (
        meta.resolved_command
            .clone()
            .ok_or_else(|| AppError::BadRequest(format!("Agent '{}' CLI not found in PATH", meta.name)))?,
        meta.args.clone(),
        meta.env
            .iter()
            .map(|e| aionui_common::EnvVar {
                name: e.name.clone(),
                value: e.value.clone(),
            })
            .collect::<Vec<_>>(),
        Some(ctx.workspace.clone()),
    );
    if meta.backend.as_deref() == Some("claude") {
        let cc_switch_env = crate::cc_switch::read_claude_provider_env();
        if !cc_switch_env.is_empty() {
            // Filter out model-level env vars that would crash Claude's ACP agent.
            // Claude's ACP implementation expects Anthropic model IDs; injecting
            // managed/third-party model names (e.g. ANTHROPIC_DEFAULT_SONNET_MODEL)
            // causes exit-code-1 failures. Model routing is handled by the managed
            // API endpoint, not by Claude's config.
            // Matches the same set as CLAUDE_MODEL_ENV_KEYS in
            // NewApiDesktopAccountService.ts.
            let is_model_key = |name: &str| -> bool {
                name == "ANTHROPIC_MODEL" || name.starts_with("ANTHROPIC_DEFAULT_") && name.ends_with("_MODEL")
            };
            let filtered_count = cc_switch_env.keys().filter(|k| is_model_key(k)).count();
            let injected_keys: Vec<&str> = cc_switch_env
                .keys()
                .filter(|k| !is_model_key(k))
                .map(|k| k.as_str())
                .collect();
            if filtered_count > 0 {
                tracing::info!(count = filtered_count, "cc-switch: filtered ANTHROPIC_*_MODEL env keys");
            }
            for (name, value) in &cc_switch_env {
                if is_model_key(name) {
                    continue;
                }
                env.push(aionui_common::EnvVar {
                    name: name.clone(),
                    value: value.clone(),
                });
            }
            tracing::info!(?injected_keys, "cc-switch: env vars injected");

            let claude_cli = Path::new(&command);
            if let Ok(wrapper) = ensure_managed_claude_wrapper(&deps.data_dir, claude_cli) {
                env.push(aionui_common::EnvVar {
                    name: "CLAUDE_CODE_EXECUTABLE".into(),
                    value: wrapper,
                });
                tracing::info!(
                    cli = %claude_cli.display(),
                    "cc-switch: managed Claude wrapper injected"
                );
            } else {
                warn!(cli = %claude_cli.display(), "cc-switch: failed to inject managed Claude wrapper");
            }
        }
    }

    // OpenCode: inject managed OPENCODE_CONFIG / XDG_CONFIG_HOME so
    // AionCore-spawned opencode processes always use the managed config
    // path, even when the shell shim is missing or PATH bypasses it.
    if meta.backend.as_deref() == Some("opencode") {
        for ev in ensure_managed_opencode_env(&deps.data_dir)? {
            env.push(ev);
        }
        tracing::info!("opencode: managed config env vars injected");
    }

    let command_spec = CommandSpec {
        command,
        args,
        env,
        cwd,
    };
    let session_snapshot = deps.acp_agent_service.load_snapshot_state(&ctx.conversation_id).await;

    let params = Arc::new(
        assemble_acp_params(
            ctx.conversation_id.clone(),
            WorkspaceInfo {
                path: ctx.workspace,
                is_custom: ctx.is_custom_workspace,
            },
            meta,
            command_spec,
            config,
            Vec::new(),
            session_snapshot,
            deps.data_dir.clone(),
        )
        .await,
    );

    let skill_mgr = deps.skill_manager.clone();
    let catalog_tx = deps.agent_registry.catalog_sender();

    let (agent, domain_rx, notification_rx) = AcpAgentManager::build(params, skill_mgr, &catalog_tx).await?;

    let arc = Arc::new(agent);
    arc.start_permission_handler();
    arc.start_session_event_tracker(notification_rx);
    CatalogForwarder::spawn(
        arc.agent_id().to_owned(),
        crate::IAgentTask::subscribe(arc.as_ref()),
        catalog_tx,
    );

    // Desired (mode/model/config) are seeded from `params.session_snapshot`
    // inside `AcpAgentManager::new`. The CLI-assigned session id is still
    // loaded here so the first turn after a task rebuild takes the resume
    // path.
    if let Some(sid) = deps.acp_agent_service.load_session_id(&ctx.conversation_id).await {
        arc.set_session_id(sid).await;
    }

    // Open the ACP session eagerly so `POST /warmup` returns only after
    // session/new (or claude-meta-resume / session/load) and the first
    // reconcile pass have completed. Matches aionrs factory behaviour:
    // the caller sees "warmed up" == "ready for PUT /mode | /model".
    arc.warmup_session().await?;

    let instance = AgentInstance::Acp(Arc::clone(&arc));

    // Hand the service the domain event receiver so it can
    // persist user intent changes without reverse-engineering
    // them from CLI observations.
    deps.acp_agent_service.attach(ctx.conversation_id, domain_rx).await;

    Ok(instance)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn ensure_managed_claude_wrapper_writes_bare_wrapper_script() {
        let dir = tempdir().unwrap();
        let claude_path = dir.path().join("claude's-bin");
        let wrapper = ensure_managed_claude_wrapper(dir.path(), &claude_path).unwrap();
        let content = fs::read_to_string(&wrapper).unwrap();

        assert_eq!(
            content,
            format!("#!/bin/sh\nexec {} --bare \"$@\"\n", shell_escape_path(&claude_path)),
        );
    }

    #[test]
    fn ensure_managed_opencode_env_writes_managed_config_and_xdg_paths() {
        let dir = tempdir().unwrap();
        let env = ensure_managed_opencode_env(dir.path()).unwrap();

        let config_path = dir.path().join("managed-opencode").join("opencode.json");
        let xdg_config_home = dir.path().join("xdg-config");

        assert!(config_path.exists());
        assert!(xdg_config_home.join("opencode").exists());
        assert!(
            env.iter()
                .any(|e| e.name == "OPENCODE_CONFIG" && e.value == config_path.to_string_lossy())
        );
        assert!(
            env.iter()
                .any(|e| e.name == "XDG_CONFIG_HOME" && e.value == xdg_config_home.to_string_lossy())
        );
    }
}
