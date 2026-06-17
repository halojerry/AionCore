use super::*;

#[test]
fn probe_resolved_command_accepts_bare_npx_when_managed_runtime_is_supported() {
    if !probe_node_runtime_supported().is_supported() {
        return;
    }

    let meta = AgentMetadata {
        id: "agent-1".into(),
        icon: None,
        name: "Test ACP".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: Some("custom".into()),
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Custom,
        agent_source_info: AgentSourceInfo::default(),
        enabled: true,
        available: false,
        command: Some("npx".into()),
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let resolved = probe_resolved_command(&meta).expect("probe");
    assert_eq!(resolved, PathBuf::from("npx"));
}

#[test]
fn probe_resolved_command_requires_primary_binary_for_builtin_managed_claude() {
    if !probe_node_runtime_supported().is_supported()
        || !probe_managed_acp_tool_supported(ManagedAcpToolId::ClaudeAgentAcp).is_supported()
    {
        return;
    }

    let meta = AgentMetadata {
        id: "agent-claude".into(),
        icon: None,
        name: "Claude Code".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: Some("claude".into()),
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Builtin,
        agent_source_info: AgentSourceInfo {
            binary_name: Some("definitely-missing-claude-cli".into()),
            ..Default::default()
        },
        enabled: true,
        available: false,
        command: None,
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let reason = probe_resolved_command(&meta).expect_err("missing claude CLI must hide builtin row");
    assert!(matches!(
        reason,
        UnavailableReason::PrimaryMissing { binary } if binary == "definitely-missing-claude-cli"
    ));
}

#[test]
fn probe_resolved_command_requires_primary_binary_for_builtin_managed_codex() {
    if !probe_node_runtime_supported().is_supported()
        || !probe_managed_acp_tool_supported(ManagedAcpToolId::CodexAcp).is_supported()
    {
        return;
    }

    let meta = AgentMetadata {
        id: "agent-codex".into(),
        icon: None,
        name: "Codex".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: Some("codex".into()),
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Builtin,
        agent_source_info: AgentSourceInfo {
            binary_name: Some("definitely-missing-codex-cli".into()),
            ..Default::default()
        },
        enabled: true,
        available: false,
        command: None,
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let reason = probe_resolved_command(&meta).expect_err("missing codex CLI must hide builtin row");
    assert!(matches!(
        reason,
        UnavailableReason::PrimaryMissing { binary } if binary == "definitely-missing-codex-cli"
    ));
}

#[test]
fn probe_resolved_command_native_cli_unsupported_yields_managed_runtime_unavailable() {
    if probe_native_cli_tool_supported(NativeCliToolId::Hermes).is_supported() {
        return;
    }

    let meta = AgentMetadata {
        id: "agent-hermes".into(),
        icon: None,
        name: "Hermes".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: Some("hermes".into()),
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Builtin,
        agent_source_info: AgentSourceInfo::default(),
        enabled: true,
        available: false,
        command: None,
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let reason = probe_resolved_command(&meta).expect_err("unsupported native CLI must be unavailable");
    assert!(matches!(
        reason,
        UnavailableReason::ManagedRuntimeUnavailable { resource, .. } if resource == "hermes"
    ));
}

#[test]
fn probe_resolved_command_native_cli_missing_primary_binary_yields_primary_missing() {
    if !probe_native_cli_tool_supported(NativeCliToolId::OpenCode).is_supported() {
        return;
    }

    let meta = AgentMetadata {
        id: "agent-opencode".into(),
        icon: None,
        name: "OpenCode".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: Some("opencode".into()),
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Builtin,
        agent_source_info: AgentSourceInfo {
            binary_name: Some("definitely-missing-opencode-cli".into()),
            ..Default::default()
        },
        enabled: true,
        available: false,
        command: None,
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let reason = probe_resolved_command(&meta).expect_err("missing opencode CLI must hide builtin row");
    assert!(matches!(
        reason,
        UnavailableReason::PrimaryMissing { binary } if binary == "definitely-missing-opencode-cli"
    ));
}

#[test]
fn probe_resolved_command_native_cli_skipped_when_backend_is_command() {
    // Builtin agents with a non-NativeCli backend (or with a command set)
    // should fall through to the generic command probe, not the NativeCli branch.
    let meta = AgentMetadata {
        id: "agent-custom".into(),
        icon: None,
        name: "Custom".into(),
        name_i18n: None,
        description: None,
        description_i18n: None,
        backend: None,
        agent_type: AgentType::Acp,
        agent_source: AgentSource::Builtin,
        agent_source_info: AgentSourceInfo::default(),
        enabled: true,
        available: false,
        command: Some("echo".into()),
        resolved_command: None,
        args: vec![],
        env: vec![],
        native_skills_dirs: None,
        behavior_policy: BehaviorPolicy::default(),
        yolo_id: None,
        sort_order: 0,
        team_capable: false,
        handshake: AgentHandshake::default(),
    };

    let resolved = probe_resolved_command(&meta).expect("echo should be on PATH");
    assert!(
        resolved.to_string_lossy().contains("echo"),
        "expected echo in PATH, got {}",
        resolved.display()
    );
}
