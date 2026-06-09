//! Bundle the hermes-agent Python wheel into managed resources.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

/// Version of hermes-agent to bundle.
const HERMES_VERSION: &str = "0.1.0";

/// Mirror URLs for downloading hermes-agent wheel (tsinghua first, then PyPI fallback).
const TSINGHUA_PYPI_BASE: &str = "https://pypi.tuna.tsinghua.edu.cn";
const PYPI_SIMPLE_BASE: &str = "https://pypi.org/simple";
const PYPI_FILES_BASE: &str = "https://files.pythonhosted.org";

/// Download and export the hermes-agent wheel into `output_root/runtimes/hermes/`.
pub async fn ensure_hermes(output_root: &Path) -> Result<(String, PathBuf)> {
    let wheel_filename = format!("hermes_agent-{HERMES_VERSION}-py3-none-any.whl");

    let temp_dir = tempfile::tempdir().context("create temp dir for hermes")?;
    let wheel_path = temp_dir.path().join(&wheel_filename);

    // Try downloading from tsinghua mirror first.
    let downloaded = match try_download_from_tsinghua(&wheel_filename, &wheel_path).await {
        Ok(path) => path,
        Err(_) => try_download_from_pypi(&wheel_filename, &wheel_path)
            .await
            .context("could not download hermes-agent wheel from any mirror")?,
    };

    // Copy wheel to a clean directory, then materialize.
    let staged = temp_dir.path().join("staged");
    std::fs::create_dir_all(&staged).context("create hermes staged dir")?;
    std::fs::copy(downloaded, staged.join(&wheel_filename)).context("copy hermes wheel")?;

    let target = output_root.join("runtimes").join("hermes");
    aionui_runtime::managed_resources::materialize_directory(&staged, &target).context("materialize hermes wheel")?;

    Ok(("hermes".to_string(), target))
}

/// Try to download from Tsinghua PyPI mirror using the JSON API.
async fn try_download_from_tsinghua(wheel_filename: &str, dest: &Path) -> Result<PathBuf> {
    // Use the simple API to get download URL.
    let simple_url = format!("{TSINGHUA_PYPI_BASE}/simple/hermes-agent/");
    let response = reqwest::get(&simple_url)
        .await
        .context("fetch hermes-agent from tsinghua")?
        .error_for_status()
        .context("tsinghua request failed")?;

    let html = response.text().await.context("read tsinghua response")?;

    // Find the download URL for our wheel file.
    let wheel_url = find_wheel_url_in_html(&html, wheel_filename)?;
    let full_url = if wheel_url.starts_with("http") {
        wheel_url.to_string()
    } else {
        format!("{TSINGHUA_PYPI_BASE}{wheel_url}")
    };

    download_wheel(&full_url, dest).await
}

/// Try to download from the official PyPI files host.
async fn try_download_from_pypi(wheel_filename: &str, dest: &Path) -> Result<PathBuf> {
    // First try the JSON API.
    let json_url = format!("https://pypi.org/pypi/hermes-agent/{HERMES_VERSION}/json");
    if let Ok(response) = reqwest::get(&json_url).await
        && let Ok(json) = response.json::<serde_json::Value>().await
        && let Some(urls) = json["urls"].as_array()
    {
        for url_entry in urls {
            if let Some(filename) = url_entry["filename"].as_str()
                && filename == wheel_filename
                && let Some(url) = url_entry["url"].as_str()
            {
                return download_wheel(url, dest).await;
            }
        }
    }

    // Fallback: try simple index.
    let simple_url = format!("{PYPI_SIMPLE_BASE}/hermes-agent/");
    let response = reqwest::get(&simple_url)
        .await
        .context("fetch hermes-agent from pypi simple")?
        .error_for_status()
        .context("pypi simple request failed")?;

    let html = response.text().await.context("read pypi simple response")?;
    let wheel_url = find_wheel_url_in_html(&html, wheel_filename)?;
    let full_url = if wheel_url.starts_with("http") {
        wheel_url.to_string()
    } else {
        format!("{PYPI_FILES_BASE}{wheel_url}")
    };

    download_wheel(&full_url, dest).await
}

/// Parse PEP 503 simple index HTML to find a wheel URL.
fn find_wheel_url_in_html(html: &str, filename: &str) -> Result<String> {
    for line in html.lines() {
        if line.contains(filename) {
            // Extract href value.
            if let Some(href_start) = line.find("href=\"") {
                let after_href = &line[href_start + 6..];
                if let Some(href_end) = after_href.find('\"') {
                    return Ok(after_href[..href_end].to_string());
                }
            }
            if let Some(href_start) = line.find("href='") {
                let after_href = &line[href_start + 6..];
                if let Some(href_end) = after_href.find('\'') {
                    return Ok(after_href[..href_end].to_string());
                }
            }
        }
    }

    anyhow::bail!("could not find URL for {filename} in simple index HTML")
}

async fn download_wheel(url: &str, dest: &Path) -> Result<PathBuf> {
    let response = reqwest::get(url)
        .await
        .with_context(|| format!("download hermes wheel from {url}"))?
        .error_for_status()
        .with_context(|| format!("download hermes wheel failed: {url}"))?;

    let bytes = response.bytes().await.context("read hermes wheel response")?;
    std::fs::write(dest, &bytes).context("write hermes wheel")?;
    Ok(dest.to_path_buf())
}
