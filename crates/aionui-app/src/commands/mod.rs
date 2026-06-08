//! Subcommand implementations for the `poundingcore` binary.
//!
//! This file is a facade — module declarations and re-exports only.
//! All logic lives in the submodules.

mod bridge;
pub(crate) mod bundle_cli;
pub(crate) mod bundle_hermes;
pub(crate) mod bundle_python;
pub(crate) mod bundle_uv;
mod doctor;
mod prepare_managed_resources;
mod server;
mod team_guide;
mod team_stdio;

pub use bridge::run_mcp_bridge;
pub use doctor::run_doctor;
pub use prepare_managed_resources::run_prepare_managed_resources;
pub(crate) use server::{bind_http_listener, run_server};
pub use team_guide::run_team_guide;
pub use team_stdio::run_team_stdio;
