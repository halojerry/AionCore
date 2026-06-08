//! Bundle a python-build-standalone distribution into managed resources.

use std::path::{Path, PathBuf};

use aionui_runtime::managed_resources::materialize_directory;
use anyhow::{Context, Result};
use flate2::read::GzDecoder;
use tar::Archive;

/// Python version to bundle.
const PYTHON_VERSION: &str = "3.12";

/// Known-good release date for python-build-standalone (use a recent stable date).
const PYTHON_RELEASE_DATE: &str = "20241206";

/// Platform-specific download info for python-build-standalone.
struct PythonPlatform {
    /// Target triple suffix for indygreg/python-build-standalone releases.
    target_triple: &'static str,
}

impl PythonPlatform {
    fn for_current() -> Result<Self> {
        match (std::env::consts::OS, std::env::consts::ARCH) {
            ("macos", "aarch64") => Ok(Self {
                target_triple: "aarch64-apple-darwin",
            }),
            ("macos", "x86_64") => Ok(Self {
                target_triple: "x86_64-apple-darwin",
            }),
            ("windows", "x86_64") => Ok(Self {
                target_triple: "x86_64-pc-windows-msvc",
            }),
            ("windows", "aarch64") => Ok(Self {
                target_triple: "aarch64-pc-windows-msvc",
            }),
            ("linux", "x86_64") => Ok(Self {
                target_triple: "x86_64-unknown-linux-gnu",
            }),
            ("linux", "aarch64") => Ok(Self {
                target_triple: "aarch64-unknown-linux-gnu",
            }),
            (os, arch) => anyhow::bail!("unsupported platform for python-build-standalone: {os}/{arch}"),
        }
    }
}

/// Download and export a standalone Python runtime into `output_root/runtimes/python/`.
pub async fn ensure_python(output_root: &Path) -> Result<(String, PathBuf)> {
    let platform = PythonPlatform::for_current()?;

    let filename = format!(
        "cpython-{PYTHON_VERSION}.x+{PYTHON_RELEASE_DATE}-{}-install_only.tar.gz",
        platform.target_triple
    );
    let url = format!(
        "https://github.com/indygreg/python-build-standalone/releases/download/{PYTHON_RELEASE_DATE}/{filename}"
    );

    let temp_dir = tempfile::tempdir().context("create temp dir for python")?;
    let archive_path = temp_dir.path().join(&filename);

    // Download.
    let response = reqwest::get(&url)
        .await
        .context("download python-build-standalone")?
        .error_for_status()
        .with_context(|| format!("download python from {url}"))?;
    let bytes = response.bytes().await.context("read python response")?;
    std::fs::write(&archive_path, &bytes).context("write python archive")?;

    // Extract.
    let extract_dir = temp_dir.path().join("extracted");
    std::fs::create_dir_all(&extract_dir).context("create python extract dir")?;
    extract_tar_gz(&archive_path, &extract_dir)?;

    // The archive extracts to a `python/` directory. Flatten it.
    let flat_dir = temp_dir.path().join("flat");
    std::fs::create_dir_all(&flat_dir).context("create python flat dir")?;

    // Find the extracted root directory and copy its contents flat.
    let python_dir = find_python_dir(&extract_dir)?;
    copy_dir_contents(&python_dir, &flat_dir)?;

    // Materialize to output.
    let target = output_root.join("runtimes").join("python");
    materialize_directory(&flat_dir, &target).context("materialize python runtime")?;

    Ok(("python".to_string(), target))
}

fn extract_tar_gz(archive_path: &Path, dest: &Path) -> Result<()> {
    let file = std::fs::File::open(archive_path).context("open python tar.gz")?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);
    archive.unpack(dest).context("extract python tar.gz")?;
    Ok(())
}

/// Find the first subdirectory under `src` that looks like it contains python.
fn find_python_dir(src: &Path) -> Result<PathBuf> {
    // Try `python/` first (common structure).
    let python_dir = src.join("python");
    if python_dir.is_dir() {
        return Ok(python_dir);
    }

    // Otherwise, take the first subdirectory.
    for entry in std::fs::read_dir(src).context("read python extract dir")? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            return Ok(entry.path());
        }
    }

    anyhow::bail!(
        "could not find python directory in extracted archive under {}",
        src.display()
    )
}

fn copy_dir_contents(src: &Path, dest: &Path) -> Result<()> {
    for entry in walkdir::WalkDir::new(src) {
        let entry = entry?;
        let relative = entry.path().strip_prefix(src).unwrap_or(entry.path());

        if relative.as_os_str().is_empty() {
            continue;
        }

        let target = dest.join(relative);

        if entry.file_type().is_dir() {
            std::fs::create_dir_all(&target)?;
            continue;
        }

        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
        }

        if entry.file_type().is_symlink() {
            if target.exists() {
                std::fs::remove_file(&target)?;
            }
            #[cfg(unix)]
            {
                let link_target = std::fs::read_link(entry.path())?;
                std::os::unix::fs::symlink(&link_target, &target)?;
            }
            #[cfg(windows)]
            {
                std::fs::copy(entry.path(), &target)?;
            }
            continue;
        }

        std::fs::copy(entry.path(), &target)?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if let Ok(metadata) = std::fs::metadata(entry.path()) {
                let mut perms = metadata.permissions();
                // Ensure executables are actually executable.
                if perms.mode() & 0o111 != 0 {
                    perms.set_mode(0o755);
                    let _ = std::fs::set_permissions(&target, perms);
                }
            }
        }
    }

    Ok(())
}
