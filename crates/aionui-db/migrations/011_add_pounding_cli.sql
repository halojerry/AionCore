-- Migration 008: Brand POUNDING CLI agent
-- Overwrites the upstream "Aion CLI" (id=632f31d2) with POUNDING branding.
-- Column list matches the seed INSERT in 001_initial_schema.sql.

INSERT OR REPLACE INTO agent_metadata
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
