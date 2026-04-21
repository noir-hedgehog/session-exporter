"""
Emotional analytics for the 养虾回忆 H5 report.
Extracts emotionally resonant insights WITHOUT exposing raw message content.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

DB_PATH = Path.home() / ".openclaw" / "sessions.db"

DEMO_MODE = True  # Set to False for local use with real data


def _ts(date_str: str) -> int:
    return int(datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc).timestamp())


def _fmt_ts(ts: int, fmt: str = "%m月%d日 %H:%M") -> str:
    return datetime.fromtimestamp(ts).strftime(fmt)


def get_cards_data(year: int | None = None) -> dict:
    """Generate the full cards dataset for the H5 report."""
    if DEMO_MODE:
        return _get_demo_data(year or datetime.now().year)

    return _get_real_data(year or datetime.now().year)


def _get_real_data(year: int) -> dict:
    """Real data path — only statistics, no raw content exposed."""
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    year_start = _ts(f"{year}-01-01")
    year_end = _ts(f"{year+1}-01-01")

    # --- Basic stats ---
    total_sessions = cx.execute(
        "SELECT COUNT(*) FROM sessions WHERE first_ts >= ? AND first_ts < ?",
        (year_start, year_end)).fetchone()[0] or 0
    total_messages = cx.execute("""
        SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
    """, (year_start, year_end)).fetchone()[0] or 0

    if total_sessions == 0:
        cx.close()
        return _get_demo_data(year)

    # --- Agent breakdown ---
    agents = cx.execute("""
        SELECT s.agent, SUM(s.message_count) as msgs, COUNT(*) as sessions
        FROM sessions s WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY s.agent ORDER BY msgs DESC
    """, (year_start, year_end)).fetchall()

    # --- User vs Assistant ratio ---
    roles = cx.execute("""
        SELECT m.role, COUNT(*) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY m.role
    """, (year_start, year_end)).fetchall()
    role_map = {r["role"]: r["cnt"] for r in roles}
    user_msgs = role_map.get("user", 0)
    assistant_msgs = role_map.get("assistant", 0)

    # --- Late night sessions (after 23:00 or before 05:00 CST = UTC+8) ---
    late_sessions = cx.execute("""
        SELECT s.id, s.label, s.first_ts, s.last_ts, s.message_count,
               (CAST(strftime('%H', s.first_ts, 'unixepoch', '+8 hours') AS INTEGER)) as start_hour
        FROM sessions s WHERE s.first_ts >= ? AND s.first_ts < ?
        HAVING start_hour >= 23 OR start_hour < 5
        ORDER BY start_hour DESC, message_count DESC
    """, (year_start, year_end)).fetchall()

    late_night_sessions = [dict(r) for r in late_sessions]

    # --- Peak day ---
    peak_day = cx.execute("""
        SELECT date(s.first_ts, 'unixepoch', 'localtime') as day,
               COUNT(*) as cnt
        FROM sessions s WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY day ORDER BY cnt DESC LIMIT 1
    """, (year_start, year_end)).fetchone()

    # --- Monthly distribution ---
    monthly = cx.execute("""
        SELECT CAST(strftime('%m', s.first_ts, 'unixepoch') AS INTEGER) as month,
               COUNT(*) as sessions, SUM(s.message_count) as msgs
        FROM sessions s WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY month ORDER BY month
    """, (year_start, year_end)).fetchall()

    # --- Longest session ---
    longest = cx.execute("""
        SELECT * FROM sessions
        WHERE first_ts >= ? AND first_ts < ?
        ORDER BY message_count DESC LIMIT 1
    """, (year_start, year_end)).fetchone()

    # --- Repeated questions (same content pattern, counted by hash bucket) ---
    # We count messages by a simple hash of first 50 chars to detect repetition
    repeated = cx.execute("""
        SELECT SUBSTR(content, 1, 50) as prefix, COUNT(*) as cnt, MAX(LENGTH(content)) as maxlen
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
          AND m.role = 'user' AND LENGTH(m.content) > 5
        GROUP BY prefix HAVING cnt >= 2
        ORDER BY cnt DESC LIMIT 3
    """, (year_start, year_end)).fetchall()

    # --- Most active hour ---
    hourly = cx.execute("""
        SELECT (CAST(strftime('%H', m.timestamp, 'unixepoch', '+8 hours') AS INTEGER)) as hour,
               COUNT(*) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ?
        GROUP BY hour ORDER BY cnt DESC LIMIT 1
    """, (year_start, year_end)).fetchone()

    # --- First and last ---
    first_sess = cx.execute(
        "SELECT * FROM sessions WHERE first_ts >= ? AND first_ts < ? ORDER BY first_ts ASC LIMIT 1",
        (year_start, year_end)).fetchone()
    last_sess = cx.execute(
        "SELECT * FROM sessions WHERE first_ts >= ? AND first_ts < ? ORDER BY last_ts DESC LIMIT 1",
        (year_start, year_end)).fetchone()

    # --- Most talkative agent ---
    top_agent = agents[0] if agents else None

    # --- Longest single message ---
    longest_msg = cx.execute("""
        SELECT LENGTH(content) as len FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE s.first_ts >= ? AND s.first_ts < ? AND LENGTH(content) > 0
        ORDER BY len DESC LIMIT 1
    """, (year_start, year_end)).fetchone()

    cx.close()

    return {
        "year": year,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "user_msgs": user_msgs,
        "assistant_msgs": assistant_msgs,
        "agents": [dict(a) for a in agents],
        "late_night_sessions": late_night_sessions,
        "peak_day": dict(peak_day) if peak_day else None,
        "monthly": [dict(m) for m in monthly],
        "longest_session": dict(longest) if longest else None,
        "repeated_questions": [dict(r) for r in repeated],
        "most_active_hour": dict(hourly)["hour"] if hourly else None,
        "first_session": dict(first_sess) if first_sess else None,
        "last_session": dict(last_sess) if last_sess else None,
        "top_agent": dict(top_agent) if top_agent else None,
        "longest_msg_len": dict(longest_msg)["len"] if longest_msg else 0,
        "is_demo": False,
    }


def _get_demo_data(year: int) -> dict:
    """Demo data — realistic but completely fictional. No real content exposed."""
    return {
        "year": year,
        "total_sessions": 128,
        "total_messages": 5842,
        "user_msgs": 2103,
        "assistant_msgs": 3739,
        "agents": [
            {"agent": "test", "msgs": 3621, "sessions": 78},
            {"agent": "lingxi", "msgs": 1847, "sessions": 42},
            {"agent": "cursor", "msgs": 312, "sessions": 6},
            {"agent": "codex", "msgs": 62, "sessions": 2},
        ],
        "late_night_sessions": [
            {"id": "demo-1", "label": "AgentInput 项目讨论", "first_ts": _ts(f"{year}-04-19T23:42:00"), "message_count": 87},
            {"id": "demo-2", "label": "Session 可视化设计", "first_ts": _ts(f"{year}-03-12T00:18:00"), "message_count": 64},
            {"id": "demo-3", "label": "凌晨需求评审", "first_ts": _ts(f"{year}-02-28T23:55:00"), "message_count": 43},
        ],
        "peak_day": {"day": f"{year}-04-10", "cnt": 12},
        "monthly": [
            {"month": 1, "sessions": 3, "msgs": 82},
            {"month": 2, "sessions": 8, "msgs": 347},
            {"month": 3, "sessions": 29, "msgs": 1248},
            {"month": 4, "sessions": 88, "msgs": 4165},
        ],
        "longest_session": {
            "id": "demo-long", "label": "AgentInput + YuyanIme 集成",
            "first_ts": _ts(f"{year}-04-20T14:22:00"), "last_ts": _ts(f"{year}-04-20T18:05:00"),
            "message_count": 218
        },
        "repeated_questions": [
            {"prefix": "帮我把这个函数优化一下 ", "cnt": 7, "maxlen": 120},
            {"prefix": "为什么这个报错 ", "cnt": 5, "maxlen": 45},
            {"prefix": "继续上次的任务", "cnt": 4, "maxlen": 30},
        ],
        "most_active_hour": 22,
        "first_session": {
            "id": "demo-first", "label": "第一次对话",
            "first_ts": _ts(f"{year}-02-15T09:12:00")
        },
        "last_session": {
            "id": "demo-last", "label": "最新会话",
            "last_ts": _ts(f"{year}-04-21T20:30:00")
        },
        "top_agent": {"agent": "test", "msgs": 3621, "sessions": 78},
        "longest_msg_len": 4821,
        "is_demo": True,
    }


# Compatibility alias
get_report = get_cards_data
