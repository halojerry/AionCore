use std::collections::HashMap;
use std::fs;
use std::path::Path;

use rusqlite::Connection;
use tracing::{debug, info, warn};

use super::CcSwitchPaths;

#[derive(Debug, serde::Deserialize)]
pub(crate) struct CcSwitchSettings {
    #[serde(rename = "currentProviderClaude")]
    pub(crate) current_provider_claude: Option<String>,
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

/// Model env keys that must NOT be injected into agent subprocesses.
///
/// These keys are stored in cc-switch.db for `model_info.rs` to build
/// the UI model picker, but injecting them into the agent's environment
/// would override the model selected via the ACP session protocol.
const MODEL_ENV_KEY_BLOCKLIST: &[&str] = &[
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_MODEL",
    // Legacy keys from the upstream _NAME suffix bug — still present in older
    // cc-switch.db rows and must not leak into agent subprocess env.
    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME",
];

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

    let mut env = read_env_from_db(&paths.database_path, &provider_id);

    // Strip model env keys before injecting into agent subprocess.
    // Model selection is handled by the ACP session protocol; these
    // env overrides would cause model mismatch.
    for key in MODEL_ENV_KEY_BLOCKLIST {
        env.remove(*key);
    }

    env
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

/// Read the full provider env from cc-switch.db **without** stripping
/// model env keys. Used to sync slot→model mappings to
/// `~/.claude/settings.json` so Claude Code can resolve slots to the
/// correct upstream model on process start.
pub(crate) fn read_claude_provider_full_env_with_paths(
    paths: &CcSwitchPaths,
) -> HashMap<String, String> {
    let settings_content = match fs::read_to_string(&paths.settings_path) {
        Ok(c) => c,
        Err(_) => return HashMap::new(),
    };

    let settings: CcSwitchSettings = match serde_json::from_str(&settings_content) {
        Ok(s) => s,
        Err(e) => {
            warn!(error = %e, "cc-switch: failed to parse settings.json (full env)");
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
            "cc-switch: database file not found (full env)"
        );
        return HashMap::new();
    }

    read_env_from_db(&paths.database_path, &provider_id)
}

/// Model env var keys to sync from cc-switch.db into
/// `~/.claude/settings.json`. These keys tell Claude Code which upstream
/// model each slot (`default` / `opus` / `haiku`) resolves to.
const MODEL_ENV_SYNC_KEYS: &[&str] = &[
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_MODEL",
];

/// Write cc-switch model env vars into `~/.claude/settings.json`,
/// merging with any existing `env` keys so non-model settings
/// (API key, base URL, etc.) are preserved.
pub(crate) fn sync_claude_settings_model_env_with_paths(paths: &CcSwitchPaths) {
    let full_env = read_claude_provider_full_env_with_paths(paths);
    if full_env.is_empty() {
        debug!("cc-switch: no provider env available; skipping settings.json sync");
        return;
    }

    // Read existing settings.json (may not exist yet).
    let mut settings: serde_json::Value = fs::read_to_string(&paths.claude_settings_path)
        .ok()
        .and_then(|content| serde_json::from_str(&content).ok())
        .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));

    let env_obj = settings
        .as_object_mut()
        .and_then(|root| root.entry("env".to_owned()).or_insert_with(|| {
            serde_json::Value::Object(serde_json::Map::new())
        })
        .as_object_mut());

    let Some(env_obj) = env_obj else {
        warn!("cc-switch: settings.json 'env' key is not an object; cannot sync model env vars");
        return;
    };

    for key in MODEL_ENV_SYNC_KEYS {
        if let Some(value) = full_env.get(*key) {
            env_obj.insert(
                key.to_string(),
                serde_json::Value::String(value.clone()),
            );
        }
    }

    let serialized = match serde_json::to_string_pretty(&settings) {
        Ok(s) => s,
        Err(e) => {
            warn!(error = %e, "cc-switch: failed to serialize settings.json for model env sync");
            return;
        }
    };

    if let Err(e) = fs::write(&paths.claude_settings_path, serialized) {
        warn!(error = %e, path = %paths.claude_settings_path.display(), "cc-switch: failed to write settings.json for model env sync");
        return;
    }

    info!(
        path = %paths.claude_settings_path.display(),
        keys = ?MODEL_ENV_SYNC_KEYS.iter().filter(|k| full_env.contains_key(**k)).collect::<Vec<_>>(),
        "cc-switch: synced model env vars to claude settings.json"
    );
}

/// Convenience wrapper that resolves system paths and syncs model env
/// vars from cc-switch.db into `~/.claude/settings.json`.
pub fn sync_claude_settings_model_env() {
    let Some(paths) = CcSwitchPaths::system() else {
        return;
    };
    sync_claude_settings_model_env_with_paths(&paths);
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
