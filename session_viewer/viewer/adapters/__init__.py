"""
Multi-agent framework session adapter.

Each adapter knows how to:
- List session files for a given base directory
- Parse a session file into a list of Message objects
- Detect which framework a session belongs to

Registry
--------
ADAPTERS = {
    "openclaw": OpenClawAdapter,
    "hermes": HermesAdapter,
}

detect(path_or_content) -> Adapter
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List

DB_PATH_ENV = "OPENCLAW_SESSION_DB"


@dataclass
class Message:
    role: str          # "user" | "assistant" | "system"
    content: str
    timestamp: str      # ISO string
    type: str = "text"  # "text" | "thinking" | "tool_call" | "tool_result" | "image"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "type": self.type,
        }


@dataclass
class SessionInfo:
    id: str
    agent: str
    label: str
    first_ts: int      # unix timestamp
    last_ts: int
    message_count: int
    adapter: str = "openclaw"
    path: str = ""     # absolute path to session file


class BaseAdapter(ABC):
    name: str = "base"
    session_ext: str = ".jsonl"

    @abstractmethod
    def iter_sessions(self, base_dir: str) -> Iterator[SessionInfo]:
        """Scan base_dir for session files and yield SessionInfo."""
        ...

    @abstractmethod
    def parse_session(self, path: str) -> List[Message]:
        """Parse a single session file into Messages."""
        ...

    def guess_agent(self, path: str) -> str:
        """Derive agent name from path. Override if framework has metadata."""
        parts = Path(path).parts
        if "agents" in parts:
            idx = parts.index("agents")
            return parts[idx + 1] if idx + 1 < len(parts) else "unknown"
        return "unknown"


class OpenClawAdapter(BaseAdapter):
    """
    OpenClaw JSONL format.

    Each line: {"type": "session"|"message", "timestamp": "...", "message": {...}}
    Session lines: meta only
    Message lines: {"role": "user"|"assistant"|"system", "content": [...blocks...]}

    Content blocks: {"type": "text"|"thinking"|"tool_call"|"tool_result"|"image", "text": "..."}
    """

    name = "openclaw"
    session_ext = ".jsonl"

    def iter_sessions(self, base_dir: str) -> Iterator[SessionInfo]:
        base = Path(base_dir)
        if not base.exists():
            return

        # Support both flat and nested agent dir layouts
        for jsonl_path in base.rglob("*.jsonl"):
            try:
                si = self._parse_session_meta(jsonl_path)
                if si:
                    yield si
            except Exception:
                continue

    def _parse_session_meta(self, path: Path) -> SessionInfo | None:
        """Quick scan: read first+last lines to get session metadata."""
        try:
            lines = path.read_text().strip().split("\n")
            if not lines:
                return None

            first = json.loads(lines[0])
            last = json.loads(lines[-1])

            if first.get("type") == "session":
                meta = first.get("session", {})
            else:
                meta = first.get("message", {})

            sid = meta.get("id", path.stem)
            # Derive agent: if path is .../agents/{agent}/... use {agent}, else "openclaw"
            parts = path.parts
            agent = meta.get("agent")
            if not agent:
                if "agents" in parts:
                    idx = parts.index("agents")
                    candidate = parts[idx + 1] if idx + 1 < len(parts) else None
                    # "sessions" is the flat store dir, not an agent
                    agent = candidate if candidate and candidate != "sessions" else "openclaw"
                else:
                    agent = "openclaw" 
            label = meta.get("label", sid)
            first_ts = self._ts_to_unix(first.get("timestamp", ""))
            last_ts = self._ts_to_unix(last.get("timestamp", ""))

            return SessionInfo(
                id=sid,
                agent=agent,
                label=label,
                first_ts=first_ts,
                last_ts=last_ts,
                message_count=len(lines),
                adapter=self.name,
                path=str(path),
            )
        except Exception:
            return None

    def parse_session(self, path: str) -> List[Message]:
        messages = []
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("type") == "session":
                continue  # meta-only line

            msg_data = obj.get("message", {})
            role = msg_data.get("role", "unknown")
            blocks = msg_data.get("content", [])

            if not blocks:
                continue

            for block in blocks:
                btype = block.get("type", "text")
                text = block.get("text", "") or ""
                ts = obj.get("timestamp", "")

                if btype == "text" and text.strip():
                    messages.append(Message(role=role, content=text, timestamp=ts, type="text"))
                elif btype in ("thinking", "tool_call", "tool_result", "image"):
                    if text.strip():
                        messages.append(Message(role=role, content=text, timestamp=ts, type=btype))

        return messages

    def _ts_to_unix(self, ts: str) -> int:
        from datetime import datetime, timezone
        try:
            return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
        except Exception:
            return 0


class HermesAdapter(BaseAdapter):
    """
    Hermes Agent session format.

    Hermes stores sessions as JSON files (not JSONL) with a tasks array.
    Each task has: id, status, messages[].role + messages[].content.

    Path convention: ~/.hermes/sessions/YYYY-MM/ or ~/.hermes/runs/
    """

    name = "hermes"
    session_ext = ".json"

    def iter_sessions(self, base_dir: str) -> Iterator[SessionInfo]:
        base = Path(base_dir)
        if not base.exists():
            return

        for json_path in base.rglob("*.json"):
            # Skip non-session files
            if any(k in json_path.name.lower() for k in ["skill", "model", "config", "checkpoint"]):
                continue
            try:
                si = self._parse_hermes_session(json_path)
                if si:
                    yield si
            except Exception:
                continue

    def _parse_hermes_session(self, path: Path) -> SessionInfo | None:
        try:
            data = json.loads(path.read_text())
            tasks = data if isinstance(data, list) else data.get("tasks", [data])

            if not tasks:
                return None

            first_task = tasks[0]
            last_task = tasks[-1]

            sid = path.stem
            label = first_task.get("id", sid)[:60]
            agent = "hermes"
            first_ts = self._parse_hermes_ts(first_task.get("created_at", ""))
            last_ts = self._parse_hermes_ts(last_task.get("finished_at", last_task.get("created_at", "")))
            msg_count = sum(len(t.get("messages", [])) for t in tasks)

            return SessionInfo(
                id=sid,
                agent=agent,
                label=label,
                first_ts=first_ts,
                last_ts=last_ts,
                message_count=msg_count,
                adapter=self.name,
                path=str(path),
            )
        except Exception:
            return None

    def parse_session(self, path: str) -> List[Message]:
        messages = []
        try:
            data = json.loads(open(path).read())
            tasks = data if isinstance(data, list) else data.get("tasks", [data])

            for task in tasks:
                for msg in task.get("messages", []):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    ts = self._hermes_to_iso(msg.get("timestamp", ""))
                    if content and isinstance(content, str):
                        messages.append(Message(role=role, content=content, timestamp=ts))
        except Exception:
            pass
        return messages

    def _parse_hermes_ts(self, ts: str) -> int:
        from datetime import datetime, timezone
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return int(datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T")).timestamp())
            except Exception:
                continue
        return 0

    def _hermes_to_iso(self, ts: str) -> str:
        if not ts:
            return ""
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(ts.replace("Z", "").replace("T", " ").replace("/", "-"), fmt.replace("Z", "").replace("T", " "))
                return dt.isoformat() + "Z"
            except Exception:
                continue
        return ts


# Registry
ADAPTERS: dict[str, type[BaseAdapter]] = {
    "openclaw": OpenClawAdapter,
    "hermes": HermesAdapter,
}


def get_default_base_dir() -> str:
    """Return the default OpenClaw sessions directory."""
    return str(Path.home() / ".openclaw" / "agents")


def detect_adapter(path: str) -> str:
    """Auto-detect which adapter to use based on path or file content."""
    p = Path(path)
    if p.suffix == ".json":
        return "hermes"
    if p.suffix == ".jsonl" or p.is_dir():
        # Peek at first line
        if p.is_file():
            try:
                first_line = open(path).readline()
                obj = json.loads(first_line)
                if obj.get("type") == "session":
                    return "openclaw"
            except Exception:
                pass
    return "openclaw"
