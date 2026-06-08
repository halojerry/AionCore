-- 013: Ensure the pounding-image-generation MCP server row exists and is
-- enabled so that image generation tools are available to all ACP agents.
--
-- The server row must have builtin=1 and enabled=1 for
-- INJECTABLE_BUILTIN_MCP_NAMES ("pounding-image-generation") in factory/acp.rs
-- to inject it into agent sessions via build_builtin_image_gen_server().
--
-- The transport_config.command ("aionui-img-gen") is a placeholder; the actual
-- binary path is resolved at runtime by the managed-resources materializer or
-- falls back to the system PATH.
INSERT OR IGNORE INTO mcp_servers
    (id, name, description, enabled, transport_type, transport_config,
     builtin, created_at, updated_at)
VALUES
    ('pounding-image-gen-builtin', 'pounding-image-generation',
     'POUNDING Image Generation — builtin MCP server for AI image generation',
     1, 'stdio',
     '{"command":"aionui-img-gen","args":[],"env":{}}',
     1,
     unixepoch('now','subsec')*1000, unixepoch('now','subsec')*1000);
