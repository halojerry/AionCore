//! Bundle JS CLI tools (claude, codex, opencode, openclaw) into managed resources.
//!
//! Each CLI is installed via bun into a temp directory, then the node_modules tree
//! is materialized into the bundle output under `cli/<name>/<version>/<platform>/`.

use std::path::{Path, PathBuf};
use std::process::Stdio;

use aionui_runtime::managed_resources::materialize_directory;
use anyhow::{Context, Result};

/// CLI bundle result: list of (name, path) successes and (name, error) failures.
pub struct CliBundlesResult {
    pub successes: Vec<(String, PathBuf)>,
    pub failures: Vec<(String, String)>,
}

/// Package info for each bundled CLI.
struct CliPackage {
    /// Short name used in output path and logging.
    name: &'static str,
    /// npm package name.
    package: &'static str,
}

const CLI_PACKAGES: &[CliPackage] = &[
    CliPackage {
        name: "claude",
        package: "@anthropic-ai/claude-code",
    },
    CliPackage {
        name: "codex",
        package: "@openai/codex",
    },
    CliPackage {
        name: "opencode",
        package: "opencode-ai",
    },
    CliPackage {
        name: "openclaw",
        package: "openclaw",
    },
];

/// Registry URLs to try (npmmirror.com first, then npmjs.org).
const REGISTRY_MIRRORS: &[&str] = &["https://registry.npmmirror.com", "https://registry.npmjs.org"];

/// Install all CLI packages and export them to the bundle output root.
pub async fn ensure_clis(output_root: &Path) -> CliBundlesResult {
    let platform_key = platform_key();
    let mut successes = Vec::new();
    let mut failures = Vec::new();

    for cli in CLI_PACKAGES {
        match install_and_export_cli(cli, output_root, &platform_key).await {
            Ok((name, path)) => {
                successes.push((name, path));
            }
            Err(error) => {
                failures.push((cli.name.to_string(), format!("{error:#}")));
            }
        }
    }

    CliBundlesResult { successes, failures }
}

/// Install a single CLI package and export it to the bundle.
async fn install_and_export_cli(cli: &CliPackage, output_root: &Path, platform_key: &str) -> Result<(String, PathBuf)> {
    let temp_dir = tempfile::tempdir().context(format!("create temp dir for {}", cli.name))?;
    let project_dir = temp_dir.path().join("project");
    std::fs::create_dir_all(&project_dir)?;

    // Write minimal package.json.
    let package_json = serde_json::json!({
        "name": "cli-bundle",
        "private": true
    });
    std::fs::write(
        project_dir.join("package.json"),
        serde_json::to_vec_pretty(&package_json)?,
    )?;

    // Try each registry mirror until one succeeds.
    install_with_mirrors(cli, &project_dir).await?;

    // Read the installed package.json to determine entrypoint and version.
    let (entrypoint, version, path_entries) = read_installed_package_info(&project_dir, cli)?;

    // Build manifest.
    let manifest = serde_json::json!({
        "entrypoint": entrypoint,
        "path_entries": path_entries,
        "version": version,
        "platform": platform_key
    });
    std::fs::write(project_dir.join("manifest.json"), serde_json::to_vec_pretty(&manifest)?)?;

    // Materialize to output.
    let target = output_root.join("cli").join(cli.name).join(&version).join(platform_key);

    materialize_directory(&project_dir, &target).context(format!("materialize {} CLI bundle", cli.name))?;

    Ok((cli.name.to_string(), target))
}

/// Attempt to install the CLI package, trying each registry mirror.
async fn install_with_mirrors(cli: &CliPackage, project_dir: &Path) -> Result<()> {
    let bun_path = find_bun().context("could not find bun executable")?;

    for registry in REGISTRY_MIRRORS {
        let mut cmd = tokio::process::Command::new(&bun_path);
        cmd.arg("add")
            .arg("--exact")
            .arg("--no-save")
            .current_dir(project_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Set registry via environment.
        cmd.env("BUN_CONFIG_REGISTRY", registry);
        cmd.env("npm_config_registry", registry);

        // No progress bars in CI/bundling.
        cmd.env("NO_COLOR", "1");
        cmd.env("BUN_INSTALL_PROGRESS", "0");

        // Install the package.
        cmd.arg(format!("{}@latest", cli.package));

        let output = cmd.output().await?;

        if output.status.success() {
            return Ok(());
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        if let Some(registry_idx) = REGISTRY_MIRRORS.iter().position(|r| *r == *registry)
            && registry_idx + 1 < REGISTRY_MIRRORS.len()
        {
            eprintln!("  cli:{} install from {registry} failed, trying next mirror", cli.name);
        }

        // If this is the last mirror, return the error.
        if *registry == REGISTRY_MIRRORS.last().copied().unwrap_or("") {
            let stdout_str = String::from_utf8_lossy(&output.stdout);
            let detail = if stderr.is_empty() {
                stdout_str.to_string()
            } else if stdout_str.is_empty() {
                stderr.to_string()
            } else {
                format!("{stderr}; stdout: {stdout_str}")
            };
            anyhow::bail!("bun add {} failed (registry={registry}): {detail}", cli.package);
        }

        // Clean up failed node_modules before trying next mirror.
        let node_modules = project_dir.join("node_modules");
        if node_modules.exists() {
            let _ = std::fs::remove_dir_all(&node_modules);
        }
    }

    anyhow::bail!("no registry mirror succeeded for {}", cli.package)
}

/// Read the installed package's package.json to determine the entrypoint, version, and path_entries.
fn read_installed_package_info(project_dir: &Path, cli: &CliPackage) -> Result<(String, String, Vec<String>)> {
    let package_name = cli.package;

    // Build the path to the installed package's package.json.
    let node_modules = project_dir.join("node_modules");
    let package_json_path = node_modules
        .join(package_name.replace('/', std::path::MAIN_SEPARATOR_STR))
        .join("package.json");

    let contents = std::fs::read_to_string(&package_json_path).with_context(|| {
        format!(
            "read package.json for {} at {}",
            package_name,
            package_json_path.display()
        )
    })?;

    let package_json: serde_json::Value = serde_json::from_str(&contents).context("parse installed package.json")?;

    let version = package_json["version"].as_str().unwrap_or("0.0.0").to_string();

    // Determine entrypoint from the "bin" field.
    let entrypoint = resolve_bin_entry(package_name, &package_json["bin"]).context("could not resolve bin entry")?;

    let entrypoint_rel = PathBuf::from("node_modules")
        .join(package_name.replace('/', std::path::MAIN_SEPARATOR_STR))
        .join(&entrypoint);

    let path_entries = vec!["node_modules/.bin".to_string()];

    Ok((normalize_slashes(&entrypoint_rel), version, path_entries))
}

/// Resolve the bin entry from a package.json bin field.
fn resolve_bin_entry(package_name: &str, bin_field: &serde_json::Value) -> Result<String> {
    match bin_field {
        serde_json::Value::String(value) if !value.is_empty() => Ok(value.clone()),
        serde_json::Value::Object(entries) => {
            let short_name = package_name.rsplit('/').next().unwrap_or(package_name);

            // Prefer the short name key, then the full package name.
            for key in [short_name, package_name] {
                if let Some(serde_json::Value::String(value)) = entries.get(key)
                    && !value.is_empty()
                {
                    return Ok(value.clone());
                }
            }

            // Fallback to any string value.
            entries
                .values()
                .find_map(|value| match value {
                    serde_json::Value::String(value) if !value.is_empty() => Some(value.clone()),
                    _ => None,
                })
                .ok_or_else(|| anyhow::anyhow!("package {package_name} does not expose a usable bin entry"))
        }
        _ => anyhow::bail!("package {package_name} does not expose a usable bin entry"),
    }
}

/// Normalize path separators to forward slashes.
fn normalize_slashes(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

/// Find bun on the system PATH.
fn find_bun() -> Option<PathBuf> {
    // Check env override first.
    if let Ok(path) = std::env::var("AIONUI_BUN_PATH") {
        let p = PathBuf::from(&path);
        if p.is_file() {
            return Some(p);
        }
    }

    // Search PATH.
    which::which("bun").ok()
}

/// Get a platform key string for the current platform.
fn platform_key() -> String {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "darwin-arm64".into(),
        ("macos", "x86_64") => "darwin-x64".into(),
        ("linux", "x86_64") => "linux-x64".into(),
        ("linux", "aarch64") => "linux-arm64".into(),
        ("windows", "x86_64") => "win32-x64".into(),
        ("windows", "aarch64") => "win32-arm64".into(),
        (os, arch) => format!("{os}-{arch}"),
    }
}
