"""Convert parsed sessions to ChatLab standard format."""

from __future__ import annotations

import time
from pathlib import Path

from .parser import ParsedMessage, ParsedSession


def build_chatlab_doc(session: ParsedSession) -> dict:
    """Build a ChatLab-format JSON document from a ParsedSession."""
    # Collect unique members
    members_map: dict[str, dict] = {}
    for msg in session.messages:
        if msg.sender not in members_map:
            members_map[msg.sender] = {
                "platformId": msg.sender,
                "accountName": msg.account_name,
            }

    members = list(members_map.values())

    chatlab_messages = []
    for msg in session.messages:
        chatlab_messages.append({
            "sender": msg.sender,
            "accountName": msg.account_name,
            "timestamp": msg.timestamp,
            "type": msg.msg_type,
            "content": msg.content,
        })

    return {
        "chatlab": {
            "version": "0.0.1",
            "exportedAt": int(time.time()),
            "generator": "chatlab-exporter",
            "description": f"Exported from OpenClaw session: {session.name}",
        },
        "meta": {
            "name": session.name,
            "platform": "openclaw",
            "type": "private",
        },
        "members": members,
        "messages": chatlab_messages,
    }


def export_session(session: ParsedSession, output_path: Path) -> None:
    """Export a single session to a ChatLab JSON file."""
    doc = build_chatlab_doc(session)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def export_sessions(sessions: list[ParsedSession], output_dir: Path, suffix: str = "") -> list[Path]:
    """Export multiple sessions to individual files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    import json
    written = []
    for session in sessions:
        safe_name = session.name.replace("/", "_").replace("\\", "_")
        out_path = output_dir / f"{safe_name}{suffix}.json"
        doc = build_chatlab_doc(session)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        written.append(out_path)
    return written
