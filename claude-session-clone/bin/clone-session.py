#!/usr/bin/env python3
"""
claude-session-clone: Full clone of a Claude Code session into another session.

Usage:
    clone-session.py <source_session_id> [target_session_id]

If target_session_id is omitted, prints the source session location and stats
(the SKILL.md handles loading it into the current context).

If target_session_id is provided, copies the full session data (transcript,
subagents, tool-results) into the target session location.
"""

import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"


def encode_project_path(project_path: str) -> str:
    """Convert /Users/dzineer/Foo/Bar to -Users-dzineer-Foo-Bar"""
    return project_path.replace("/", "-")


def find_session(session_id: str) -> tuple[Path | None, Path | None, str | None]:
    """
    Find a session's .jsonl file and optional directory across all projects.
    Returns (jsonl_path, dir_path, project_encoded) or (None, None, None).
    """
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl = project_dir / f"{session_id}.jsonl"
        if jsonl.exists():
            session_dir = project_dir / session_id
            return (
                jsonl,
                session_dir if session_dir.is_dir() else None,
                project_dir.name,
            )
    return None, None, None


def get_session_stats(jsonl_path: Path, session_dir: Path | None) -> dict:
    """Get stats about a session."""
    stats = {
        "jsonl_size": jsonl_path.stat().st_size,
        "jsonl_lines": 0,
        "subagent_count": 0,
        "tool_result_count": 0,
        "total_size": jsonl_path.stat().st_size,
    }

    # Count lines
    with open(jsonl_path, "r") as f:
        for _ in f:
            stats["jsonl_lines"] += 1

    if session_dir:
        subagents_dir = session_dir / "subagents"
        tool_results_dir = session_dir / "tool-results"

        if subagents_dir.is_dir():
            for f in subagents_dir.iterdir():
                stats["subagent_count"] += 1
                stats["total_size"] += f.stat().st_size

        if tool_results_dir.is_dir():
            for f in tool_results_dir.iterdir():
                stats["tool_result_count"] += 1
                stats["total_size"] += f.stat().st_size

    return stats


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def get_session_project_path(jsonl_path: Path) -> str | None:
    """Extract the original project path from the first user message in a session."""
    with open(jsonl_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("type") == "user" and entry.get("cwd"):
                    return entry["cwd"]
            except json.JSONDecodeError:
                continue
    return None


def clone_session(
    source_jsonl: Path,
    source_dir: Path | None,
    source_project: str,
    target_id: str,
    target_project_dir: Path | None = None,
) -> dict:
    """
    Clone a session's full data to a new session ID.

    If target_project_dir is None, clones into the same project directory as the source.
    """
    if target_project_dir is None:
        target_project_dir = source_jsonl.parent

    target_jsonl = target_project_dir / f"{target_id}.jsonl"
    target_dir = target_project_dir / target_id

    result = {
        "target_jsonl": str(target_jsonl),
        "target_dir": None,
        "jsonl_lines_copied": 0,
        "subagents_copied": 0,
        "tool_results_copied": 0,
        "total_bytes_copied": 0,
    }

    # 1. Copy and rewrite the main .jsonl — update sessionId references
    with open(source_jsonl, "r") as src, open(target_jsonl, "w") as dst:
        for line in src:
            try:
                entry = json.loads(line)
                # Update sessionId if present
                if "sessionId" in entry:
                    entry["sessionId"] = target_id
                # Update uuid to avoid collisions (generate new ones)
                if "uuid" in entry:
                    entry["uuid"] = str(uuid.uuid4())
                dst.write(json.dumps(entry, separators=(",", ":")) + "\n")
                result["jsonl_lines_copied"] += 1
            except json.JSONDecodeError:
                # Preserve malformed lines as-is
                dst.write(line)
                result["jsonl_lines_copied"] += 1

    result["total_bytes_copied"] += target_jsonl.stat().st_size

    # 2. Copy subagents and tool-results directories if they exist
    if source_dir and source_dir.is_dir():
        subagents_src = source_dir / "subagents"
        tool_results_src = source_dir / "tool-results"

        if subagents_src.is_dir() or tool_results_src.is_dir():
            target_dir.mkdir(exist_ok=True)
            result["target_dir"] = str(target_dir)

        if subagents_src.is_dir():
            target_subagents = target_dir / "subagents"
            shutil.copytree(subagents_src, target_subagents, dirs_exist_ok=True)
            for f in target_subagents.iterdir():
                result["subagents_copied"] += 1
                result["total_bytes_copied"] += f.stat().st_size

        if tool_results_src.is_dir():
            target_tool_results = target_dir / "tool-results"
            shutil.copytree(tool_results_src, target_tool_results, dirs_exist_ok=True)
            for f in target_tool_results.iterdir():
                result["tool_results_copied"] += 1
                result["total_bytes_copied"] += f.stat().st_size

    # 3. Add a clone marker as the last entry in the new transcript
    clone_marker = {
        "type": "user",
        "isMeta": True,
        "isSidechain": False,
        "userType": "external",
        "sessionId": target_id,
        "message": {
            "role": "user",
            "content": (
                f"<system-reminder>\n"
                f"This session was cloned from session {source_jsonl.stem} "
                f"on {datetime.now(timezone.utc).isoformat()}.\n"
                f"All previous context, messages, and tool results have been preserved.\n"
                f"</system-reminder>"
            ),
        },
        "uuid": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(target_jsonl, "a") as dst:
        dst.write(json.dumps(clone_marker, separators=(",", ":")) + "\n")

    return result


def list_sessions(project_path: str | None = None) -> list[dict]:
    """List recent sessions, optionally filtered to a project."""
    sessions = []
    if not HISTORY_FILE.exists():
        return sessions

    with open(HISTORY_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if project_path and entry.get("project") != project_path:
                    continue
                sessions.append(entry)
            except json.JSONDecodeError:
                continue

    # Deduplicate by sessionId, keep latest
    seen = {}
    for s in sessions:
        sid = s.get("sessionId")
        if sid:
            seen[sid] = s

    # Sort by timestamp descending
    result = sorted(seen.values(), key=lambda x: x.get("timestamp", 0), reverse=True)
    return result[:20]


def main():
    if len(sys.argv) < 2:
        # List mode
        print("No session ID provided. Recent sessions:\n")
        sessions = list_sessions()
        for s in sessions[:15]:
            ts = s.get("timestamp", 0)
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else "unknown"
            display = s.get("display", "")[:80]
            sid = s.get("sessionId", "unknown")
            project = s.get("project", "unknown")
            print(f"  {sid}")
            print(f"    Time: {dt}  Project: {os.path.basename(project)}")
            print(f"    Last: {display}")
            print()
        sys.exit(0)

    source_id = sys.argv[1]
    target_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Find source
    source_jsonl, source_dir, source_project = find_session(source_id)
    if not source_jsonl:
        print(f"ERROR: Session {source_id} not found in any project under {PROJECTS_DIR}")
        sys.exit(1)

    stats = get_session_stats(source_jsonl, source_dir)
    print(f"Source session: {source_id}")
    print(f"  Location: {source_jsonl}")
    print(f"  Transcript: {stats['jsonl_lines']:,} lines, {format_size(stats['jsonl_size'])}")
    print(f"  Subagents: {stats['subagent_count']} files")
    print(f"  Tool results: {stats['tool_result_count']} files")
    print(f"  Total size: {format_size(stats['total_size'])}")
    print()

    if target_id is None:
        # Info-only mode — the SKILL.md will handle context injection
        project_path = get_session_project_path(source_jsonl)
        print(f"  Original project: {project_path or 'unknown'}")
        print(f"\nTo clone, run: clone-session.py {source_id} <target_session_id>")
        sys.exit(0)

    # Check if target already exists — if so, clone INTO its project directory
    target_jsonl_check, target_dir_check, target_project = find_session(target_id)
    if target_jsonl_check:
        target_project_dir = target_jsonl_check.parent
        print(f"Target session {target_id} exists at: {target_jsonl_check}")
        print(f"  Cloning INTO target's project directory: {target_project_dir}")
        print(f"  Existing target transcript will be REPLACED with source data.")
        print()

        # Remove existing target files so we can write fresh
        target_jsonl_check.unlink()
        if target_dir_check and target_dir_check.is_dir():
            shutil.rmtree(target_dir_check)
    else:
        # Target doesn't exist — clone into source's project directory
        target_project_dir = source_jsonl.parent

    # Clone
    print(f"Cloning into target session: {target_id}")
    print(f"  Target project: {target_project_dir}")
    print("  Copying transcript...")

    result = clone_session(
        source_jsonl, source_dir, source_project, target_id,
        target_project_dir=target_project_dir,
    )

    print(f"\nClone complete!")
    print(f"  Target transcript: {result['target_jsonl']}")
    if result["target_dir"]:
        print(f"  Target directory: {result['target_dir']}")
    print(f"  Lines copied: {result['jsonl_lines_copied']:,}")
    print(f"  Subagents copied: {result['subagents_copied']}")
    print(f"  Tool results copied: {result['tool_results_copied']}")
    print(f"  Total bytes: {format_size(result['total_bytes_copied'])}")


if __name__ == "__main__":
    main()
