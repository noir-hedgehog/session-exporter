#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from chatlab_exporter.parser import iter_session_files, parse_session_file
from chatlab_exporter.formatter import build_chatlab_doc
import json

# Test single file
path = Path('/Users/uriah/.openclaw/agents/lingxi/sessions/0e1be56d-5cb1-409b-bb6c-6f1d01dbc055.jsonl')
session = parse_session_file(path)
print(f'Single file: {len(session.messages)} messages extracted')
for m in session.messages:
    print(f'  [{m.sender}] {repr(m.content[:80])}')

# Export to chatlab format
doc = build_chatlab_doc(session)
out = Path('/tmp/chatlab-test.json')
with out.open('w', encoding='utf-8') as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f'\nExported to {out}')
print(f'File size: {out.stat().st_size} bytes')
