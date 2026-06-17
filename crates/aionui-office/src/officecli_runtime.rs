use std::ffi::{OsStr, OsString};
#[cfg(test)]
use std::path::Path;
use std::path::PathBuf;

use aionui_runtime::resolve_command_path;

// POUNDING: install order is COS (China CDN) → d.officecli.ai (official mirror) → GitHub (upstream).
// The install scripts themselves download binaries; COS distributes both the scripts and
// the pre-built OfficeCLI binaries for out-of-box experience in mainland China.
pub(crate) const OFFICECLI_INSTALL_SH_MIRROR_URL: &str =
    "https://yss-1256275613.cos.ap-guangzhou.myqcloud.com/pounding/officecli/install.sh";
pub(crate) const OFFICECLI_INSTALL_PS1_MIRROR_URL: &str =
    "https://yss-1256275613.cos.ap-guangzhou.myqcloud.com/pounding/officecli/install.ps1";
pub(crate) const OFFICECLI_INSTALL_SH_FALLBACK_URL: &str = "https://d.officecli.ai/install.sh";
pub(crate) const OFFICECLI_INSTALL_PS1_FALLBACK_URL: &str = "https://d.officecli.ai/install.ps1";
pub(crate) const OFFICECLI_INSTALL_SH_URL: &str =
    "https://raw.githubusercontent.com/halojerry/OfficeCLI/main/install.sh";
pub(crate) const OFFICECLI_INSTALL_PS1_URL: &str =
    "https://raw.githubusercontent.com/halojerry/OfficeCLI/main/install.ps1";
pub(crate) const OFFICECLI_LATEST_RELEASE_URL: &str = "https://github.com/halojerry/OfficeCLI/releases/latest";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum OfficecliInstallPlatform {
    Unix,
    Windows,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct OfficecliInstallCommand {
    pub program: OsString,
    pub args: Vec<OsString>,
}

pub(crate) fn resolve_officecli_path() -> Option<PathBuf> {
    // 1. Check bundled path (next to poundingcore binary — out-of-box experience)
    if let Some(bundled) = resolve_bundled_officecli() {
        return Some(bundled);
    }
    // 2. Check PATH
    resolve_command_path("officecli")
        // 3. Check known install locations
        .or_else(resolve_known_officecli_install_path)
}

/// Resolve officecli from the same directory as the poundingcore binary
/// (bundled for out-of-box experience in Electron app).
fn resolve_bundled_officecli() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let name = if cfg!(windows) { "officecli.exe" } else { "officecli" };
    let candidate = dir.join(name);
    if candidate.is_file() { Some(candidate) } else { None }
}

pub(crate) fn install_command() -> OfficecliInstallCommand {
    if cfg!(windows) {
        install_command_for_platform(OfficecliInstallPlatform::Windows)
    } else {
        install_command_for_platform(OfficecliInstallPlatform::Unix)
    }
}

pub(crate) fn install_command_for_platform(platform: OfficecliInstallPlatform) -> OfficecliInstallCommand {
    match platform {
        OfficecliInstallPlatform::Windows => OfficecliInstallCommand {
            program: OsString::from("powershell.exe"),
            args: vec![
                OsString::from("-NoProfile"),
                OsString::from("-ExecutionPolicy"),
                OsString::from("Bypass"),
                OsString::from("-Command"),
                OsString::from(format!(
                    "$ErrorActionPreference='Stop'; try {{ $s = irm {OFFICECLI_INSTALL_PS1_MIRROR_URL} }} catch {{ try {{ $s = irm {OFFICECLI_INSTALL_PS1_FALLBACK_URL} }} catch {{ $s = irm {OFFICECLI_INSTALL_PS1_URL} }} }}; iex $s"
                )),
            ],
        },
        OfficecliInstallPlatform::Unix => OfficecliInstallCommand {
            program: OsString::from("bash"),
            args: vec![
                OsString::from("-lc"),
                // Three-tier fallback: POUNDING COS → official mirror → upstream GitHub
                OsString::from(format!(
                    "f=$(mktemp) || exit 1; (curl -fsSL {OFFICECLI_INSTALL_SH_MIRROR_URL} -o \"$f\" || curl -fsSL {OFFICECLI_INSTALL_SH_FALLBACK_URL} -o \"$f\" || curl -fsSL {OFFICECLI_INSTALL_SH_URL} -o \"$f\") && bash \"$f\"; s=$?; rm -f \"$f\"; exit $s"
                )),
            ],
        },
    }
}

fn resolve_known_officecli_install_path() -> Option<PathBuf> {
    resolve_known_officecli_install_path_from_env(
        std::env::var_os("HOME").as_deref(),
        std::env::var_os("LOCALAPPDATA").as_deref(),
    )
}

fn resolve_known_officecli_install_path_from_env(
    home: Option<&OsStr>,
    local_app_data: Option<&OsStr>,
) -> Option<PathBuf> {
    let mut candidates = Vec::new();

    if let Some(local_app_data) = local_app_data {
        candidates.push(PathBuf::from(local_app_data).join("OfficeCli").join("officecli.exe"));
    }

    if let Some(home) = home {
        candidates.push(PathBuf::from(home).join(".local").join("bin").join("officecli"));
    }

    candidates.into_iter().find(|path| path.is_file())
}

#[cfg(test)]
pub(crate) fn resolve_officecli_path_from_env_for_test(
    path_env: Option<&OsStr>,
    home: Option<&Path>,
    local_app_data: Option<&Path>,
) -> Option<PathBuf> {
    find_officecli_in_path(path_env).or_else(|| {
        resolve_known_officecli_install_path_from_env(home.map(Path::as_os_str), local_app_data.map(Path::as_os_str))
    })
}

#[cfg(test)]
fn find_officecli_in_path(path_env: Option<&OsStr>) -> Option<PathBuf> {
    let path_env = path_env?;
    for dir in std::env::split_paths(path_env) {
        let candidate = dir.join("officecli");
        if candidate.is_file() {
            return Some(candidate);
        }

        #[cfg(windows)]
        {
            let candidate = dir.join("officecli.exe");
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }
    None
}

#[cfg(test)]
pub(crate) fn install_command_for_test(platform: OfficecliInstallPlatform) -> OfficecliInstallCommand {
    install_command_for_platform(platform)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_marker_file(path: &std::path::Path) {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, b"#!/bin/sh\nexit 0\n").unwrap();
    }

    #[test]
    fn officecli_resolution_uses_path_binary_not_legacy_prefix() {
        let tmp = tempfile::tempdir().unwrap();
        let path_bin = tmp.path().join("path-bin").join("officecli");
        let legacy_bin = ["runtime", "node", "tools", "officecli", "bin", "officecli"]
            .into_iter()
            .fold(tmp.path().to_path_buf(), |path, segment| path.join(segment));
        write_marker_file(&path_bin);
        write_marker_file(&legacy_bin);

        let path_env = std::env::join_paths([path_bin.parent().unwrap()]).unwrap();
        let resolved = resolve_officecli_path_from_env_for_test(Some(&path_env), Some(tmp.path()), None);

        assert_eq!(resolved, Some(path_bin));
    }

    #[test]
    fn officecli_resolution_discovers_windows_installer_location() {
        let tmp = tempfile::tempdir().unwrap();
        let local_app_data = tmp.path().join("LocalAppData");
        let officecli_exe = local_app_data.join("OfficeCli").join("officecli.exe");
        std::fs::create_dir_all(officecli_exe.parent().unwrap()).unwrap();
        std::fs::write(&officecli_exe, b"fake exe").unwrap();

        let resolved = resolve_officecli_path_from_env_for_test(None, None, Some(&local_app_data));

        assert_eq!(resolved, Some(officecli_exe));
    }

    #[test]
    fn official_installer_commands_use_officecli_channel() {
        let unix = install_command_for_test(OfficecliInstallPlatform::Unix);
        let windows = install_command_for_test(OfficecliInstallPlatform::Windows);
        let unix_text = format!("{:?} {:?}", unix.program, unix.args);
        let windows_text = format!("{:?} {:?}", windows.program, windows.args);

        // Should include the upstream GitHub fallback URL as the last resort
        assert!(unix_text.contains("halojerry/OfficeCLI/main/install.sh"));
        assert!(windows_text.contains("halojerry/OfficeCLI/main/install.ps1"));
    }

    // Three-tier fallback: POUNDING COS → d.officecli.ai mirror → upstream GitHub.
    #[test]
    fn installer_commands_use_cos_then_mirror_then_github() {
        let unix = install_command_for_test(OfficecliInstallPlatform::Unix);
        let windows = install_command_for_test(OfficecliInstallPlatform::Windows);
        let unix_text = format!("{:?} {:?}", unix.program, unix.args);
        let windows_text = format!("{:?} {:?}", windows.program, windows.args);

        let unix_cos = unix_text.find("pounding/officecli/install.sh");
        let unix_mirror = unix_text.find("d.officecli.ai/install.sh");
        let unix_github = unix_text.find("halojerry/OfficeCLI/main/install.sh");
        assert!(unix_cos.is_some(), "unix installer must include COS URL");
        assert!(
            unix_cos < unix_mirror,
            "unix installer must try COS before mirror"
        );
        assert!(
            unix_mirror < unix_github,
            "unix installer must try mirror before GitHub"
        );

        let windows_cos = windows_text.find("pounding/officecli/install.ps1");
        let windows_mirror = windows_text.find("d.officecli.ai/install.ps1");
        let windows_github = windows_text.find("halojerry/OfficeCLI/main/install.ps1");
        assert!(windows_cos.is_some(), "windows installer must include COS URL");
        assert!(
            windows_cos < windows_mirror,
            "windows installer must try COS before mirror"
        );
        assert!(
            windows_mirror < windows_github,
            "windows installer must try mirror before GitHub"
        );
    }
}
