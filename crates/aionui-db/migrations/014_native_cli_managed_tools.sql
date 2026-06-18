-- Migration 014: Native CLI builtin rows now resolve through managed
-- native CLI artifacts instead of PATH-based lookup.
--
-- Hermes, OpenCode, and OpenClaw are auto-installed from GitHub Releases
-- into the runtime cache at startup. These rows no longer need a persisted
-- spawn command — runtime resolution derives the command plan from the
-- managed native CLI artifact.
--
-- Keep `backend` as the durable source-of-truth. Runtime resolution now
-- derives the actual binary path from managed native CLI artifacts.

-- Hermes (55f3ed1c)
-- command=NULL routes spawn through native_cli_runtime (managed tool path).
-- args keep upstream ["acp"] so CLI starts in ACP mode, not interactive.
UPDATE agent_metadata
SET command           = NULL,
    agent_source_info = json_remove(COALESCE(agent_source_info, '{}'), '$.binary_name'),
    updated_at        = CAST(strftime('%s','now') AS INTEGER) * 1000
WHERE id = '55f3ed1c'
  AND agent_source = 'builtin'
  AND backend = 'hermes';

-- OpenCode (53861a53)
UPDATE agent_metadata
SET command           = NULL,
    agent_source_info = json_remove(COALESCE(agent_source_info, '{}'), '$.binary_name'),
    updated_at        = CAST(strftime('%s','now') AS INTEGER) * 1000
WHERE id = '53861a53'
  AND agent_source = 'builtin'
  AND backend = 'opencode';

-- OpenClaw ACP (b7e8a9c4)
UPDATE agent_metadata
SET command           = NULL,
    agent_source_info = json_remove(COALESCE(agent_source_info, '{}'), '$.binary_name'),
    updated_at        = CAST(strftime('%s','now') AS INTEGER) * 1000
WHERE id = 'b7e8a9c4'
  AND agent_source = 'builtin'
  AND backend = 'openclaw';
