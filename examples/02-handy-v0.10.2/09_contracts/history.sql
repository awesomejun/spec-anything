-- Handy v0.10.2 Transcription History SQLite Schema
-- Source of truth: src-tauri/src/managers/history.rs (MIGRATIONS[0..3] + ADDED_COLUMNS)
-- Database filename: <app_data_dir>/history.db
-- Verified against official macOS Mach-O binary (Handy.app/Contents/MacOS/handy)

PRAGMA foreign_keys = ON;

-- Migration 1: Base transcription_history table
CREATE TABLE IF NOT EXISTS transcription_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    saved BOOLEAN NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    transcription_text TEXT NOT NULL
);

-- Migration 2: Optional LLM post-processed transcript
ALTER TABLE transcription_history ADD COLUMN post_processed_text TEXT;

-- Migration 3: Prompt template snapshot used for post-processing
ALTER TABLE transcription_history ADD COLUMN post_process_prompt TEXT;

-- Migration 4: Flag indicating post-processing was requested for this entry
ALTER TABLE transcription_history ADD COLUMN post_process_requested BOOLEAN NOT NULL DEFAULT 0;

-- rusqlite_migration user_version after MIGRATIONS[0..3]
PRAGMA user_version = 4;

-- Forward-compatible nullable columns appended outside MIGRATIONS (ADDED_COLUMNS)
-- Keeps user_version=4 so older released builds can still open history.db safely.
ALTER TABLE transcription_history ADD COLUMN source_name TEXT;
ALTER TABLE transcription_history ADD COLUMN language TEXT;
ALTER TABLE transcription_history ADD COLUMN language_source TEXT;
