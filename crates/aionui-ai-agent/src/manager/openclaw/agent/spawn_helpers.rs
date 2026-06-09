use aionui_api_types::OpenClawGatewayConfig;
use aionui_common::{CommandSpec, EnvVar};

use super::{DEFAULT_GATEWAY_PORT, GATEWAY_READY_POLL_INTERVAL, GATEWAY_READY_TIMEOUT};
use crate::error::AgentError;
use tracing::{debug, warn};

pub(super) fn build_spawn_config(cli_path: &str, workspace: &str, gateway: &OpenClawGatewayConfig) -> CommandSpec {
    let host = gateway.host.as_deref().unwrap_or("127.0.0.1");
    let port = gateway.port.unwrap_or(DEFAULT_GATEWAY_PORT);

    let mut env = vec![
        EnvVar {
            name: "OPENCLAW_GATEWAY_HOST".into(),
            value: host.to_owned(),
        },
        EnvVar {
            name: "OPENCLAW_GATEWAY_PORT".into(),
            value: port.to_string(),
        },
    ];

    if let Some(ref token) = gateway.token {
        env.push(EnvVar {
            name: "OPENCLAW_GATEWAY_TOKEN".into(),
            value: token.clone(),
        });
    }
    if let Some(ref password) = gateway.password {
        env.push(EnvVar {
            name: "OPENCLAW_GATEWAY_PASSWORD".into(),
            value: password.clone(),
        });
    }

    CommandSpec {
        command: cli_path.into(),
        args: vec!["gateway".into(), "--port".into(), port.to_string()],
        env,
        cwd: Some(workspace.to_owned()),
    }
}

pub(super) async fn is_port_listening(host: &str, port: u16) -> bool {
    tokio::net::TcpStream::connect((host, port)).await.is_ok()
}

pub(super) async fn wait_for_gateway_ready(host: &str, port: u16) -> Result<(), AgentError> {
    let start = tokio::time::Instant::now();
    while start.elapsed() < GATEWAY_READY_TIMEOUT {
        if is_port_listening(host, port).await {
            return Ok(());
        }
        tokio::time::sleep(GATEWAY_READY_POLL_INTERVAL).await;
    }
    Err(AgentError::internal(format!(
        "OpenClaw gateway did not become ready on {host}:{port} within {}s",
        GATEWAY_READY_TIMEOUT.as_secs()
    )))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::shared_kernel::approval_key;

    #[test]
    fn default_gateway_port_is_18789() {
        assert_eq!(DEFAULT_GATEWAY_PORT, 18789);
    }

    fn env_val<'a>(config: &'a CommandSpec, name: &str) -> Option<&'a str> {
        config.env.iter().find(|e| e.name == name).map(|e| e.value.as_str())
    }

    #[test]
    fn build_spawn_config_with_defaults() {
        let gateway = OpenClawGatewayConfig {
            host: None,
            port: None,
            token: None,
            password: None,
            use_external_gateway: false,
            cli_path: Some("/usr/bin/openclaw".into()),
        };
        let config = build_spawn_config("/usr/bin/openclaw", "/proj", &gateway);
        assert_eq!(config.command.to_str().unwrap(), "/usr/bin/openclaw");
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_HOST").unwrap(), "127.0.0.1");
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_PORT").unwrap(), "18789");
        assert!(env_val(&config, "OPENCLAW_GATEWAY_TOKEN").is_none());
    }

    #[test]
    fn build_spawn_config_with_custom_gateway() {
        let gateway = OpenClawGatewayConfig {
            host: Some("remote.host".into()),
            port: Some(9999),
            token: Some("secret".into()),
            password: Some("pass".into()),
            use_external_gateway: true,
            cli_path: Some("/usr/bin/openclaw".into()),
        };
        let config = build_spawn_config("/usr/bin/openclaw", "/proj", &gateway);
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_HOST").unwrap(), "remote.host");
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_PORT").unwrap(), "9999");
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_TOKEN").unwrap(), "secret");
        assert_eq!(env_val(&config, "OPENCLAW_GATEWAY_PASSWORD").unwrap(), "pass");
    }

    #[test]
    fn approval_key_formats_correctly() {
        assert_eq!(approval_key(Some("edit"), Some("file")), "edit:file");
        assert_eq!(approval_key(Some("edit"), None), "edit");
        assert_eq!(approval_key(None, None), "");
    }
}

/// Auto-approve any pending device repair requests before connecting to the gateway.
///
/// When the AionCore backend restarts, it may reconnect with the same device identity
/// but the OpenClaw gateway may have created a pending repair that needs approval.
/// This function runs `openclaw devices approve --latest` to silently approve
/// the most recent pending request, preventing NOT_PAIRED errors on startup.
pub(super) async fn auto_approve_pending_device_repairs(
    cli_path: &str,
    host: &str,
    port: u16,
    token: Option<&str>,
    password: Option<&str>,
) {
    let url = format!("ws://{host}:{port}");

    let mut cmd = tokio::process::Command::new(cli_path);
    cmd.arg("devices")
        .arg("approve")
        .arg("--latest")
        .arg("--json")
        .arg("--timeout")
        .arg("5000")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    let has_auth = token.is_some() || password.is_some();

    // When the gateway has no auth, passing --url triggers openclaw's
    // "url override requires explicit credentials" error. Without --url
    // the command uses the configured default gateway (our local spawn).
    if has_auth {
        cmd.arg("--url").arg(&url);
    }

    if let Some(t) = token {
        cmd.arg("--token").arg(t);
    }
    if let Some(p) = password {
        cmd.arg("--password").arg(p);
    }

    match cmd.output().await {
        Ok(output) if output.status.success() => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            if !stdout.trim().is_empty() {
                debug!(%url, "Auto-approved OpenClaw device repair: {stdout}");
            }
        }
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr);
            // Non-zero exit usually means "nothing to approve" — not an error
            debug!(%url, stderr = %stderr.trim(), "OpenClaw auto-approve returned non-zero (likely nothing pending)");
        }
        Err(e) => {
            warn!(%url, error = %e, "Failed to run openclaw devices approve for auto-repair");
        }
    }
}

/// Approve a pending device pairing request via `openclaw devices approve --latest`.
///
/// When the device identity is new or changed (file lost, corrupt, first install),
/// the gateway creates a pending pairing request and returns NOT_PAIRED. This
/// function runs `openclaw devices approve --latest` (the ONLY supported pairing
/// mechanism — there is no `devices pair` CLI command in openclaw 2026.6.1+).
///
/// Returns `true` if a pending request was approved, `false` if none was pending.
pub(super) async fn auto_pair_new_device(
    cli_path: &str,
    host: &str,
    port: u16,
    device_id: &str,
    token: Option<&str>,
    password: Option<&str>,
) -> Result<bool, AgentError> {
    let url = format!("ws://{host}:{port}");

    // `openclaw devices approve --latest` approves the most recent pending
    // request created by the gateway when an unknown device connects.
    let mut cmd = tokio::process::Command::new(cli_path);
    cmd.arg("devices")
        .arg("approve")
        .arg("--latest")
        .arg("--json")
        .arg("--timeout")
        .arg("5000")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    let has_auth = token.is_some() || password.is_some();

    // When the gateway has no auth, passing --url triggers openclaw's
    // "url override requires explicit credentials" error.  Without --url
    // the command uses the configured default gateway (our local spawn).
    if has_auth {
        cmd.arg("--url").arg(&url);
    }

    if let Some(t) = token {
        cmd.arg("--token").arg(t);
    }
    if let Some(p) = password {
        cmd.arg("--password").arg(p);
    }

    match cmd.output().await {
        Ok(output) if output.status.success() => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            if !stdout.trim().is_empty() {
                debug!(%url, %device_id, "Approved pending OpenClaw device: {stdout}");
            }
            Ok(true)
        }
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr);
            // If failing because --url was missing and gateway URL isn't configured,
            // report it clearly; otherwise "nothing to approve" is fine.
            if stderr.contains("requires explicit credentials") {
                warn!(%url, %device_id, stderr = %stderr.trim(),
                       "openclaw devices approve requires gateway credentials in ~/.openclaw/openclaw.json");
            } else {
                debug!(%url, %device_id, stderr = %stderr.trim(),
                       "openclaw devices approve --latest returned non-zero (likely nothing pending)");
            }
            Ok(false)
        }
        Err(e) => {
            warn!(%url, %device_id, error = %e,
                   "Failed to run openclaw devices approve --latest");
            Ok(false)
        }
    }
}
