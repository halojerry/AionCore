use std::collections::HashMap;
use std::fs;
use std::path::Path;

use aionui_api_types::{ModelInfoEntry, ModelInfoPayload};
use rusqlite::Connection;
use tracing::warn;

use super::CcSwitchPaths;

fn sanitize_model_value(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }

    let without_ansi = regex::Regex::new(r"\x1b\[[0-9;]*[A-Za-z]")
        .ok()?
        .replace_all(trimmed, "")
        .to_string();
    let without_prefix = regex::Regex::new(r"(?i)^set model to\s+")
        .ok()?
        .replace(&without_ansi, "")
        .to_string();
    let without_suffix = regex::Regex::new(r"\[(?:\d{1,3}(?:;\d{1,3})*)m\]?$")
        .ok()?
        .replace(&without_prefix, "")
        .to_string();

    let normalized = without_suffix.trim();
    (!normalized.is_empty()).then(|| normalized.to_owned())
}

pub(crate) fn normalize_claude_model_slot(value: &str) -> Option<&'static str> {
    match sanitize_model_value(value)?.to_lowercase().as_str() {
        "sonnet" | "default" => Some("default"),
        "opus" => Some("opus"),
        "haiku" => Some("haiku"),
        _ => None,
    }
}

fn read_claude_selected_slot(claude_settings_path: &Path) -> Option<&'static str> {
    let content = fs::read_to_string(claude_settings_path).ok()?;
    let parsed: serde_json::Value = serde_json::from_str(&content).ok()?;
    let model_str = parsed.get("model")?.as_str()?;
    normalize_claude_model_slot(model_str)
}

pub fn build_model_info_from_env(
    env: &HashMap<String, String>,
    labels: &HashMap<String, String>,
    active_slot: Option<&str>,
) -> Option<ModelInfoPayload> {
    let default_model = env
        .get("ANTHROPIC_DEFAULT_SONNET_MODEL")
        .and_then(|s| sanitize_model_value(s))
        .or_else(|| env.get("ANTHROPIC_MODEL").and_then(|s| sanitize_model_value(s)));
    let opus_model = env
        .get("ANTHROPIC_DEFAULT_OPUS_MODEL")
        .and_then(|s| sanitize_model_value(s));
    let haiku_model = env
        .get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
        .and_then(|s| sanitize_model_value(s));

    let mut available = Vec::new();
    let mut seen = std::collections::HashSet::new();

    let candidates = [("default", default_model), ("opus", opus_model), ("haiku", haiku_model)];

    for (slot, model_id_opt) in &candidates {
        if let Some(model_id) = model_id_opt
            && seen.insert(model_id.as_str())
        {
            let label = labels
                .get(model_id.as_str())
                .cloned()
                .unwrap_or_else(|| model_id.clone());
            available.push(ModelInfoEntry {
                id: slot.to_string(),
                label,
            });
        }
    }

    if available.is_empty() {
        return None;
    }

    let preferred_slot = active_slot.and_then(normalize_claude_model_slot).unwrap_or("default");
    let current_model_id = available
        .iter()
        .find(|m| m.id == preferred_slot)
        .map(|m| m.id.clone())
        .unwrap_or_else(|| available[0].id.clone());
    let current_model_label = available
        .iter()
        .find(|m| m.id == current_model_id)
        .map(|m| m.label.clone());

    Some(ModelInfoPayload {
        current_model_id: Some(current_model_id),
        current_model_label,
        available_models: available,
    })
}

fn read_model_labels(conn: &Connection) -> HashMap<String, String> {
    let mut stmt = match conn.prepare("SELECT model_id, display_name FROM model_pricing") {
        Ok(s) => s,
        Err(_) => return HashMap::new(),
    };
    let rows = stmt
        .query_map([], |row| {
            let model_id: String = row.get(0)?;
            let display_name: Option<String> = row.get(1)?;
            Ok((model_id, display_name))
        })
        .ok();

    let Some(rows) = rows else {
        return HashMap::new();
    };

    rows.filter_map(|r| r.ok())
        .filter(|(id, _)| !id.trim().is_empty())
        .map(|(id, name)| {
            let label = name.filter(|n| !n.trim().is_empty()).unwrap_or_else(|| id.clone());
            (id, label)
        })
        .collect()
}

pub fn read_claude_model_info_with_paths(paths: &CcSwitchPaths) -> Option<ModelInfoPayload> {
    let settings_content = fs::read_to_string(&paths.settings_path).ok()?;
    let settings: serde_json::Value = serde_json::from_str(&settings_content).ok()?;
    let provider_id = settings
        .get("currentProviderClaude")?
        .as_str()
        .filter(|s| !s.trim().is_empty())?;

    if !paths.database_path.exists() {
        return None;
    }

    let conn = Connection::open_with_flags(&paths.database_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
        .map_err(|e| warn!(error = %e, "cc-switch: failed to open database for model info"))
        .ok()?;

    let settings_config_json: String = conn
        .query_row(
            "SELECT settings_config FROM providers WHERE id = ?1 AND app_type = 'claude' LIMIT 1",
            [provider_id],
            |row| row.get(0),
        )
        .ok()?;

    let config: serde_json::Value = serde_json::from_str(&settings_config_json).ok()?;
    let env_obj = config.get("env")?.as_object()?;

    let env: HashMap<String, String> = env_obj
        .iter()
        .filter_map(|(k, v)| {
            v.as_str()
                .filter(|s| !s.trim().is_empty())
                .map(|s| (k.clone(), s.to_owned()))
        })
        .collect();

    let labels = read_model_labels(&conn);
    let active_slot = read_claude_selected_slot(&paths.claude_settings_path)
        .or_else(|| config.get("model")?.as_str().and_then(normalize_claude_model_slot));

    build_model_info_from_env(&env, &labels, active_slot)
}

pub fn read_claude_model_info() -> Option<ModelInfoPayload> {
    let paths = CcSwitchPaths::system()?;
    read_claude_model_info_with_paths(&paths)
}

/// Read Codex model info from `~/.codex/config.toml` and
/// `~/.codex/pounding-models.json`.
///
/// Codex uses a TOML config (not SQLite like Claude). The config.toml format:
///
/// ```toml
/// [model_providers]
/// [model_providers."pounding-new-api-desktop-newapi-managed-provider"]
/// model = "deepseek-v4-pro"
/// name = "POUNDING API"
/// base_url = "https://api.mxou.cn/v1"
/// ```
///
/// This function finds the first managed provider (id starting with "pounding-")
/// and extracts its model field as the **current** model.
///
/// The full list of available models is read from `~/.codex/pounding-models.json`
/// (written by the desktop TypeScript process during provider sync). When that
/// file is present, `available_models` will contain every selectable model
/// rather than only the currently active one.
pub fn read_codex_model_info() -> Option<ModelInfoPayload> {
    let home = dirs::home_dir()?;
    let codex_dir = std::env::var("CODEX_HOME")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|_| home.join(".codex"));
    let config_path = codex_dir.join("config.toml");
    let models_path = codex_dir.join("pounding-models.json");

    let content = std::fs::read_to_string(&config_path).ok()?;

    // Quick check: does this config reference a managed provider?
    if !content
        .lines()
        .any(|line| line.trim().starts_with("[model_providers.\"pounding-"))
    {
        return None;
    }

    // Parse the TOML manually — format is simple enough:
    // [model_providers."<id>"]
    // model = "<value>"
    let current_model = content
        .lines()
        .skip_while(|line| !line.trim().starts_with("[model_providers.\"pounding-"))
        .skip(1) // skip the section header
        .take_while(|line| !line.trim().starts_with('['))
        .find_map(|line| {
            let trimmed = line.trim();
            trimmed
                .strip_prefix("model")
                .and_then(|rest| rest.trim().strip_prefix('='))
                .map(|val| val.trim().trim_matches('"').to_owned())
                .filter(|v| !v.is_empty())
        })?;

    let current_model_id = sanitize_model_value(&current_model)?;

    // Read the full model list from pounding-models.json (written by desktop TS).
    // When present, every model in the provider is selectable — not just the one
    // currently active in config.toml.
    let available_models: Vec<ModelInfoEntry> = if models_path.exists() {
        std::fs::read_to_string(&models_path)
            .ok()
            .and_then(|json| serde_json::from_str::<serde_json::Value>(&json).ok())
            .and_then(|v| v.get("models")?.as_array().cloned())
            .map(|arr| {
                arr.iter()
                    .filter_map(|m| m.as_str())
                    .filter_map(|id| sanitize_model_value(id))
                    .map(|id| ModelInfoEntry {
                        label: id.clone(),
                        id,
                    })
                    .collect()
            })
            .unwrap_or_default()
    } else {
        vec![]
    };

    if available_models.is_empty() {
        // No models file — return just the current model (backward compat)
        return Some(ModelInfoPayload {
            current_model_id: Some(current_model_id.clone()),
            current_model_label: Some(current_model.clone()),
            available_models: vec![ModelInfoEntry {
                id: current_model_id,
                label: current_model,
            }],
        });
    }

    // Ensure current_model_id is in available_models; fall back to first if not
    let current_id = if available_models.iter().any(|m| m.id == current_model_id) {
        current_model_id
    } else {
        available_models.first()?.id.clone()
    };
    let current_label = available_models
        .iter()
        .find(|m| m.id == current_id)
        .map(|m| m.label.clone());

    Some(ModelInfoPayload {
        current_model_id: Some(current_id),
        current_model_label: current_label,
        available_models,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_model_info_from_env_with_all_slots() {
        let mut env = HashMap::new();
        env.insert("ANTHROPIC_DEFAULT_SONNET_MODEL".into(), "deepseek-v4-pro".into());
        env.insert("ANTHROPIC_DEFAULT_OPUS_MODEL".into(), "deepseek-v4-max".into());
        env.insert("ANTHROPIC_DEFAULT_HAIKU_MODEL".into(), "deepseek-v4-lite".into());

        let labels = HashMap::from([
            ("deepseek-v4-pro".to_owned(), "DeepSeek V4 Pro".to_owned()),
            ("deepseek-v4-max".to_owned(), "DeepSeek V4 Max".to_owned()),
            ("deepseek-v4-lite".to_owned(), "DeepSeek V4 Lite".to_owned()),
        ]);

        let info = build_model_info_from_env(&env, &labels, None);
        assert!(info.is_some());

        let payload = info.unwrap();
        assert_eq!(payload.available_models.len(), 3);
        assert_eq!(payload.current_model_id.as_deref(), Some("default"));
        assert_eq!(payload.current_model_label.as_deref(), Some("DeepSeek V4 Pro"));
    }

    #[test]
    fn builds_model_info_single_model() {
        let mut env = HashMap::new();
        env.insert("ANTHROPIC_MODEL".into(), "glm-5.1x".into());

        let info = build_model_info_from_env(&env, &HashMap::new(), None);
        assert!(info.is_some());

        let payload = info.unwrap();
        assert_eq!(payload.available_models.len(), 1);
        assert_eq!(payload.available_models[0].id, "default");
        assert_eq!(payload.available_models[0].label, "glm-5.1x");
    }

    #[test]
    fn returns_none_when_no_model_env_vars() {
        let env = HashMap::new();
        let info = build_model_info_from_env(&env, &HashMap::new(), None);
        assert!(info.is_none());
    }

    #[test]
    fn respects_active_slot_override() {
        let mut env = HashMap::new();
        env.insert("ANTHROPIC_DEFAULT_SONNET_MODEL".into(), "model-a".into());
        env.insert("ANTHROPIC_DEFAULT_OPUS_MODEL".into(), "model-b".into());

        let info = build_model_info_from_env(&env, &HashMap::new(), Some("opus"));
        assert!(info.is_some());
        assert_eq!(info.unwrap().current_model_id.as_deref(), Some("opus"));
    }

    #[test]
    fn normalize_slot_maps_sonnet_to_default() {
        assert_eq!(normalize_claude_model_slot("sonnet"), Some("default"));
        assert_eq!(normalize_claude_model_slot("default"), Some("default"));
        assert_eq!(normalize_claude_model_slot("opus"), Some("opus"));
        assert_eq!(normalize_claude_model_slot("haiku"), Some("haiku"));
        assert_eq!(normalize_claude_model_slot("unknown"), None);
        assert_eq!(normalize_claude_model_slot(""), None);
    }

    #[test]
    fn sanitizes_ansi_polluted_model_values() {
        let mut env = HashMap::new();
        env.insert(
            "ANTHROPIC_DEFAULT_SONNET_MODEL".into(),
            "\u{1b}[1mclaude-sonnet-4-20250514\u{1b}[0m".into(),
        );
        env.insert(
            "ANTHROPIC_DEFAULT_OPUS_MODEL".into(),
            "Set model to claude-opus-4-7[1m]".into(),
        );

        let info = build_model_info_from_env(&env, &HashMap::new(), Some("Set model to opus[1m]"));
        let payload = info.expect("sanitized model info should exist");

        assert_eq!(payload.current_model_id.as_deref(), Some("opus"));
        assert_eq!(payload.available_models[0].label, "claude-sonnet-4-20250514");
        assert_eq!(payload.available_models[1].label, "claude-opus-4-7");
    }
}
