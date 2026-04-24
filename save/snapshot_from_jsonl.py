#!/usr/bin/env python3
"""Extract a snapshot from a Claude session JSONL file. No AI needed."""
import json
import os
import re
import sys
from datetime import datetime, timezone

def extract_messages(jsonl_path):
    """Extract user/assistant text messages from JSONL."""
    messages = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                msg_type = obj.get('type', '')
                if msg_type not in ('user', 'assistant'):
                    continue
                msg = obj.get('message', {})
                if not isinstance(msg, dict):
                    continue
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_parts = []
                    for p in content:
                        if isinstance(p, dict) and p.get('type') == 'text':
                            text_parts.append(p.get('text', ''))
                    content = '\n'.join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)
                if content and len(content.strip()) > 5:
                    messages.append((msg_type, content))
            except Exception:
                pass
    return messages


def extract_tasks(messages):
    """Find task-related content from messages."""
    in_progress = []
    pending = []
    completed = []

    for role, content in messages:
        # Look for task patterns: - [ ] task, - [x] task, etc.
        for line in content.split('\n'):
            line = line.strip()
            if re.match(r'^-\s*\[x\]', line, re.IGNORECASE):
                task = re.sub(r'^-\s*\[x\]\s*', '', line).strip()
                if task and task not in completed:
                    completed.append(task)
            elif re.match(r'^-\s*\[\s\]', line):
                task = re.sub(r'^-\s*\[\s\]\s*', '', line).strip()
                if task and task not in pending:
                    pending.append(task)

    return in_progress, pending, completed


def extract_key_context(messages):
    """Extract key context items from the conversation."""
    context_lines = []
    files_mentioned = set()

    for role, content in messages:
        # Collect file paths mentioned
        for match in re.finditer(r'(?:^|\s)(/[^\s:]+\.\w+)', content):
            path = match.group(1)
            if len(path) < 200:
                files_mentioned.add(path)

    # Use the last few assistant messages as context summary
    assistant_msgs = [(r, c) for r, c in messages if r == 'assistant']
    for _, content in assistant_msgs[-5:]:
        for line in content.split('\n'):
            line = line.strip()
            if line and len(line) > 20 and not line.startswith('```'):
                context_lines.append(line)
                if len(context_lines) > 30:
                    break
        if len(context_lines) > 30:
            break

    return context_lines, list(files_mentioned)[:50]


def main():
    jsonl_path = sys.argv[1]
    snapshot_path = sys.argv[2]
    target_dir = sys.argv[3]
    session_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"

    messages = extract_messages(jsonl_path)
    if not messages:
        print("ERROR: No messages found in JSONL", file=sys.stderr)
        sys.exit(1)

    in_progress, pending, completed = extract_tasks(messages)
    context_lines, file_paths = extract_key_context(messages)

    # Also read existing TASKS.md and MEMORY.md if they exist
    existing_tasks = ""
    tasks_path = os.path.join(target_dir, "tasks", "TASKS.md")
    if os.path.exists(tasks_path):
        with open(tasks_path) as f:
            existing_tasks = f.read()

    existing_memory = ""
    memory_path = os.path.join(target_dir, "memory", "MEMORY.md")
    if os.path.exists(memory_path):
        with open(memory_path) as f:
            existing_memory = f.read()

    # Build snapshot
    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)

    with open(snapshot_path, 'w') as f:
        f.write(f"# Session Snapshot\n")
        f.write(f"Timestamp: {now}\n")
        f.write(f"Project: {target_dir}\n")
        f.write(f"Source Session: {session_id}\n\n")

        f.write("## Tasks - In Progress\n")
        if in_progress:
            for t in in_progress:
                f.write(f"- [ ] {t}\n")
        else:
            f.write("- (none detected)\n")
        f.write("\n")

        f.write("## Tasks - Pending\n")
        if pending:
            for t in pending:
                f.write(f"- [ ] {t}\n")
        else:
            f.write("- (none detected)\n")
        f.write("\n")

        f.write("## Tasks - Completed (recent)\n")
        if completed:
            for t in completed:
                f.write(f"- [x] {t}\n")
        else:
            f.write("- (none detected)\n")
        f.write("\n")

        f.write("## Key Context / Memory\n")
        if context_lines:
            for line in context_lines[:30]:
                f.write(f"- {line}\n")
        f.write("\n")

        if existing_memory:
            f.write("## Previous Memory\n")
            f.write(existing_memory)
            f.write("\n\n")

        if existing_tasks:
            f.write("## Previous Tasks\n")
            f.write(existing_tasks)
            f.write("\n\n")

        f.write("## Important File Paths\n")
        if file_paths:
            for p in file_paths:
                f.write(f"- {p}\n")
        f.write("\n")

    print(f"Snapshot written: {snapshot_path}")


if __name__ == '__main__':
    main()
