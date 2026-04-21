"""CLI entry point for session-import."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .importer import import_all


def main():
    parser = argparse.ArgumentParser(description="Import OpenClaw sessions into SQLite")
    parser.add_argument("--db", "-d", type=Path, required=True, help="Output SQLite database path")
    parser.add_argument("--agent", "-a", action="append", help="Agent name (can repeat)")
    parser.add_argument("--all", "-A", action="store_true", help="Import all agents (main, lingxi, test, cursor, codex)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.all:
        agents = ["main", "lingxi", "test", "cursor", "codex"]
    elif args.agent:
        agents = args.agent
    else:
        print("Error: specify --all or --agent", file=sys.stderr)
        sys.exit(1)

    print(f"Importing into {args.db} ...")
    result = import_all(agents, args.db, verbose=args.verbose)
    print(f"Done: {result['sessions']} sessions, {result['messages']} messages imported")


if __name__ == "__main__":
    main()
