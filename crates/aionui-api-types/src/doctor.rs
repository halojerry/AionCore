//! Doctor diagnostic API types.
//!
//! Exposed through `/api/doctor/diagnose` and `/api/doctor/repair`.

use serde::{Deserialize, Serialize};

/// Full diagnostic report for the doctor API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDiagnosticReport {
    pub agents: Vec<AgentDiagnosticEntry>,
    pub runtimes: RuntimeDiagnostics,
    pub acp_bridges: AcpBridgeDiagnostics,
    pub summary: DiagnosticSummary,
}

/// A single agent's availability snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDiagnosticEntry {
    pub name: String,
    pub backend: Option<String>,
    pub available: bool,
    pub reason: Option<String>,
    pub bundled_source: bool,
}

/// Runtime toolchain availability.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeDiagnostics {
    pub uv: RuntimeStatus,
    pub python: RuntimeStatus,
    pub hermes: RuntimeStatus,
}

/// Status of a single runtime binary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeStatus {
    pub available: bool,
    pub path: Option<String>,
}

/// ACP bridge binary diagnostics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcpBridgeDiagnostics {
    pub claude: RuntimeStatus,
    pub codex: RuntimeStatus,
}

/// Summary of the diagnostic report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiagnosticSummary {
    pub healthy: bool,
    pub issues: Vec<String>,
}

/// Request to repair a specific agent or resource.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepairRequest {
    pub target: String,
}

/// Result of a repair attempt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepairResult {
    pub success: bool,
    pub source: Option<String>,
    pub error: Option<String>,
}
