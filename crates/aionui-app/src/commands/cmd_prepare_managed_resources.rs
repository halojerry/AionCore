use std::process::ExitCode;

use crate::cli::PrepareManagedResourcesArgs;
use crate::commands::error::{CliBoundaryCode, CliBoundaryError};
use aionui_runtime::acp_tool_runtime::ManagedAcpToolId;
use aionui_runtime::managed_resources::export_node_runtime_to_root;
use aionui_runtime::native_cli_runtime::NativeCliToolId;
use aionui_runtime::{ensure_native_cli_tool, ensure_node_runtime, prepare_managed_acp_tool_to_root};

const SUBCOMMAND: &str = "prepare-managed-resources";

pub async fn run_prepare_managed_resources(args: PrepareManagedResourcesArgs) -> Result<ExitCode, CliBoundaryError> {
    let output_root = args.bundle_out;
    std::fs::create_dir_all(&output_root).map_err(|_| prepare_managed_resources_error("output.create"))?;
    // Canonicalize to an absolute path so that all derived paths (staging
    // directories, package roots, and smoke test targets) are absolute.
    // Without this, a relative --bundle-out (e.g. `./managed-resources`)
    // causes Node subprocesses to resolve relative paths against a different
    // CWD and produce doubled staging paths.
    let output_root =
        std::fs::canonicalize(&output_root).map_err(|_| prepare_managed_resources_error("output.canonicalize"))?;

    let node_runtime = ensure_node_runtime()
        .await
        .map_err(|error| prepare_managed_resources_error_with_detail("node.prepare", error))?;
    let node_dir_name = node_runtime
        .root
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| prepare_managed_resources_error("node.layout"))?;
    let exported_node = export_node_runtime_to_root(&output_root, &node_runtime.root, node_dir_name)
        .map_err(|error| prepare_managed_resources_error_with_detail("node.export", error))?;

    println!("Prepared managed resources under {}", output_root.display());
    println!("  node   -> {}", exported_node.display());

    for tool in [ManagedAcpToolId::CodexAcp, ManagedAcpToolId::ClaudeAgentAcp] {
        let prepared = prepare_managed_acp_tool_to_root(tool, &output_root)
            .await
            .map_err(|error| prepare_managed_resources_error_with_detail("acp.prepare", error))?;
        println!("  {:<6} -> {}", tool.slug(), prepared.root.display());
    }

    for tool in [
        NativeCliToolId::Hermes,
        NativeCliToolId::OpenCode,
        NativeCliToolId::OpenClaw,
    ] {
        let resolved = ensure_native_cli_tool(tool)
            .await
            .map_err(|error| prepare_managed_resources_error_with_detail("native-cli.prepare", error))?;
        let dest_dir = output_root
            .join("cli")
            .join(tool.slug())
            .join(tool.version())
            .join(detect_platform_key());
        copy_directory(&resolved.root, &dest_dir)
            .map_err(|error| prepare_managed_resources_error_with_detail("native-cli.export", error))?;
        println!("  {:<6} -> {}", tool.slug(), dest_dir.display());
    }

    Ok(ExitCode::SUCCESS)
}

fn detect_platform_key() -> &'static str {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "darwin-arm64",
        ("macos", "x86_64") => "darwin-x64",
        ("linux", "aarch64") => "linux-arm64",
        ("linux", "x86_64") => "linux-x64",
        ("windows", "x86_64") => "win32-x64",
        ("windows", "aarch64") => "win32-arm64",
        _ => "unknown",
    }
}

fn copy_directory(src: &std::path::Path, dest: &std::path::Path) -> Result<(), String> {
    if !src.is_dir() {
        return Err(format!("source directory missing: {}", src.display()));
    }
    std::fs::create_dir_all(dest).map_err(|e| format!("create dest dir {dest:?}: {e}"))?;
    for entry in std::fs::read_dir(src).map_err(|e| format!("read dir {src:?}: {e}"))? {
        let entry = entry.map_err(|e| format!("read entry: {e}"))?;
        let src_path = entry.path();
        let dest_path = dest.join(entry.file_name());
        if src_path.is_dir() {
            copy_directory(&src_path, &dest_path)?;
        } else {
            std::fs::copy(&src_path, &dest_path).map_err(|e| format!("copy file {src_path:?}: {e}"))?;
        }
    }
    Ok(())
}

fn prepare_managed_resources_error(stage: &'static str) -> CliBoundaryError {
    CliBoundaryError::new(
        CliBoundaryCode::CliPrepareManagedResourcesFailed,
        SUBCOMMAND,
        "failed to prepare managed resources",
    )
    .with_field("stage", stage)
}

fn prepare_managed_resources_error_with_detail(stage: &'static str, error: impl std::fmt::Display) -> CliBoundaryError {
    eprintln!("prepare-managed-resources stage={stage} detail: {error}");
    prepare_managed_resources_error(stage)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prepare_error_uses_stable_code_and_stage_without_raw_path() {
        let err = prepare_managed_resources_error("node.export");

        assert_eq!(err.code(), CliBoundaryCode::CliPrepareManagedResourcesFailed);
        assert!(err.stderr_line().starts_with(
            "CLI_PREPARE_MANAGED_RESOURCES_FAILED subcommand=prepare-managed-resources stage=node.export"
        ));
        assert!(!err.stderr_line().contains("/Users/secret/bundle"));
    }
}
