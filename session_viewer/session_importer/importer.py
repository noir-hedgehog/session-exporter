"""Import JSONL sessions into SQLite."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from pathlib import Path

from .db import init_db
from .parser import iter_session_files, parse_session_file


def import_session(session_path: Path, agent: str, db_path: Path, verbose: bool = False) -> int:
    """Import a single session file. Returns number of messages imported."""
    conn = db_path
    session = parse_session_file(session_path, agent)
    if not session:
        return 0

    now = int(time.time())

    # Upsert session
    import sqlite3
    cx = sqlite3.connect(db_path)
    cx.execute("""
        INSERT INTO sessions (id, agent, label, first_ts, last_ts, message_count, raw_file, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            label=excluded.label,
            last_ts=excluded.last_ts,
            message_count=excluded.message_count,
            imported_at=excluded.imported_at
    """, (session.id, session.agent, session.label, session.first_ts, session.last_ts,
          len(session.messages), str(session_path), now))

    # Import messages
    for msg in session.messages:
        cx.execute("""
            INSERT OR IGNORE INTO messages
            (id, session_id, role, sender, account_name, timestamp, type, content, thinking, raw_blocks, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg.id or hashlib.md5(f"{session.id}{msg.timestamp}".encode()).hexdigest()[:16],
            session.id, msg.role, msg.sender, msg.account_name,
            msg.timestamp, msg.type, msg.content, msg.thinking,
            json.dumps(msg.raw_blocks, ensure_ascii=False), now
        ))

    cx.commit()
    cx.close()
    return len(session.messages)


def import_all(agents: list[str], db_path: Path, verbose: bool = False) -> dict:
    """Import all sessions for given agents."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    total_sessions = 0
    total_messages = 0

    for agent in agents:
        for session_file in iter_session_files(agent):
            n = import_session(session_file, agent, db_path, verbose)
            if n > 0:
                total_sessions += 1
                total_messages += n
                if verbose:
                    print(f"  ✓ {agent}/{session_file.name}: {n} messages")

    return {"sessions": total_sessions, "messages": total_messages}
