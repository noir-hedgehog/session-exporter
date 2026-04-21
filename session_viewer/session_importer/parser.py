"""Parse OpenClaw JSONL session files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class ParsedMessage:
    id: str
    session_id: str
    role: str          # user / assistant / system
    sender: str        # user / hecate / ...
    account_name: str
    timestamp: int     # Unix seconds
    type: int = 0      # 0=TEXT, 1=IMAGE, 80=SYSTEM
    content: str = ""  # extracted text
    thinking: str = "" # thinking content (if any)
    raw_blocks: list = field(default_factory=list)


@dataclass
class ParsedSession:
    id: str
    agent: str
    label: str
    first_ts: int
    last_ts: int
    messages: list[ParsedMessage] = field(default_factory=list)


def _iso_to_unix(ts: str) -> int:
    ts = ts.strip().replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(ts).timestamp())
    except ValueError:
        return int(datetime.fromisoformat(ts.replace("+00:00", "")).replace(tzinfo=timezone.utc).timestamp())


def _extract_blocks(content: list) -> tuple[str, str]:
    """Extract text and thinking from content blocks. Returns (text, thinking)."""
    text_parts = []
    thinking_parts = []

    for block in content:
        if not isinstance(block, dict):
            continue
        t = block.get("type", "")
        if t == "text":
            txt = block.get("text", "").strip()
            if txt:
                text_parts.append(txt)
        elif t == "thinking":
            th = block.get("thinking", "").strip()
            if th:
                thinking_parts.append(th)
        elif t == "image":
            text_parts.append("[Image]")
        # tool_call, tool_result, toolCall → skip for now

    return "\n".join(text_parts), "\n".join(thinking_parts)


def parse_message(entry: dict, session_id: str) -> ParsedMessage | None:
    msg_data = entry.get("message", {})
    role = msg_data.get("role", "")
    if role not in ("user", "assistant", "system"):
        return None

    content = msg_data.get("content", [])
    text, thinking = _extract_blocks(content)

    ts_str = entry.get("timestamp", "0")
    try:
        ts = _iso_to_unix(ts_str)
    except Exception:
        ts = 0

    sender_map = {"user": "user", "assistant": "hecate", "system": "system"}
    name_map = {"user": "User", "assistant": "Hekate", "system": "System"}

    return ParsedMessage(
        id=entry.get("id", ""),
        session_id=session_id,
        role=role,
        sender=sender_map.get(role, role),
        account_name=name_map.get(role, role),
        timestamp=ts,
        type=0,
        content=text,
        thinking=thinking,
        raw_blocks=content,
    )


def parse_session_file(path: Path, agent: str) -> ParsedSession | None:
    session_id = path.stem
    messages: list[ParsedMessage] = []
    first_ts = 0
    last_ts = 0
    label = ""

    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get("type") == "session":
                    session_id = entry.get("id", session_id)
                    label = entry.get("label", "")
                    continue

                if entry.get("type") == "message":
                    msg = parse_message(entry, session_id)
                    if msg:
                        if msg.content or msg.thinking:
                            messages.append(msg)
                            if msg.timestamp:
                                if not first_ts or msg.timestamp < first_ts:
                                    first_ts = msg.timestamp
                                if msg.timestamp > last_ts:
                                    last_ts = msg.timestamp
    except Exception:
        return None

    if not messages:
        return None

    return ParsedSession(
        id=session_id,
        agent=agent,
        label=label or session_id,
        first_ts=first_ts,
        last_ts=last_ts,
        messages=messages,
    )


def iter_session_files(agent: str) -> Iterator[Path]:
    base = Path.home() / ".openclaw" / "agents" / agent / "sessions"
    if not base.exists():
        return
    for p in sorted(base.iterdir()):
        if p.suffix == ".jsonl" and not p.name.endswith(".deleted"):
            yield p
