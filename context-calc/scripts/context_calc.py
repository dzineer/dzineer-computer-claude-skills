#!/usr/bin/env python3
"""
Claude Code Context Calculator
Finds the JSONL session file for a project and reports context size in tokens.
No external dependencies — pure Python standard library.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
CACHE_DIR = CLAUDE_DIR / "context-cache"

# Claude model context window sizes
CONTEXT_WINDOWS = {
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-sonnet-4-5-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-haiku": 200_000,
    "default": 200_000,
}


def encode_project_path(project_path):
    """Encode a project path the way Claude Code does.
    Claude Code replaces /, _ and . with - in directory names."""
    abs_path = os.path.abspath(project_path)
    return abs_path.replace("/", "-").replace(".", "-")


def find_project_dir(project_path):
    """Find the Claude projects directory for a given project path.
    Uses exact match first, then fuzzy match to handle _ vs - encoding."""
    abs_path = os.path.abspath(project_path)

    # Try exact encoding (replace / with -)
    encoded = abs_path.replace("/", "-")
    project_dir = PROJECTS_DIR / encoded
    if project_dir.exists():
        return project_dir

    # Try encoding that also replaces _ and . with - (Claude Code's actual behavior)
    encoded_fuzzy = abs_path.replace("/", "-").replace("_", "-").replace(".", "-")
    project_dir = PROJECTS_DIR / encoded_fuzzy
    if project_dir.exists():
        return project_dir

    # Fuzzy search: normalize both sides and compare
    if PROJECTS_DIR.exists():
        normalized_target = abs_path.replace("/", "-").replace("_", "-").replace(".", "-").lower()
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir():
                normalized_dir = d.name.replace("_", "-").replace(".", "-").lower()
                if normalized_dir == normalized_target:
                    return d

    return None


def find_sessions(project_dir):
    """Find all JSONL session files in a project directory."""
    sessions = []
    for f in project_dir.glob("*.jsonl"):
        if f.is_file():
            stat = f.stat()
            sessions.append({
                "path": f,
                "session_id": f.stem,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            })
    sessions.sort(key=lambda s: s["modified"], reverse=True)
    return sessions


def find_active_session(project_dir):
    """Find the most recently modified session (likely the active one)."""
    sessions = find_sessions(project_dir)
    if not sessions:
        return None
    return sessions[0]


def parse_session(jsonl_path, detail=False):
    """Parse a session JSONL file and extract token usage stats."""
    messages = []
    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    model = None
    session_id = None
    first_timestamp = None
    last_timestamp = None
    user_messages = 0
    assistant_messages = 0
    tool_uses = 0

    with open(jsonl_path, "r", errors="replace") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not session_id:
                session_id = record.get("sessionId")

            ts_str = record.get("timestamp")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if first_timestamp is None:
                        first_timestamp = ts
                    last_timestamp = ts
                except (ValueError, TypeError):
                    pass

            msg_type = record.get("type")
            msg = record.get("message", {})

            if msg_type == "user":
                user_messages += 1
            elif msg_type == "assistant":
                assistant_messages += 1

                if not model:
                    model = msg.get("model")

                usage = msg.get("usage", {})
                if usage:
                    inp = usage.get("input_tokens", 0)
                    out = usage.get("output_tokens", 0)
                    cc = usage.get("cache_creation_input_tokens", 0)
                    cr = usage.get("cache_read_input_tokens", 0)

                    total_input += inp
                    total_output += out
                    total_cache_create += cc
                    total_cache_read += cr

                    if detail:
                        messages.append({
                            "line": line_num + 1,
                            "type": msg_type,
                            "input_tokens": inp,
                            "cache_creation": cc,
                            "cache_read": cr,
                            "output_tokens": out,
                            "context_size": inp + cc + cr,
                        })

                # Count tool uses
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_uses += 1

    # Latest context size = last assistant message's input context
    # Also detect compaction events (>40% context drop between consecutive assistant messages)
    latest_context = 0
    prev_context = 0
    compactions = []
    peak_context = 0
    with open(jsonl_path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "assistant":
                usage = record.get("message", {}).get("usage", {})
                if usage:
                    latest_context = (
                        usage.get("input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )
                    if latest_context > peak_context:
                        peak_context = latest_context
                    if prev_context > 0 and latest_context < prev_context * 0.6:
                        compactions.append({
                            "before": prev_context,
                            "after": latest_context,
                            "drop_pct": round((1 - latest_context / prev_context) * 100, 1),
                        })
                    prev_context = latest_context

    # Model's maximum context window
    model_window = CONTEXT_WINDOWS.get(model or "", CONTEXT_WINDOWS["default"])
    # Check if user has a custom contextWindow in settings.json (compaction threshold)
    compaction_threshold = None
    settings_file = CLAUDE_DIR / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, "r") as sf:
                settings = json.load(sf)
            custom_window = settings.get("contextWindow")
            if custom_window and isinstance(custom_window, int) and 0 < custom_window < model_window:
                compaction_threshold = custom_window
        except (json.JSONDecodeError, OSError):
            pass
    # Use model window as the actual limit
    context_window = model_window
    remaining = max(0, context_window - latest_context)
    pct_used = (latest_context / context_window * 100) if context_window > 0 else 0

    duration = None
    if first_timestamp and last_timestamp:
        duration = last_timestamp - first_timestamp

    return {
        "session_id": session_id,
        "jsonl_path": str(jsonl_path),
        "file_size_bytes": os.path.getsize(jsonl_path),
        "model": model or "unknown",
        "context_window": context_window,
        "latest_context_tokens": latest_context,
        "remaining_tokens": remaining,
        "pct_used": round(pct_used, 1),
        "cumulative_input_tokens": total_input,
        "cumulative_cache_creation_tokens": total_cache_create,
        "cumulative_cache_read_tokens": total_cache_read,
        "cumulative_output_tokens": total_output,
        "total_messages": user_messages + assistant_messages,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "tool_uses": tool_uses,
        "first_message": first_timestamp.isoformat() if first_timestamp else None,
        "last_message": last_timestamp.isoformat() if last_timestamp else None,
        "duration": str(duration) if duration else None,
        "compactions": compactions,
        "compaction_threshold": compaction_threshold,
        "peak_context": peak_context,
        "detail": messages if detail else None,
    }


def format_tokens(n):
    """Format token count with commas and K/M suffix."""
    if n >= 1_000_000:
        return f"{n:,} ({n/1_000_000:.1f}M)"
    elif n >= 1_000:
        return f"{n:,} ({n/1_000:.1f}K)"
    return f"{n:,}"


def format_bytes(n):
    """Format byte count."""
    if n >= 1_048_576:
        return f"{n/1_048_576:.1f} MB"
    elif n >= 1_024:
        return f"{n/1_024:.1f} KB"
    return f"{n} bytes"


def progress_bar(pct, width=40):
    """Generate a text progress bar."""
    filled = int(width * pct / 100)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {pct:.1f}%"


def get_banner(text, font="block"):
    """Generate ASCII art banner using the ascii-banner skill."""
    banner_script = Path.home() / ".claude" / "skills" / "ascii-banner" / "scripts" / "banner.py"
    if not banner_script.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(banner_script), text, "--font", font],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.rstrip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def format_duration_friendly(duration_str):
    """Convert a duration string like '5 days, 18:31:52.641000' to friendly format."""
    if not duration_str:
        return "N/A"
    try:
        if "day" in duration_str:
            parts = duration_str.split(",")
            days_part = parts[0].strip()
            days = int(days_part.split()[0])
            if days == 1:
                return "~1 day"
            return f"~{days} days"
        else:
            # Just hours:minutes:seconds
            h, m, s = duration_str.split(":")
            h = int(h)
            if h > 0:
                return f"~{h} hours"
            return f"~{int(m)} minutes"
    except (ValueError, IndexError):
        return duration_str


def format_tokens_short(n):
    """Format token count with K/M suffix only (no commas)."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def print_table(rows):
    """Print rows as a Unicode box-drawing table.
    Each row is a (label, value) tuple."""
    # Calculate column widths
    col1_width = max(len(r[0]) for r in rows)
    col2_width = max(len(r[1]) for r in rows)

    # Box drawing
    top    = f"  \u250c\u2500{'\u2500' * col1_width}\u2500\u252c\u2500{'\u2500' * col2_width}\u2500\u2510"
    sep    = f"  \u251c\u2500{'\u2500' * col1_width}\u2500\u253c\u2500{'\u2500' * col2_width}\u2500\u2524"
    bottom = f"  \u2514\u2500{'\u2500' * col1_width}\u2500\u2534\u2500{'\u2500' * col2_width}\u2500\u2518"

    print(top)
    for i, (label, value) in enumerate(rows):
        print(f"  \u2502 {label:<{col1_width}} \u2502 {value:<{col2_width}} \u2502")
        if i < len(rows) - 1:
            print(sep)
    print(bottom)


def print_report(stats, ascii_mode=False):
    """Print a formatted report."""
    # Build cache description
    cumulative_total = (
        stats["cumulative_input_tokens"]
        + stats["cumulative_cache_creation_tokens"]
        + stats["cumulative_cache_read_tokens"]
        + stats["cumulative_output_tokens"]
    )
    cache_pct = (stats["cumulative_cache_read_tokens"] / cumulative_total * 100) if cumulative_total > 0 else 0
    if cache_pct > 50:
        total_desc = f"{format_tokens_short(cumulative_total)} tokens (mostly cache reads)"
    else:
        total_desc = f"{format_tokens_short(cumulative_total)} tokens"

    duration_friendly = format_duration_friendly(stats.get("duration"))

    compactions = stats.get("compactions", [])
    compaction_count = len(compactions)
    if compaction_count > 0:
        last_compaction = compactions[-1]
        compaction_desc = (
            f"{compaction_count}x (last: {format_tokens_short(last_compaction['before'])} "
            f"-> {format_tokens_short(last_compaction['after'])}, -{last_compaction['drop_pct']}%)"
        )
    else:
        compaction_desc = "None"

    rows = [
        ("Metric", "Value"),
        ("Model", stats["model"]),
        ("Current Context", f"{format_tokens_short(stats['latest_context_tokens'])} tokens"),
        ("Window Size", f"{format_tokens_short(stats['context_window'])} tokens"),
    ]
    ct = stats.get("compaction_threshold")
    if ct:
        rows.append(("Compaction At", f"{format_tokens_short(ct)} tokens (from settings.json)"))
    rows += [
        ("Remaining", f"{format_tokens_short(stats['remaining_tokens'])} tokens"),
        ("Usage", progress_bar(stats["pct_used"])),
        ("Peak Context", f"{format_tokens_short(stats['peak_context'])} tokens"),
        ("Compactions", compaction_desc),
        ("Messages", f"{stats['total_messages']} ({stats['user_messages']} user, {stats['assistant_messages']} assistant)"),
        ("Tool Uses", str(stats["tool_uses"])),
        ("Session Duration", duration_friendly),
        ("Total Processed", total_desc),
    ]

    # Use header row separately
    header = rows[0]
    data_rows = rows[1:]

    # Calculate column widths from all rows including header
    col1_width = max(len(r[0]) for r in rows)
    col2_width = max(len(r[1]) for r in rows)

    top    = f"  \u250c\u2500{'\u2500' * col1_width}\u2500\u252c\u2500{'\u2500' * col2_width}\u2500\u2510"
    hsep   = f"  \u251c\u2500{'\u2500' * col1_width}\u2500\u253c\u2500{'\u2500' * col2_width}\u2500\u2524"
    sep    = f"  \u251c\u2500{'\u2500' * col1_width}\u2500\u253c\u2500{'\u2500' * col2_width}\u2500\u2524"
    bottom = f"  \u2514\u2500{'\u2500' * col1_width}\u2500\u2534\u2500{'\u2500' * col2_width}\u2500\u2518"

    print(top)
    # Header
    print(f"  \u2502 {header[0]:<{col1_width}} \u2502 {header[1]:<{col2_width}} \u2502")
    print(hsep)
    # Data rows
    for i, (label, value) in enumerate(data_rows):
        print(f"  \u2502 {label:<{col1_width}} \u2502 {value:<{col2_width}} \u2502")
        if i < len(data_rows) - 1:
            print(sep)
    print(bottom)

    # Note about JSONL lag
    print()
    print("  Note: Context size reflects the last Claude response in the JSONL.")
    if compaction_count > 0:
        print(f"  This session has been compacted {compaction_count}x. After /compact,")
        print("  the reduced context appears once the next response is generated.")
    else:
        print("  If you just ran /compact, the drop will appear after the next response.")

    if stats.get("detail"):
        print()
        print("  MESSAGE-BY-MESSAGE BREAKDOWN")
        print(f"  {'Line':>6}  {'Type':>10}  {'Input':>8}  {'Cache+':>8}  {'CacheR':>8}  {'Output':>8}  {'Context':>10}")
        print(f"  {'----':>6}  {'----':>10}  {'-----':>8}  {'------':>8}  {'------':>8}  {'------':>8}  {'-------':>10}")
        for m in stats["detail"]:
            print(
                f"  {m['line']:>6}  {m['type']:>10}  "
                f"{m['input_tokens']:>8,}  {m['cache_creation']:>8,}  "
                f"{m['cache_read']:>8,}  {m['output_tokens']:>8,}  "
                f"{m['context_size']:>10,}"
            )
        print()


def get_session_model(jsonl_path):
    """Extract the model name from the first assistant message in a JSONL file."""
    try:
        with open(jsonl_path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") == "assistant":
                    model = record.get("message", {}).get("model")
                    if model:
                        return model
    except (OSError, PermissionError):
        pass
    return "unknown"


def print_sessions_list(sessions):
    """Print a list of all sessions with model info."""
    print(f"{'Session ID':<40} {'Model':<20} {'Size':>10} {'Last Modified':<25}")
    print("-" * 100)
    for s in sessions:
        model = get_session_model(s["path"])
        print(
            f"{s['session_id']:<40} "
            f"{model:<20} "
            f"{format_bytes(s['size_bytes']):>10} "
            f"{s['modified'].strftime('%Y-%m-%d %H:%M:%S'):>25}"
        )
    print(f"\nTotal: {len(sessions)} session(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Find Claude Code session JSONL and calculate context size in tokens"
    )
    parser.add_argument(
        "--project", "-p",
        default=os.getcwd(),
        help="Project directory path (default: current directory)",
    )
    parser.add_argument(
        "--session", "-s",
        default=None,
        help="Session UUID to analyze (default: most recent)",
    )
    parser.add_argument("--all", "-a", action="store_true", help="List all sessions for this project")
    parser.add_argument("--detail", "-d", action="store_true", help="Show message-by-message breakdown")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--ascii", action="store_true", help="Show key stats as ASCII art banners")

    args = parser.parse_args()

    # Find project directory
    project_dir = find_project_dir(args.project)
    if not project_dir:
        encoded = encode_project_path(args.project)
        print(f"Error: No Claude Code sessions found for project.", file=sys.stderr)
        print(f"  Project: {args.project}", file=sys.stderr)
        print(f"  Expected: {PROJECTS_DIR / encoded}", file=sys.stderr)
        sys.exit(1)

    # List all sessions
    if args.all:
        sessions = find_sessions(project_dir)
        if not sessions:
            print("No sessions found.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps([{
                "session_id": s["session_id"],
                "size_bytes": s["size_bytes"],
                "modified": s["modified"].isoformat(),
                "path": str(s["path"]),
            } for s in sessions], indent=2))
        else:
            print(f"\nSessions for: {args.project}")
            print(f"Storage: {project_dir}\n")
            print_sessions_list(sessions)
        sys.exit(0)

    # Find specific session or most recent
    if args.session:
        jsonl_path = project_dir / f"{args.session}.jsonl"
        if not jsonl_path.exists():
            print(f"Error: Session file not found: {jsonl_path}", file=sys.stderr)
            sys.exit(1)
    else:
        session = find_active_session(project_dir)
        if not session:
            print("Error: No session files found.", file=sys.stderr)
            sys.exit(1)
        jsonl_path = session["path"]

    # Parse and report
    stats = parse_session(jsonl_path, detail=args.detail)

    # Check for cached context (written by stop hook after each response)
    # This gives us post-compaction accuracy
    cache_file = CACHE_DIR / f"{project_dir.name}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            cached_ctx = cached.get("latest_context_tokens", 0)
            cached_session = cached.get("session_id", "")
            # Use cache if it's for the same session and has a different (likely newer) value
            if cached_session == stats["session_id"] and cached_ctx != stats["latest_context_tokens"]:
                # Cache was written by the stop hook after the latest response
                # Use it as the authoritative context size
                stats["latest_context_tokens"] = cached_ctx
                context_window = stats["context_window"]
                stats["remaining_tokens"] = max(0, context_window - cached_ctx)
                stats["pct_used"] = round(cached_ctx / context_window * 100, 1) if context_window > 0 else 0
                stats["_source"] = "cache (post-response hook)"
        except (json.JSONDecodeError, OSError):
            pass

    if args.json:
        output = {k: v for k, v in stats.items() if k != "detail"}
        if args.detail and stats.get("detail"):
            output["detail"] = stats["detail"]
        print(json.dumps(output, indent=2))
    else:
        print_report(stats, ascii_mode=args.ascii)


if __name__ == "__main__":
    main()
