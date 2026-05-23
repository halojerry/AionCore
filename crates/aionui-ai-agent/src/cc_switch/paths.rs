use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct CcSwitchPaths {
    pub settings_path: PathBuf,
    pub database_path: PathBuf,
    pub claude_settings_path: PathBuf,
}

#[derive(Debug, serde::Deserialize)]
struct CcSwitchSettingsFile {
    #[serde(rename = "claudeConfigDir")]
    claude_config_dir: Option<String>,
}

fn resolve_claude_config_dir(home: &Path, settings_path: &Path) -> PathBuf {
    let override_dir = fs::read_to_string(settings_path)
        .ok()
        .and_then(|content| serde_json::from_str::<CcSwitchSettingsFile>(&content).ok())
        .and_then(|settings| settings.claude_config_dir)
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty());

    match override_dir {
        Some(dir) => {
            let path = PathBuf::from(dir);
            if path.is_absolute() {
                path
            } else {
                home.join(path)
            }
        }
        None => home.join(".claude"),
    }
}

impl CcSwitchPaths {
    pub fn from_home(home: &Path) -> Self {
        let base = home.join(".cc-switch");
        let settings_path = base.join("settings.json");
        let database_path = base.join("cc-switch.db");
        let claude_config_dir = resolve_claude_config_dir(home, &settings_path);
        Self {
            settings_path,
            database_path,
            claude_settings_path: claude_config_dir.join("settings.json"),
        }
    }

    pub fn system() -> Option<Self> {
        dirs::home_dir().map(|h| Self::from_home(&h))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn resolves_paths_from_home() {
        let paths = CcSwitchPaths::from_home(Path::new("/home/testuser"));
        assert_eq!(
            paths.settings_path,
            Path::new("/home/testuser/.cc-switch/settings.json")
        );
        assert_eq!(paths.database_path, Path::new("/home/testuser/.cc-switch/cc-switch.db"));
        assert_eq!(
            paths.claude_settings_path,
            Path::new("/home/testuser/.claude/settings.json")
        );
    }

    #[test]
    fn system_returns_some_when_home_exists() {
        let paths = CcSwitchPaths::system();
        assert!(paths.is_some());
    }
}
