-- Pomotroid v1.7.1 SQLite WAL Schema (MIGRATION_1 through MIGRATION_6)
-- Derived from src-tauri/src/db/migrations.rs (commit 4a02ac7bff9083dc5b2cc42fa7c4683c1fc15805)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    INTEGER NOT NULL,
    ended_at      INTEGER,
    round_type    TEXT NOT NULL CHECK(round_type IN ('work', 'short-break', 'long-break')),
    duration_secs INTEGER NOT NULL CHECK(duration_secs > 0),
    completed     INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS custom_themes (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL UNIQUE,
    colors TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_round_type ON sessions(round_type);

INSERT INTO schema_version VALUES (1);
INSERT INTO schema_version VALUES (2);
INSERT OR IGNORE INTO settings (key, value) VALUES ('check_for_updates', 'true');
INSERT INTO schema_version VALUES (3);
INSERT OR IGNORE INTO settings (key, value) VALUES ('global_shortcuts_enabled', 'false');
INSERT INTO schema_version VALUES (4);
INSERT OR IGNORE INTO settings (key, value) VALUES ('short_breaks_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('long_breaks_enabled', 'true');
INSERT INTO schema_version VALUES (5);
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_toggle', ' ');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_reset', 'ArrowLeft');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_skip', 'ArrowRight');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_volume_down', 'ArrowDown');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_volume_up', 'ArrowUp');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_mute', 'm');
INSERT OR IGNORE INTO settings (key, value) VALUES ('local_shortcut_fullscreen', 'F11');
INSERT INTO schema_version VALUES (6);
