//! Bundle the uv Python package manager into managed resources.

use std::path::{Path, PathBuf};

use aionui_runtime::managed_resources::materialize_directory;
use anyhow::{Context, Result};
use flate2::read::GzDecoder;
use tar::Archive;

/// Platform-specific download info for uv.
struct UvPlatform {
    /// URL path suffix, e.g. "uv-aarch64-apple-darwin.tar.gz"
    url_suffix: &'static str,
    /// Whether the archive is a .zip (Windows) or .tar.gz (others)
    is_zip: bool,
}

impl UvPlatform {
    fn for_current() -> Result<Self> {
        match (std::env::consts::OS, std::env::consts::ARCH) {
            ("macos", "aarch64") => Ok(Self {
                url_suffix: "uv-aarch64-apple-darwin.tar.gz",
                is_zip: false,
            }),
            ("macos", "x86_64") => Ok(Self {
                url_suffix: "uv-x86_64-apple-darwin.tar.gz",
                is_zip: false,
            }),
            ("windows", "x86_64") => Ok(Self {
                url_suffix: "uv-x86_64-pc-windows-msvc.zip",
                is_zip: true,
            }),
            ("linux", "x86_64") => Ok(Self {
                url_suffix: "uv-x86_64-unknown-linux-gnu.tar.gz",
                is_zip: false,
            }),
            ("linux", "aarch64") => Ok(Self {
                url_suffix: "uv-aarch64-unknown-linux-gnu.tar.gz",
                is_zip: false,
            }),
            (os, arch) => anyhow::bail!("unsupported platform for uv: {os}/{arch}"),
        }
    }
}

/// Download and export the uv runtime into `output_root/runtimes/uv/`.
pub async fn ensure_uv(output_root: &Path) -> Result<(String, PathBuf)> {
    let platform = UvPlatform::for_current()?;
    let url = format!(
        "https://github.com/astral-sh/uv/releases/latest/download/{}",
        platform.url_suffix
    );

    let temp_dir = tempfile::tempdir().context("create temp dir for uv")?;
    let archive_path = temp_dir.path().join("uv_archive");

    // Download.
    let response = reqwest::get(&url)
        .await
        .context("download uv")?
        .error_for_status()
        .with_context(|| format!("download uv from {url}"))?;
    let bytes = response.bytes().await.context("read uv response")?;
    std::fs::write(&archive_path, &bytes).context("write uv archive")?;

    // Extract.
    let extract_dir = temp_dir.path().join("extracted");
    std::fs::create_dir_all(&extract_dir).context("create uv extract dir")?;

    if platform.is_zip {
        extract_zip(&archive_path, &extract_dir)?;
    } else {
        extract_tar_gz(&archive_path, &extract_dir)?;
    }

    // The archive typically contains a single directory with the uv binary inside.
    // Flatten: find the uv/uv.exe binary and place it in a flat layout.
    let flat_dir = temp_dir.path().join("flat");
    std::fs::create_dir_all(&flat_dir).context("create uv flat dir")?;
    copy_binary_recursive(&extract_dir, &flat_dir, "uv")?;

    // Use materialize_directory to copy to output.
    let target = output_root.join("runtimes").join("uv");
    materialize_directory(&flat_dir, &target).context("materialize uv runtime")?;

    Ok(("uv".to_string(), target))
}

fn extract_tar_gz(archive_path: &Path, dest: &Path) -> Result<()> {
    let file = std::fs::File::open(archive_path).context("open uv tar.gz")?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);
    archive.unpack(dest).context("extract uv tar.gz")?;
    Ok(())
}

fn extract_zip(archive_path: &Path, dest: &Path) -> Result<()> {
    let file = std::fs::File::open(archive_path).context("open uv zip")?;
    let mut archive = zip::ZipArchive::new(file).context("read uv zip")?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i)?;
        let Some(name) = entry.enclosed_name() else {
            continue;
        };
        let output_path = dest.join(name);

        if entry.is_dir() {
            std::fs::create_dir_all(&output_path)?;
        } else {
            if let Some(parent) = output_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let mut writer = std::fs::File::create(&output_path)?;
            std::io::copy(&mut entry, &mut writer)?;
        }

        #[cfg(unix)]
        if let Some(mode) = entry.unix_mode() {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = std::fs::metadata(&output_path)?.permissions();
            perms.set_mode(mode);
            std::fs::set_permissions(&output_path, perms)?;
        }
    }

    Ok(())
}

/// Recursively find a binary named `name` (or `{name}.exe` on Windows) and copy
/// it flat into `dest`.
fn copy_binary_recursive(src: &Path, dest: &Path, name: &str) -> Result<()> {
    let exe_name = if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_string()
    };

    for entry in walkdir::WalkDir::new(src) {
        let entry = entry?;
        if entry.file_type().is_file() && entry.file_name().to_string_lossy() == exe_name {
            let target = dest.join(&exe_name);
            std::fs::copy(entry.path(), &target)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = std::fs::metadata(&target)?.permissions();
                perms.set_mode(0o755);
                std::fs::set_permissions(&target, perms)?;
            }
            return Ok(());
        }
    }

    anyhow::bail!("could not find {} in extracted uv archive", exe_name)
}
