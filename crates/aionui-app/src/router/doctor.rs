//! Doctor diagnostic and repair API endpoints.
//!
//! - `GET  /api/doctor/diagnose` — full system diagnostic snapshot
//! - `POST /api/doctor/repair`   — attempt to repair a specific agent/resource

use axum::Router;
use axum::extract::Json;
use axum::extract::State;
use axum::http::StatusCode;
use axum::routing::{get, post};

use aionui_api_types::{
    AcpBridgeDiagnostics, AgentDiagnosticEntry, AgentDiagnosticReport, AgentSource, DiagnosticSummary, RepairRequest,
    RepairResult, RuntimeDiagnostics, RuntimeStatus,
};

use crate::router::state::ModuleStates;

/// Build the diagnostic report from the live registry snapshot.
async fn diagnose(State(states): State<ModuleStates>) -> (StatusCode, Json<AgentDiagnosticReport>) {
    let snapshot = states.agent.agent_registry.diagnostic_snapshot().await;

    let agents: Vec<AgentDiagnosticEntry> = snapshot
        .into_iter()
        .map(|(meta, reason)| AgentDiagnosticEntry {
            name: meta.name,
            backend: meta.backend,
            available: meta.available,
            reason: reason.map(|r| r.to_string()),
            bundled_source: matches!(meta.agent_source, AgentSource::Internal | AgentSource::Builtin),
        })
        .collect();

    let runtimes = check_runtimes();
    let acp_bridges = check_acp_bridges();

    let mut issues: Vec<String> = Vec::new();
    for a in &agents {
        if !a.available {
            if let Some(ref reason) = a.reason {
                issues.push(format!("Agent '{}' unavailable: {}", a.name, reason));
            } else {
                issues.push(format!("Agent '{}' unavailable", a.name));
            }
        }
    }
    if !runtimes.uv.available {
        issues.push("uv runtime not found".into());
    }
    if !runtimes.python.available {
        issues.push("python runtime not found".into());
    }
    if !runtimes.hermes.available {
        issues.push("hermes runtime not found".into());
    }
    if !acp_bridges.claude.available {
        issues.push("claude ACP bridge not found".into());
    }
    if !acp_bridges.codex.available {
        issues.push("codex ACP bridge not found".into());
    }

    let healthy = issues.is_empty();

    let report = AgentDiagnosticReport {
        agents,
        runtimes,
        acp_bridges,
        summary: DiagnosticSummary { healthy, issues },
    };

    (StatusCode::OK, Json(report))
}

/// Attempt to repair a target agent or resource.
async fn repair(
    State(states): State<ModuleStates>,
    Json(req): Json<RepairRequest>,
) -> (StatusCode, Json<RepairResult>) {
    let result = states
        .agent
        .agent_registry
        .attempt_repair(&req.target)
        .await
        .unwrap_or_else(|e| RepairResult {
            success: false,
            source: None,
            error: Some(e.to_string()),
        });
    (StatusCode::OK, Json(result))
}

fn check_runtimes() -> RuntimeDiagnostics {
    RuntimeDiagnostics {
        uv: check_binary("uv"),
        python: check_binary("python3"),
        hermes: check_binary("hermes"),
    }
}

fn check_acp_bridges() -> AcpBridgeDiagnostics {
    AcpBridgeDiagnostics {
        claude: check_binary("claude"),
        codex: check_binary("codex"),
    }
}

fn check_binary(name: &str) -> RuntimeStatus {
    match aionui_runtime::resolve_command_path(name) {
        Some(path) => RuntimeStatus {
            available: true,
            path: Some(path.display().to_string()),
        },
        None => RuntimeStatus {
            available: false,
            path: None,
        },
    }
}

/// Assemble doctor routes with the given module states.
pub fn doctor_routes(states: ModuleStates) -> Router {
    Router::new()
        .route("/api/doctor/diagnose", get(diagnose))
        .route("/api/doctor/repair", post(repair))
        .with_state(states)
}
