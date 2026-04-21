# chatlab-exporter

Export OpenClaw agent conversation sessions to [ChatLab](https://github.com/hellodigua/ChatLab) standard format for analysis.

## Installation

```bash
pip install -e .
```

## Usage

### Single session export

```bash
python -m chatlab_exporter --input ~/.openclaw/agents/lingxi/sessions/de4a03e2.jsonl --output export.json
```

### Batch export all sessions for an agent

```bash
python -m chatlab_exporter --agent lingxi --output ./exports/
```

### With custom name

```bash
python -m chatlab_exporter --input session.jsonl --name "My Chat" --output export.json
```

## Output format

Exports to ChatLab standard JSON format:

```json
{
  "chatlab": { "version": "0.0.1", "exportedAt": 1703001600, "generator": "chatlab-exporter" },
  "meta": { "name": "Session Name", "platform": "openclaw", "type": "private" },
  "members": [
    { "platformId": "user", "accountName": "User" },
    { "platformId": "hecate", "accountName": "Hekate" }
  ],
  "messages": [
    { "sender": "user", "accountName": "User", "timestamp": 1703001600, "type": 0, "content": "Hello" }
  ]
}
```

## Message type mapping

| OpenClaw content type | ChatLab message type |
|-----------------------|---------------------|
| `text`                | 0 (TEXT)            |
| `image`               | 1 (IMAGE)           |
| `thinking`            | skipped             |
| `tool_result`         | skipped (extracted into parent text) |

## Supported agents

- `main`, `test`, `lingxi`, `cursor`, `codex`

Defaults to reading session files from `~/.openclaw/agents/{agent}/sessions/`.
