"""Annual report / 养虾回忆 for OpenClaw sessions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".openclaw" / "sessions.db"


def get_report(year: int | None = None) -> dict:
    """Generate the annual report from SQLite sessions db."""
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    now = datetime.now()

    if year is None:
        year = now.year

    # Basic counts
    total_sessions = cx.execute(
        "SELECT COUNT(*) FROM sessions WHERE first_ts >= ? AND first_ts < ?",
        (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))
    ).fetchone()[0] or 0

    total_messages = cx.execute(
        "SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id WHERE s.first_ts >= ? AND s.first_ts < ?",
        (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))
    ).fetchone()[0] or 0

    # Agent breakdown
    agent_rows = cx.execute("""
        SELECT s.agent, COUNT(DISTINCT s.id) as sessions, SUM(s.message_count) as msgs
        FROM sessions s
        WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY s.agent ORDER BY msgs DESC
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchall()

    # Monthly distribution
    monthly_rows = cx.execute("""
        SELECT strftime('%m', first_ts, 'unixepoch') as month,
               COUNT(*) as sessions, SUM(message_count) as msgs
        FROM sessions
        WHERE first_ts >= ? AND first_ts < ?
        GROUP BY month ORDER BY month
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchall()

    # Hourly distribution (UTC, convert to CST +8)
    hourly_rows = cx.execute("""
        SELECT (CAST(strftime('%H', timestamp, 'unixepoch') AS INTEGER) + 8) % 24 as hour,
               COUNT(*) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY hour ORDER BY hour
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchall()

    # Longest session
    longest = cx.execute("""
        SELECT id, label, agent, message_count, first_ts, last_ts
        FROM sessions WHERE first_ts >= ? AND first_ts < ?
        ORDER BY message_count DESC LIMIT 1
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchone()

    # First and last
    first_sess = cx.execute(
        "SELECT id, label, agent, first_ts FROM sessions WHERE first_ts >= ? AND first_ts < ? ORDER BY first_ts ASC LIMIT 1",
        (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))
    ).fetchone()
    last_sess = cx.execute(
        "SELECT id, label, agent, last_ts FROM sessions WHERE first_ts >= ? AND first_ts < ? ORDER BY last_ts DESC LIMIT 1",
        (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))
    ).fetchone()

    # Message length stats
    len_stats = cx.execute("""
        SELECT AVG(LENGTH(m.content)), MAX(LENGTH(m.content))
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ? AND LENGTH(m.content) > 0
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchone()

    # Top sessions by message count
    top_sessions = cx.execute("""
        SELECT id, label, agent, message_count, first_ts
        FROM sessions WHERE first_ts >= ? AND first_ts < ?
        ORDER BY message_count DESC LIMIT 5
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchall()

    # Average per day
    avg_per_day = cx.execute("""
        SELECT AVG(daily) FROM (
            SELECT COUNT(DISTINCT s.id) as daily
            FROM sessions s
            WHERE s.first_ts >= ? AND s.first_ts < ?
            GROUP BY date(s.first_ts, 'unixepoch')
        )
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchone()[0] or 0

    # User/assistant ratio
    role_stats = cx.execute("""
        SELECT m.role, COUNT(*) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY m.role
    """, (_ts(f"{year}-01-01"), _ts(f"{year+1}-01-01"))).fetchall()

    cx.close()

    def fmt_ts(ts):
        if ts is None: return None
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    return {
        "year": year,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "avg_messages_per_session": round(total_messages / total_sessions, 1) if total_sessions else 0,
        "avg_per_day": round(avg_per_day, 1),
        "avg_message_length": round(len_stats[0] or 0),
        "max_message_length": len_stats[1] or 0,
        "agents": [dict(r) for r in agent_rows],
        "monthly": [dict(r) for r in monthly_rows],
        "hourly": [dict(r) for r in hourly_rows],
        "longest_session": dict(longest) if longest else None,
        "first_session": dict(first_sess) if first_sess else None,
        "last_session": dict(last_sess) if last_sess else None,
        "top_sessions": [dict(r) for r in top_sessions],
        "role_stats": {r["role"]: r["cnt"] for r in role_stats},
    }


def _ts(date_str: str) -> int:
    from datetime import timezone
    return int(datetime.fromisoformat(date_str).timestamp())
