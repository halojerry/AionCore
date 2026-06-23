use std::collections::HashMap;
use std::fs;
use std::path::Path;

use rusqlite::Connection;
use tracing::{info, warn};

use super::CcSwitchPaths;

#[derive(Debug, serde::Deserialize)]
pub(crate) struct CcSwitchSettings {
    #[serde(rename = "currentProviderClaude")]
    pub(crate) current_provider_claude: Option<String>,
    #[serde(rename = "currentProviderCodex")]
    pub(crate) current_provider_codex: Option<String>,
    #[serde(rename = "currentProviderHermes")]
    pub(crate) current_provider_hermes: Option<String>,
    #[serde(rename = "currentProviderOpencode")]
    pub(crate) current_provider_opencode: Option<String>,
    #[serde(rename = "currentProviderOpenclaw")]
    pub(crate) current_provider_openclaw: Option<String>,
}

#[derive(Debug, serde::Deserialize)]
struct ProviderSettingsConfig {
    #[serde(default)]
    env: Option<serde_json::Map<String, serde_json::Value>>,
}

pub(crate) fn normalize_env(raw: &serde_json::Map<String, serde_json::Value>) -> HashMap<String, String> {
    raw.iter()
        .filter_map(|(k, v)| {
            if let serde_json::Value::String(s) = v
                && !s.trim().is_empty()
            {
                Some((k.clone(), s.clone()))
            } else {
                None
            }
        })
        .collect()
}

pub fn read_claude_provider_env_with_paths(paths: &CcSwitchPaths) -> HashMap<String, String> {
    let settings_content = match fs::read_to_string(&paths.settings_path) {
        Ok(c) => c,
        Err(_) => return HashMap::new(),
    };

    let settings: CcSwitchSettings = match serde_json::from_str(&settings_content) {
        Ok(s) => s,
        Err(e) => {
            warn!(error = %e, "cc-switch: failed to parse settings.json");
            return HashMap::new();
        }
    };

    let provider_id = match settings.current_provider_claude {
        Some(ref id) if !id.trim().is_empty() => id.clone(),
        _ => return HashMap::new(),
    };

    if !paths.database_path.exists() {
        warn!(
            provider_id,
            "cc-switch: settings.json references provider but database file not found"
        );
        return HashMap::new();
    }

    read_env_from_db(&paths.database_path, &provider_id)
}

fn read_env_from_db(db_path: &Path, provider_id: &str) -> HashMap<String, String> {
    let conn = match Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY) {
        Ok(c) => c,
        Err(e) => {
            warn!(error = %e, "cc-switch: failed to open database");
            return HashMap::new();
        }
    };

    let settings_config_json: Option<String> = conn
        .query_row(
            "SELECT settings_config FROM providers WHERE id = ?1 AND app_type = 'claude' LIMIT 1",
            [provider_id],
            |row| row.get(0),
        )
        .ok()
        .flatten();

    let Some(json_str) = settings_config_json else {
        warn!(provider_id, "cc-switch: provider not found in database");
        return HashMap::new();
    };

    let config: ProviderSettingsConfig = match serde_json::from_str(&json_str) {
        Ok(c) => c,
        Err(e) => {
            warn!(error = %e, provider_id, "cc-switch: failed to parse provider settings_config");
            return HashMap::new();
        }
    };

    let env = match config.env {
        Some(ref env_map) => normalize_env(env_map),
        None => HashMap::new(),
    };

    if env.is_empty() {
        info!(
            provider_id,
            "cc-switch: provider has no env vars configured (using native API)"
        );
    } else {
        let keys: Vec<&str> = env.keys().map(|k| k.as_str()).collect();
        info!(provider_id, ?keys, "cc-switch: provider env vars loaded");
    }

    env
}

pub fn read_claude_provider_env() -> HashMap<String, String> {
    let Some(paths) = CcSwitchPaths::system() else {
        return HashMap::new();
    };
    read_claude_provider_env_with_paths(&paths)
}

// ---------------------------------------------------------------------------
// Generic per-app-type provider reading
// ---------------------------------------------------------------------------

fn read_provider_config_json(app_type: &str) -> Option<serde_json::Value> {
    let paths = CcSwitchPaths::system()?;
    let settings_content = fs::read_to_string(&paths.settings_path).ok()?;
    let settings: CcSwitchSettings = serde_json::from_str(&settings_content).ok()?;

    let provider_id = match app_type {
        "claude" => settings.current_provider_claude,
        "codex" => settings.current_provider_codex,
        "hermes" => settings.current_provider_hermes,
        "opencode" => settings.current_provider_opencode,
        "openclaw" => settings.current_provider_openclaw,
        _ => return None,
    }
    .filter(|s| !s.trim().is_empty())?;

    if !paths.database_path.exists() {
        return None;
    }

    let conn = Connection::open_with_flags(&paths.database_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
        .ok()?;

    let settings_config_json: String = conn
        .query_row(
            "SELECT settings_config FROM providers WHERE id = ?1 AND app_type = ?2 LIMIT 1",
            rusqlite::params![provider_id, app_type],
            |row| row.get(0),
        )
        .ok()?;

    serde_json::from_str(&settings_config_json).ok()
}

pub fn read_provider_env_by_app_type(app_type: &str) -> HashMap<String, String> {
    let Some(config) = read_provider_config_json(app_type) else {
        return HashMap::new();
    };
    let Some(env_obj) = config.get("env").and_then(|v| v.as_object()) else {
        return HashMap::new();
    };
    normalize_env(env_obj)
}

/// Read the Codex proxy port from `~/.pounding/codex-proxy-port`.
/// Returns `None` if the file doesn't exist or contains an invalid port.
fn read_codex_proxy_port() -> Option<u16> {
    let path = dirs::home_dir()?
        .join(".pounding")
        .join("codex-proxy-port");
    let content = std::fs::read_to_string(path).ok()?;
    let trimmed = content.trim();
    let port: u16 = trimmed.parse().ok()?;
    Some(port)
}

/// Ensure the Codex live config files are up to date before spawning.
/// Reads the cc-switch DB provider row for app_type='codex' and writes
/// ~/.codex/auth.json and ~/.codex/config.toml if the DB has newer state.
///
/// Overrides `base_url` with the local codex-api-proxy address when the
/// proxy port file exists, so Codex's Responses API traffic is translated
/// to Chat Completions for the POUNDING upstream API.
pub fn ensure_codex_live_config() {
    let Some(config) = read_provider_config_json("codex") else {
        return;
    };
    let Some(home) = dirs::home_dir() else {
        return;
    };

    let codex_dir = home.join(".codex");
    let auth_path = codex_dir.join("auth.json");
    let config_path = codex_dir.join("config.toml");

    // Write auth.json
    if let Some(auth) = config.get("auth") {
        if let Err(e) = std::fs::create_dir_all(&codex_dir)
            .and_then(|_| std::fs::write(&auth_path, serde_json::to_string_pretty(auth).unwrap_or_default()))
        {
            tracing::warn!(error = %e, "cc-switch: failed to write codex auth.json");
        }
    }

    // ── Config.toml: defense-in-depth write ──────────────────────────
    //
    // The TypeScript side (writeCodexConfigForProviderSync) writes the
    // authoritative config.toml with model_catalog_json and a full
    // pounding-models.json.  We only write from Rust as a fallback when
    // the file is missing or incomplete (no model_catalog_json), which
    // covers first-login and config-deletion edge cases without
    // overwriting the richer TypeScript version.
    //
    // The cc-switch DB stores Codex provider settings_config in two formats:
    // 1. (POUNDING): top-level JSON keys — model, model_provider, base_url, wire_api
    // 2. (legacy cc-switch): a "config" key containing a TOML string with the same fields
    let mut needs_write = !config_path.exists();
    if !needs_write {
        // File exists — check whether it has model_catalog_json.
        // TypeScript always includes it; if absent, the file is stale.
        if let Ok(existing) = std::fs::read_to_string(&config_path) {
            needs_write = !existing.contains("model_catalog_json");
        } else {
            needs_write = true;  // unreadable → treat as missing
        }
    }
    if !needs_write {
        tracing::debug!("cc-switch: codex config.toml exists and is complete; skip");
    } else {
        tracing::info!("cc-switch: writing codex config.toml (fallback)");

        let mut model = config.get("model").and_then(|v| v.as_str()).unwrap_or("").to_owned();
        let mut model_provider = config
            .get("model_provider")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_owned();
        let mut base_url = config.get("base_url").and_then(|v| v.as_str()).unwrap_or("").to_owned();
        let mut wire_api = config.get("wire_api").and_then(|v| v.as_str()).unwrap_or("responses").to_owned();

        // Fallback: if the top-level keys are empty, try parsing the legacy "config" TOML field
        if model.is_empty() && model_provider.is_empty() && base_url.is_empty() {
            if let Some(toml_str) = config.get("config").and_then(|v| v.as_str()) {
                for line in toml_str.lines() {
                    let trimmed = line.trim();
                    if let Some(val) = trimmed.strip_prefix("model_provider = ") {
                        model_provider = val.trim_matches('"').to_owned();
                    } else if let Some(val) = trimmed.strip_prefix("model = ") {
                        model = val.trim_matches('"').to_owned();
                    } else if let Some(val) = trimmed.strip_prefix("base_url = ") {
                        base_url = val.trim_matches('"').to_owned();
                    } else if let Some(val) = trimmed.strip_prefix("wire_api = ") {
                        wire_api = val.trim_matches('"').to_owned();
                    }
                }
            }
        }

        // Override base_url with the local codex-api-proxy port when available
        if let Some(port) = read_codex_proxy_port() {
            base_url = format!("http://127.0.0.1:{port}/v1");
            tracing::info!(port, "cc-switch: codex base_url overridden to local proxy");
        }

        let toml_content = format!(
            "model_provider = \"{model_provider}\"\n\
             model = \"{model}\"\n\
             model_catalog_json = \"pounding-models.json\"\n\
             \n\
             [model_providers]\n\
             [model_providers.\"{model_provider}\"]\n\
             name = \"POUNDING API\"\n\
             base_url = \"{base_url}\"\n\
             wire_api = \"{wire_api}\"\n\
             requires_openai_auth = true\n"
        );

        if let Err(e) = std::fs::create_dir_all(&codex_dir).and_then(|_| std::fs::write(&config_path, &toml_content)) {
            tracing::warn!(error = %e, "cc-switch: failed to write codex config.toml");
        }
    }
}

/// Ensure the OpenCode live config file is up to date before spawning.
pub fn ensure_opencode_live_config() {
    let Some(config) = read_provider_config_json("opencode") else {
        return;
    };
    let Some(home) = dirs::home_dir() else {
        return;
    };

    let model = config.get("model").and_then(|v| v.as_str()).unwrap_or("");
    let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");
    let base_url = config.get("base_url").and_then(|v| v.as_str()).unwrap_or("");
    let npm = config
        .get("npm")
        .and_then(|v| v.as_str())
        .unwrap_or("@ai-sdk/openai-compatible");
    let provider_id = model.split('/').next().unwrap_or("pounding-managed");

    let opencode_config = serde_json::json!({
        "$schema": "https://opencode.ai/config.json",
        "model": model,
        "provider": {
            provider_id: {
                "npm": npm,
                "options": {
                    "baseURL": base_url,
                    "apiKey": api_key,
                },
                "models": {
                    model.split('/').nth(1).unwrap_or(""): { "name": model.split('/').nth(1).unwrap_or("") }
                }
            }
        }
    });

    let config_path = home.join(".opencode").join("config.json");
    if let Err(e) = std::fs::create_dir_all(config_path.parent().unwrap())
        .and_then(|_| std::fs::write(&config_path, serde_json::to_string_pretty(&opencode_config).unwrap_or_default()))
    {
        tracing::warn!(error = %e, "cc-switch: failed to write opencode config.json");
    }
}

/// Ensure the OpenClaw live config file is up to date before spawning.
pub fn ensure_openclaw_live_config() {
    let Some(config) = read_provider_config_json("openclaw") else {
        return;
    };
    let Some(home) = dirs::home_dir() else {
        return;
    };

    let config_path = home.join(".openclaw").join("openclaw.json");

    // ── Defense-in-depth skip: if the TypeScript path already wrote a complete
    //     config, don't overwrite it. The TypeScript version includes fields
    //     (gateway.remote.token, gateway.auth.mode, models.mode) that this
    //     Rust fallback doesn't generate. Overwriting loses them.
    if config_path.exists() {
        if let Ok(existing) = std::fs::read_to_string(&config_path) {
            let has_gateway_token = existing.contains("\"gateway\"") && existing.contains("\"token\"");
            let has_auth_mode = existing.contains("\"auth\"") && existing.contains("\"mode\"");
            if has_gateway_token && has_auth_mode {
                tracing::debug!("cc-switch: openclaw.json exists and is complete; skip");
                return;
            }
        }
    }
    tracing::info!("cc-switch: writing openclaw.json (fallback)");

    let model = config.get("model").and_then(|v| v.as_str()).unwrap_or("");
    let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");
    let base_url = config.get("base_url").and_then(|v| v.as_str()).unwrap_or("");
    let api = config.get("api").and_then(|v| v.as_str()).unwrap_or("openai-completions");
    let provider_id = model.split('/').next().unwrap_or("pounding-managed");

    let openclaw_config = serde_json::json!({
        "agents": {
            "defaults": {
                "model": {
                    "primary": model
                },
                "models": {
                    model: { "alias": model.split('/').nth(1).unwrap_or("") }
                }
            }
        },
        "models": {
            "providers": {
                provider_id: {
                    "baseUrl": base_url,
                    "api": api,
                    "auth": "api-key",
                    "authHeader": true,
                    "models": [{ "id": model.split('/').nth(1).unwrap_or(""), "name": model.split('/').nth(1).unwrap_or("") }]
                }
            }
        }
    });

    // Preserve auth token if already set
    let mut merged = openclaw_config;
    if let Ok(existing) = std::fs::read_to_string(&config_path) {
        if let Ok(existing_val) = serde_json::from_str::<serde_json::Value>(&existing) {
            if let Some(existing_token) = existing_val
                .get("gateway")
                .and_then(|g| g.get("auth"))
                .and_then(|a| a.get("token"))
            {
                if let serde_json::Value::Object(ref mut map) = merged {
                    map.entry("gateway".to_string())
                        .or_insert_with(|| {
                            serde_json::json!({"auth": {"token": existing_token.clone()}, "mode": "local"})
                        });
                }
            }
        }
    }
    // Always set gateway mode to local
    if let serde_json::Value::Object(ref mut map) = merged {
        map.entry("gateway".to_string())
            .or_insert_with(|| serde_json::json!({"mode": "local"}));
    }

    if let Err(e) = std::fs::create_dir_all(config_path.parent().unwrap())
        .and_then(|_| std::fs::write(&config_path, serde_json::to_string_pretty(&merged).unwrap_or_default()))
    {
        tracing::warn!(error = %e, "cc-switch: failed to write openclaw.json");
    }
    // Also write the API key
    if !api_key.is_empty() {
        let auth_path = home.join(".openclaw").join("auth.json");
        let auth = serde_json::json!({ "OPENAI_API_KEY": api_key });
        let _ = std::fs::create_dir_all(auth_path.parent().unwrap())
            .and_then(|_| std::fs::write(&auth_path, serde_json::to_string_pretty(&auth).unwrap_or_default()));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_settings_extracts_provider_id() {
        let json = r#"{"currentProviderClaude": "my-provider-id"}"#;
        let settings: CcSwitchSettings = serde_json::from_str(json).unwrap();
        assert_eq!(settings.current_provider_claude.as_deref(), Some("my-provider-id"));
    }

    #[test]
    fn parse_settings_missing_field_returns_none() {
        let json = r#"{}"#;
        let settings: CcSwitchSettings = serde_json::from_str(json).unwrap();
        assert!(settings.current_provider_claude.is_none());
    }

    #[test]
    fn normalize_env_filters_non_string_values() {
        let mut raw = serde_json::Map::new();
        raw.insert("ANTHROPIC_API_KEY".into(), serde_json::Value::String("sk-123".into()));
        raw.insert("EMPTY".into(), serde_json::Value::String("".into()));
        raw.insert("NUMBER".into(), serde_json::Value::Number(42.into()));
        raw.insert(
            "VALID_URL".into(),
            serde_json::Value::String("https://api.example.com".into()),
        );

        let result = normalize_env(&raw);
        assert_eq!(result.len(), 2);
        assert_eq!(result.get("ANTHROPIC_API_KEY").unwrap(), "sk-123");
        assert_eq!(result.get("VALID_URL").unwrap(), "https://api.example.com");
    }

    #[test]
    fn read_provider_env_returns_empty_when_no_paths() {
        let paths = CcSwitchPaths::from_home(std::path::Path::new("/nonexistent"));
        let env = read_claude_provider_env_with_paths(&paths);
        assert!(env.is_empty());
    }
}
