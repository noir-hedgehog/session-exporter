"""Parse OpenClaw JSONL session files into message lists."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class ParsedMessage:
    sender: str          # "user" or "hecate"
    account_name: str    # display name
    timestamp: int        # Unix seconds
    content: str
    msg_type: int = 0    # 0=TEXT, 1=IMAGE, 80=SYSTEM


@dataclass
class ParsedSession:
    name: str
    messages: list[ParsedMessage] = field(default_factory=list)
    first_timestamp: int | None = None


def _extract_text(content_block: dict) -> str | None:
    """Recursively extract text from a content block."""
    if not isinstance(content_block, dict):
        return None

    block_type = content_block.get("type", "")

    if block_type == "text":
        return content_block.get("text", "") or None

    if block_type in ("image", "image_url"):
        return "[Image]"

    if block_type in ("thinking", "tool_use", "tool_result", "tool_call", "toolCall"):
        return None

    # Fallback: if it has a text field
    if "text" in content_block:
        val = content_block["text"]
        if isinstance(val, str) and val.strip():
            return val

    return None


def _parse_content(content: list[dict]) -> str:
    """Extract full text from a message content list, skipping thinking/tool blocks."""
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        text = _extract_text(block)
        if text:
            parts.append(text)

    return "\n".join(parts).strip()


def _iso_to_unix(ts: str) -> int:
    """Convert ISO8601 timestamp (with or without timezone) to Unix seconds."""
    ts = ts.strip()
    # Handle 'Z' suffix
    ts = ts.replace("Z", "+00:00")
    # Normalize spaces
    ts = re.sub(r"\s+", " ", ts)
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # Try without timezone
        dt = datetime.fromisoformat(ts.replace("+00:00", ""))
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def parse_session_file(path: Path | str, name: str | None = None) -> ParsedSession:
    """Parse a single OpenClaw JSONL session file."""
    path = Path(path)
    session_name = name or path.stem

    messages: list[ParsedMessage] = []
    first_ts: int | None = None

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")
            if entry_type == "session":
                continue

            if entry_type == "message":
                msg_data = entry.get("message", {})
                role = msg_data.get("role", "")
                if role not in ("user", "assistant"):
                    continue

                content = msg_data.get("content", [])
                text = _parse_content(content)
                if not text:
                    continue

                ts_str = entry.get("timestamp", "")
                try:
                    ts = _iso_to_unix(ts_str)
                except Exception:
                    ts = 0

                if first_ts is None and ts > 0:
                    first_ts = ts

                sender = "user" if role == "user" else "hecate"
                account_name = "User" if role == "user" else "Hekate"

                messages.append(ParsedMessage(
                    sender=sender,
                    account_name=account_name,
                    timestamp=ts,
                    content=text,
                    msg_type=0,
                ))

    return ParsedSession(name=session_name, messages=messages, first_timestamp=first_ts)


def iter_session_files(agent: str, sessions_dir: Path | None = None) -> Iterator[Path]:
    """Iterate over all .jsonl session files for an agent."""
    if sessions_dir is None:
        sessions_dir = Path.home() / ".openclaw" / "agents" / agent / "sessions"

    if not sessions_dir.exists():
        return

    for p in sorted(sessions_dir.iterdir()):
        if p.suffix == ".jsonl" and not p.name.endswith(".deleted"):
            yield p
