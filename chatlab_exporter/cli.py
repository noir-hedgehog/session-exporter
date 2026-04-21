"""CLI entry point for chatlab-exporter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import iter_session_files, parse_session_file
from .formatter import export_session, export_sessions


def main():
    parser = argparse.ArgumentParser(
        description="Export OpenClaw agent sessions to ChatLab format"
    )
    parser.add_argument(
        "--input", "-i", type=Path,
        help="Path to a single .jsonl session file (or directory of sessions)"
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output path (.json file or directory for batch)"
    )
    parser.add_argument(
        "--agent", "-a",
        help="Agent name (main, lingxi, test, etc.) when reading from default sessions dir"
    )
    parser.add_argument(
        "--name", "-n",
        help="Override session/conversation name"
    )
    parser.add_argument(
        "--batch", "-b", action="store_true",
        help="Force batch mode (export all sessions from --input directory)"
    )

    args = parser.parse_args()

    # Resolve input path
    if args.input:
        input_path = Path(args.input)
    elif args.agent:
        input_path = Path.home() / ".openclaw" / "agents" / args.agent / "sessions"
    else:
        print("Error: must specify --input or --agent", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)

    # Determine output
    if not args.output:
        print("Error: must specify --output", file=sys.stderr)
        sys.exit(1)

    # Single file mode
    if input_path.is_file() and not args.batch:
        session = parse_session_file(input_path, name=args.name)
        export_session(session, args.output)
        print(f"Exported: {args.output}")
        return

    # Batch mode
    if input_path.is_dir():
        session_files = list(input_path.glob("*.jsonl"))
    elif args.agent:
        session_files = list(iter_session_files(args.agent))
    else:
        print("Error: --input must be a file or directory", file=sys.stderr)
        sys.exit(1)

    if not session_files:
        print("No session files found.", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output
    if output_dir.suffix and "." in str(output_dir):
        # Has extension — assume single file but multiple inputs given
        print("Multiple inputs but single output path — using batch mode to directory", file=sys.stderr)
        output_dir = output_dir.parent / output_dir.stem

    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for sf in session_files:
        name = args.name or sf.stem
        session = parse_session_file(sf, name=name)
        if not session.messages:
            continue
        safe_name = sf.stem.replace("/", "_").replace("\\", "_")
        out_path = output_dir / f"{safe_name}.json"
        import json
        from .formatter import build_chatlab_doc
        doc = build_chatlab_doc(session)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        written.append(out_path)
        print(f"  ✓ {sf.name} → {out_path.name} ({len(session.messages)} messages)")

    print(f"\nDone. Exported {len(written)} sessions to {output_dir}")


if __name__ == "__main__":
    main()
