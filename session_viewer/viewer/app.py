"""Flask web app for session viewing."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__, template_folder="templates", static_folder="static")

DB_PATH = Path.home() / ".openclaw" / "sessions.db"


def get_db():
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    return cx


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sessions")
def api_sessions():
    agent = request.args.get("agent")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    cx = get_db()
    if agent:
        rows = cx.execute(
            "SELECT * FROM sessions WHERE agent=? ORDER BY first_ts DESC LIMIT ? OFFSET ?",
            (agent, limit, offset)
        ).fetchall()
        total = cx.execute("SELECT COUNT(*) FROM sessions WHERE agent=?", (agent,)).fetchone()[0]
    else:
        rows = cx.execute(
            "SELECT * FROM sessions ORDER BY first_ts DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        total = cx.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    sessions = [dict(r) for r in rows]
    cx.close()
    return jsonify({"sessions": sessions, "total": total, "limit": limit, "offset": offset})


@app.route("/api/sessions/<session_id>")
def api_session(session_id):
    cx = get_db()
    msgs = cx.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    if not msgs:
        abort(404)
    return jsonify({"messages": [dict(m) for m in msgs]})


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": [], "total": 0})

    cx = get_db()
    # Simple LIKE search on content
    rows = cx.execute("""
        SELECT m.*, s.agent, s.label
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.content LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT 50
    """, (f"%{q}%",)).fetchall()
    total = len(rows)
    cx.close()
    return jsonify({"results": [dict(r) for r in rows], "total": total})


@app.route("/api/agents")
def api_agents():
    cx = get_db()
    rows = cx.execute("""
        SELECT agent, COUNT(*) as session_count, SUM(message_count) as msg_count
        FROM sessions GROUP BY agent
    """).fetchall()
    cx.close()
    return jsonify({"agents": [dict(r) for r in rows]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8787, debug=False)
