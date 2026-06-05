-- Migration 007: Add POUNDING CLI internal agent
--
-- This entry was originally inlined into 001_initial_schema.sql in the
-- forked branch, which broke sqlx checksums for existing databases
-- ("migration 1 was previously applied but has been modified").
-- Moved to a standalone migration so upgrades from upstream work cleanly.

INSERT OR IGNORE INTO agent_metadata
    (id, icon, name, backend, agent_type, agent_source, agent_source_info,
     enabled, command, args, env, native_skills_dirs, behavior_policy, yolo_id,
     sort_order, created_at, updated_at)
VALUES
    ('632f31d2', '/api/assets/logos/brand/pounding-heart-solid.png', 'POUNDING CLI',
     NULL, 'aionrs', 'internal', '{}',
     1, NULL, '[]', '[]',
     '[".aionrs/skills"]',
     '{"supports_team":true}',
     'yolo', 100,
     unixepoch('now','subsec')*1000, unixepoch('now','subsec')*1000);
