"""SQLite schema and database management."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    agent           TEXT NOT NULL,
    label           TEXT,
    first_ts        INTEGER NOT NULL,
    last_ts         INTEGER,
    message_count   INTEGER DEFAULT 0,
    raw_file        TEXT,
    imported_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
    sender          TEXT,                    -- 'user' | 'hecate' | ...
    account_name    TEXT,
    timestamp       INTEGER NOT NULL,
    type            INTEGER DEFAULT 0,       -- 0=TEXT, 1=IMAGE, 80=SYSTEM
    content         TEXT,                     -- extracted text (may be truncated)
    thinking        TEXT,                     -- full thinking content
    raw_blocks      TEXT,                     -- JSON of all content blocks
    parent_id       TEXT,
    imported_at     INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent);
CREATE INDEX IF NOT EXISTS idx_sessions_first_ts ON sessions(first_ts);

-- FTS5 for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=rowid
);
"""


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    # Triggers to keep FTS in sync
    conn.executescript("""
    CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
    END;
    CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    END;
    CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
        INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
    END;
    """)
    conn.commit()
    conn.close()
