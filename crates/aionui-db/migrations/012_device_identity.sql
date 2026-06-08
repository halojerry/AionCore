-- 012: Persist OpenClaw device identity as a fallback when ~/.openclaw/identity/device.json
-- is lost, corrupted, or the filesystem is not writable.
--
-- load_or_create_identity() reads from this table when the file-based identity is
-- unavailable, preventing silent identity rotation (new keypair → new device_id) which
-- would cause the gateway to return NOT_PAIRED ("device identity changed").
CREATE TABLE IF NOT EXISTS device_identity (
    device_id TEXT PRIMARY KEY,
    private_key_pem TEXT NOT NULL,
    public_key_pem TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);
