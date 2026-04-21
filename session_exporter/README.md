# session-exporter

[English](README.md) | [中文](README_CN.md)

Export [OpenClaw](https://github.com/openclaw/openclaw) agent conversation sessions to [ChatLab](https://github.com/hellodigua/ChatLab) standard format for analysis.

![](https://img.shields.io/badge/license-MIT-blue.svg)
![](https://img.shields.io/badge/python-3.10+-green.svg)

## Overview

OpenClaw stores conversation sessions as JSONL files, but they're not easy to analyze at scale. This tool converts them to [ChatLab's standardized format](https://chatlab.fun/standard/chatlab-format.html), so you can use ChatLab's SQL engine and AI agents to explore patterns, ask questions, and extract insights from your conversation history — all on your local machine.

## Features

- **Parse OpenClaw JSONL sessions** — handles nested content blocks, skips thinking/tool blocks
- **ChatLab standard output** — produces compliant JSON/JSONL for direct import
- **Batch export** — export all sessions for an agent in one command
- **Zero dependencies** — pure Python, no external packages required

## Installation

```bash
git clone git@github.com:noir-hedgehog/session-exporter.git
cd session-exporter
pip install -e .
```

## Quick Start

### Single session export

```bash
python -m chatlab_exporter \
  --input ~/.openclaw/agents/lingxi/sessions/abc123.jsonl \
  --output export.json
```

### Batch export all sessions for an agent

```bash
python -m chatlab_exporter \
  --agent lingxi \
  --output ./exports/
```

### With a custom conversation name

```bash
python -m chatlab_exporter \
  --input session.jsonl \
  --name "My Chat" \
  --output export.json
```

## Output Format

Exports to [ChatLab Standard Format](https://chatlab.fun/standard/chatlab-format.html):

```json
{
  "chatlab": {
    "version": "0.0.1",
    "exportedAt": 1703001600,
    "generator": "chatlab-exporter"
  },
  "meta": {
    "name": "session-name",
    "platform": "openclaw",
    "type": "private"
  },
  "members": [
    { "platformId": "user", "accountName": "User" },
    { "platformId": "hecate", "accountName": "Hekate" }
  ],
  "messages": [
    {
      "sender": "user",
      "accountName": "User",
      "timestamp": 1703001600,
      "type": 0,
      "content": "Hello!"
    }
  ]
}
```

## Message Type Mapping

| Content Type   | ChatLab Type |
|----------------|--------------|
| `text`         | 0 (TEXT)     |
| `image`        | 1 (IMAGE)    |
| `thinking`     | _skipped_    |
| `tool_call`    | _skipped_    |
| `tool_result`  | _skipped_    |

> **Note:** `thinking`, `tool_call`, and `tool_result` blocks are skipped to produce clean conversation text for ChatLab analysis. Thinking content is internal reasoning; tool calls are actions, not conversation content.

## Project Structure

```
session-exporter/
├── chatlab_exporter/
│   ├── __init__.py
│   ├── parser.py       # Parse OpenClaw JSONL session files
│   ├── formatter.py    # Convert to ChatLab format
│   └── cli.py          # CLI entry point
├── pyproject.toml
├── README.md
└── test_cli.py
```

## ChatLab Integration

1. Export your sessions: `python -m chatlab_exporter --agent lingxi --output ./exports/`
2. Open ChatLab → Import → Select the exported `.json` files
3. Use ChatLab's SQL Lab or AI Agent to analyze patterns

## Related

- [ChatLab](https://github.com/hellodigua/ChatLab) — Local AI-powered chat history analysis
- [OpenClaw](https://github.com/openclaw/openclaw) — Cross-platform AI assistant framework
