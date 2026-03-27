#!/usr/bin/env bash
# save-worker.sh — Spawns a fresh Claude session to process a save.
#
# Usage: save-worker.sh [session_id] [target_folder]
#
#   session_id     (optional) Claude session ID to extract context from.
#                  If omitted, expects a pre-written snapshot at <target>/.claude/_save_snapshot.md
#   target_folder  (optional) Directory to save tasks/ and memory/ into.
#                  Defaults to current working directory.
#
# Examples:
#   save-worker.sh                                    # snapshot must exist at $PWD/.claude/_save_snapshot.md
#   save-worker.sh abc-123-def                        # extract from session, save to $PWD
#   save-worker.sh abc-123-def /path/to/project       # extract from session, save to /path/to/project
#   save-worker.sh "" /path/to/project                # snapshot must exist, save to /path/to/project

set -euo pipefail

# Allow spawning claude from within a claude session
unset CLAUDECODE 2>/dev/null || true

SESSION_ID="${1:-}"
TARGET_DIR="${2:-$(pwd)}"

# Resolve to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

SNAPSHOT="${TARGET_DIR}/.claude/_save_snapshot.md"

# --- If session ID provided, extract context from the JSONL file ---
if [ -n "$SESSION_ID" ]; then
  echo "Extracting context from session: ${SESSION_ID}"
  echo "Target: ${TARGET_DIR}"

  # Find the session JSONL file
  JSONL_FILE=""
  for f in ~/.claude/projects/*/"${SESSION_ID}.jsonl"; do
    if [ -f "$f" ]; then
      JSONL_FILE="$f"
      break
    fi
  done

  if [ -z "$JSONL_FILE" ]; then
    echo "ERROR: Could not find JSONL file for session ${SESSION_ID}"
    echo "Searched: ~/.claude/projects/*/${SESSION_ID}.jsonl"
    exit 1
  fi

  echo "Found session file: ${JSONL_FILE}"
  JSONL_SIZE=$(wc -l < "$JSONL_FILE" | tr -d ' ')
  echo "Session size: ${JSONL_SIZE} lines"

  mkdir -p "${TARGET_DIR}/.claude"

  # Extract ALL user/assistant text messages from the JSONL into a file
  EXTRACT="${TARGET_DIR}/.claude/_session_extract.txt"
  python3 -c "
import sys, json

messages = []
with open(sys.argv[1], 'r') as f:
    for line in f:
        try:
            obj = json.loads(line.strip())
            msg_type = obj.get('type', '')
            if msg_type in ('user', 'assistant'):
                msg = obj.get('message', {})
                if isinstance(msg, dict):
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
        except:
            pass

# Write all messages
for role, content in messages:
    print(f'=== [{role.upper()}] ===')
    print(content)
    print()
" "$JSONL_FILE" > "$EXTRACT" 2>/dev/null || true

  EXTRACT_LINES=$(wc -l < "$EXTRACT" | tr -d ' ')
  EXTRACT_BYTES=$(wc -c < "$EXTRACT" | tr -d ' ')
  echo "Extracted: ${EXTRACT_LINES} lines, ${EXTRACT_BYTES} bytes"

  if [ "$EXTRACT_BYTES" -lt 50 ]; then
    echo "ERROR: Could not extract meaningful context from JSONL"
    rm -f "$EXTRACT"
    exit 1
  fi

  # Now spawn a fresh claude session to read the extract + existing files and build the snapshot
  claude -p \
    --dangerously-skip-permissions \
    --model sonnet \
    --no-session-persistence \
    "You are a save-worker extracting session context into a snapshot.

Do these steps in order:

1. Read the session extract file: ${EXTRACT}
   This contains ALL user/assistant messages from the session.

2. Also read these files if they exist (for baseline context):
   - ${TARGET_DIR}/tasks/TASKS.md
   - ${TARGET_DIR}/memory/MEMORY.md

3. Write a snapshot file at ${SNAPSHOT} combining everything. Format:

# Session Snapshot
Timestamp: (current ISO timestamp)
Project: ${TARGET_DIR}
Source Session: ${SESSION_ID}

## Tasks - In Progress
(list all in-progress tasks with descriptions and subtasks using - [ ] / - [x])

## Tasks - Pending
(list all pending tasks)

## Tasks - Completed (recent)
(list recently completed tasks)

## Key Context / Memory
- What was being worked on and why
- Important decisions made
- Architecture notes and patterns
- Debugging insights
- User preferences observed
- Key files modified and why
- Everything relevant from the session

## Important File Paths
- path: what it is

Include EVERYTHING. Merge the existing TASKS.md/MEMORY.md with new info from the session messages.
Write the file now."

  rm -f "$EXTRACT"

  if [ ! -f "$SNAPSHOT" ]; then
    echo "ERROR: Failed to create snapshot from session ${SESSION_ID}"
    exit 1
  fi

  echo "Snapshot created successfully."
fi

# --- Validate snapshot exists ---
if [ ! -f "$SNAPSHOT" ]; then
  echo "ERROR: Snapshot not found at ${SNAPSHOT}"
  echo "Either provide a session ID to extract from, or write the snapshot first."
  echo ""
  echo "Usage: save-worker.sh [session_id] [target_folder]"
  exit 1
fi

echo "Processing snapshot into structured files..."
echo "Target: ${TARGET_DIR}"

# --- Process snapshot into structured files ---
claude -p \
  --dangerously-skip-permissions \
  --model sonnet \
  --no-session-persistence \
  "You are a save-worker. Read the raw snapshot file and produce structured save files.

Read the snapshot at: ${SNAPSHOT}

Then do BOTH of these:

--- TASKS --- Save to ${TARGET_DIR}/tasks/

1. mkdir -p ${TARGET_DIR}/tasks/
2. If ${TARGET_DIR}/tasks/TASKS.md already exists, rename it to ${TARGET_DIR}/tasks/TASKS_\$(date +%Y%m%d_%H%M%S).md.
3. Write ${TARGET_DIR}/tasks/TASKS.md with these exact sections:
   ## In Progress
   ## Pending
   ## Completed (recent)
   Use - [ ] for incomplete tasks and - [x] for completed tasks. Include descriptions as sub-bullets.
4. Write ${TARGET_DIR}/tasks/tasks.json — a JSON file with this schema:
   {
     \"last_synced\": \"<ISO timestamp>\",
     \"tasks\": {
       \"in_progress\": [{\"subject\": \"...\", \"description\": \"...\", \"status\": \"in_progress\", \"slug\": \"...\", \"subtasks_dir\": \"${TARGET_DIR}/tasks/<slug>/\", \"subtasks\": [...]}],
       \"pending\": [...],
       \"completed\": [...]
     }
   }
   The slug is the subject slugified (e.g. \"Fix auth bug\" -> \"fix-auth-bug\").
5. For each active (non-completed) task that has subtasks, create:
   - ${TARGET_DIR}/tasks/<slug>/tasks.json — same schema scoped to subtasks, with a parent_task field
   - ${TARGET_DIR}/tasks/<slug>/TASKS.md — itemized subtask breakdown
6. Write/update ${TARGET_DIR}/tasks/INDEX.md with:
   ## Current
   - [TASKS.md](./TASKS.md)
   - [tasks.json](./tasks.json)
   ## History
   - list all TASKS_*.md files, newest first

--- MEMORY --- Save to ${TARGET_DIR}/memory/

1. mkdir -p ${TARGET_DIR}/memory/
2. If ${TARGET_DIR}/memory/MEMORY.md already exists, rename it to ${TARGET_DIR}/memory/MEMORY_\$(date +%Y%m%d_%H%M%S).md.
3. Write ${TARGET_DIR}/memory/MEMORY.md — a full context memory dump from the snapshot. Include everything from Key Context, Memory, and Important File Paths sections. Organize with clear headings.
4. Write ${TARGET_DIR}/memory/memory.json with this schema:
   {
     \"timestamp\": \"<ISO timestamp>\",
     \"project\": \"${TARGET_DIR}\",
     \"context\": \"...\",
     \"active_work\": [...],
     \"key_decisions\": [...],
     \"important_files\": [...],
     \"debugging_insights\": [...],
     \"user_preferences\": [...]
   }
5. Write/update ${TARGET_DIR}/memory/INDEX.md with:
   ## Current
   - [MEMORY.md](./MEMORY.md)
   - [memory.json](./memory.json)
   ## History
   - list all MEMORY_*.md files, newest first

--- CLEANUP ---
After all files are written successfully, delete ${SNAPSHOT}.
Print SAVE COMPLETE when done, or SAVE FAILED: <reason> if something went wrong."
