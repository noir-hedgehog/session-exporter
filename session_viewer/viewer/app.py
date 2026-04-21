"""Flask web app for session viewing with multi-framework adapter support."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from report import get_report

app = Flask(__name__, template_folder="templates", static_folder="static")

DB_PATH = Path.home() / ".openclaw" / "sessions.db"
SESSION_BASE_DIR = Path.home() / ".openclaw" / "agents"
CONFIG_PATH = Path(__file__).parent / "config.json"


def get_db():
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    return cx


def get_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "session_dir": str(SESSION_BASE_DIR),
        "adapter": "openclaw",
    }


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ─── Page Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/report")
def report():
    return render_template("report.html")


# ─── Config API ─────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(get_config())

    data = request.get_json() or {}
    cfg = get_config()
    if "session_dir" in data:
        cfg["session_dir"] = data["session_dir"]
    if "adapter" in data:
        cfg["adapter"] = data["adapter"]
    save_config(cfg)
    return jsonify(cfg)


@app.route("/api/session_dir/validate", methods=["POST"])
def api_validate_dir():
    data = request.get_json() or {}
    d = data.get("path", "")
    adapter_name = data.get("adapter", "openclaw")

    if not d or not Path(d).exists() or not Path(d).is_dir():
        return jsonify({"valid": False, "error": "目录不存在或不是有效文件夹"})

    from adapters import ADAPTERS
    adapter_cls = ADAPTERS.get(adapter_name, ADAPTERS["openclaw"])
    adapter = adapter_cls()
    files = list(adapter.iter_sessions(d))
    sample = [str(Path(s.path).relative_to(d)) for s in files[:5]]

    return jsonify({
        "valid": True,
        "file_count": len(files),
        "sample_files": sample
    })


# ─── Import API ─────────────────────────────────────────────────────────────

@app.route("/api/import", methods=["POST"])
def api_import():
    data = request.get_json() or {}
    base_dir = data.get("session_dir", str(SESSION_BASE_DIR))
    adapter_name = data.get("adapter", "openclaw")

    from adapters import ADAPTERS
    adapter_cls = ADAPTERS.get(adapter_name, ADAPTERS["openclaw"])
    adapter = adapter_cls()

    cx = get_db()
    imported = 0
    for si in adapter.iter_sessions(base_dir):
        exists = cx.execute("SELECT id FROM sessions WHERE id=?", (si.id,)).fetchone()
        if not exists:
            cx.execute("""
                INSERT INTO sessions (id, agent, label, first_ts, last_ts, message_count, adapter, path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (si.id, si.agent, si.label, si.first_ts, si.last_ts, si.message_count, si.adapter, si.path))
            imported += 1
            for msg in adapter.parse_session(si.path):
                cx.execute("""
                    INSERT INTO messages (session_id, role, content, type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (si.id, msg.role, msg.content, msg.type, msg.timestamp))

    cx.commit()
    cx.close()
    return jsonify({"imported": imported})


# ─── Session List ────────────────────────────────────────────────────────────

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

    cx.close()
    return jsonify({"sessions": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset})


# ─── Session Detail (with optional highlight) ───────────────────────────────

@app.route("/api/sessions/<session_id>")
def api_session(session_id):
    cx = get_db()
    msgs = cx.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    if not msgs:
        cx.close()
        abort(404)

    hl = request.args.get("hl", "").strip()
    result = []
    for m in msgs:
        d = dict(m)
        content = d.get("content", "") or ""

        if hl:
            lower = content.lower()
            klower = hl.lower()
            idx = lower.find(klower)
            if idx >= 0:
                d["_highlight"] = True
                d["_match_start"] = idx
                d["_match_end"] = idx + len(hl)
                start = max(0, idx - 60)
                end = min(len(content), idx + len(hl) + 60)
                snippet = content[start:end]
                if start > 0: snippet = "…" + snippet
                if end < len(content): snippet = snippet + "…"
                d["_snippet"] = snippet
            else:
                d["_highlight"] = False
                d["_snippet"] = content[:120]
        else:
            d["_snippet"] = content[:120] if content else ""

        result.append(d)

    cx.close()
    return jsonify({"messages": result})


# ─── Search API ─────────────────────────────────────────────────────────────

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": [], "total": 0, "query": ""})

    cx = get_db()
    rows = cx.execute("""
        SELECT m.*, s.agent, s.label, s.first_ts
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.content LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT 100
    """, (f"%{q}%",)).fetchall()
    total = len(rows)
    cx.close()

    results = []
    klen = len(q)
    for r in rows:
        d = dict(r)
        content = d.get("content", "") or ""
        lower = content.lower()
        klower = q.lower()
        idx = lower.find(klower)

        if idx >= 0:
            d["_highlight"] = True
            d["_match_start"] = idx
            d["_match_end"] = idx + klen
            start = max(0, idx - 50)
            end = min(len(content), idx + klen + 50)
            snippet = content[start:end]
            if start > 0: snippet = "…" + snippet
            if end < len(content): snippet = snippet + "…"
        else:
            d["_highlight"] = False
            snippet = content[:100]
        d["_snippet"] = snippet
        results.append(d)

    return jsonify({"results": results, "total": total, "query": q})


# ─── Agents API ─────────────────────────────────────────────────────────────

@app.route("/api/agents")
def api_agents():
    cx = get_db()
    rows = cx.execute("""
        SELECT agent, COUNT(*) as session_count, SUM(message_count) as msg_count
        FROM sessions GROUP BY agent ORDER BY session_count DESC
    """).fetchall()
    cx.close()
    return jsonify({"agents": [dict(r) for r in rows]})


# ─── Report API ─────────────────────────────────────────────────────────────

@app.route("/api/report")
def api_report():
    year = request.args.get("year", type=int)
    return jsonify(get_report(year))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8787, debug=False)
