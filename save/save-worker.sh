#!/usr/bin/env bash
# save-worker.sh — Spawns parallel Claude agents to process a save.
#
# Usage: save-worker.sh [session_id] [target_folder]
#
#   session_id     (optional) Claude session ID to extract context from.
#                  If omitted, expects a pre-written snapshot at <target>/snapshots/_save_snapshot.md
#   target_folder  (optional) Directory to save tasks/ and memory/ into.
#                  Defaults to current working directory.
#
# Architecture:
#   Phase 1: Python extracts text from JSONL (fast, no AI)
#   Phase 2: Two parallel Claude agents, each reading the same input:
#     - Agent 1 (tasks):   TASKS.md, tasks.yaml, tasks.json, subtask dirs, INDEX.md
#     - Agent 2 (memory):  MEMORY.md (index), memory.yaml, memory.json, projects.md, INDEX.md
#     (work history lives in git log — the rolling memory_last_N files are deprecated)
#   Phase 3: Wait for all, verify outputs
#   Phase 4: Audit-fix agent (ALWAYS runs) — owns memory/full.md, prints AUDIT_SCORE
#   Phase 5: Archive snapshot/extract, prune archives to the newest 5 of each

set -euo pipefail

# Allow spawning claude from within a claude session
unset CLAUDECODE 2>/dev/null || true

SESSION_ID="${1:-}"
TARGET_DIR="${2:-$(pwd)}"

# Resolve to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

EXTRACT="${TARGET_DIR}/snapshots/_session_extract.txt"
SNAPSHOT="${TARGET_DIR}/snapshots/_save_snapshot.md"
DATESTAMP=$(date +%Y%m%d_%H%M%S)
ISO_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ============================================================
# Phase 1: Extract text from JSONL (if session ID provided)
# ============================================================
if [ -n "$SESSION_ID" ]; then
  echo "Extracting context from session: ${SESSION_ID}"
  echo "Target: ${TARGET_DIR}"

  JSONL_FILE=""

  # "latest" = save the CURRENT session with zero in-session token cost:
  # resolve the project transcript dir from the target path (walking up
  # parents, using Claude's key encoding), pick the newest .jsonl in it.
  if [ "$SESSION_ID" = "latest" ]; then
    # Collect the newest jsonl from EVERY parent-dir key, then pick the
    # globally newest — the session may have been launched from the target
    # dir or any ancestor (different keys), and the live session's file is
    # always the most recently modified.
    candidates=""
    dir="$TARGET_DIR"
    while [ "$dir" != "/" ]; do
      key=$(echo "$dir" | sed 's/[^a-zA-Z0-9]/-/g')
      proj_dir="$HOME/.claude/projects/$key"
      if [ -d "$proj_dir" ]; then
        newest=$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1)
        [ -n "$newest" ] && candidates="$candidates$newest"$'\n'
      fi
      dir=$(dirname "$dir")
    done
    JSONL_FILE=$(printf '%s' "$candidates" | xargs ls -t 2>/dev/null | head -1)
    if [ -z "$JSONL_FILE" ]; then
      echo "ERROR: Could not resolve latest session transcript for ${TARGET_DIR}"
      exit 1
    fi
    SESSION_ID=$(basename "$JSONL_FILE" .jsonl)
    echo "Resolved latest session: ${SESSION_ID}"
  else
    # Find the session JSONL file by explicit ID
    for f in ~/.claude/projects/*/"${SESSION_ID}.jsonl"; do
      if [ -f "$f" ]; then
        JSONL_FILE="$f"
        break
      fi
    done
  fi

  if [ -z "$JSONL_FILE" ]; then
    echo "ERROR: Could not find JSONL file for session ${SESSION_ID}"
    echo "Searched: ~/.claude/projects/*/${SESSION_ID}.jsonl"
    exit 1
  fi

  echo "Found session file: ${JSONL_FILE}"
  JSONL_SIZE=$(wc -l < "$JSONL_FILE" | tr -d ' ')
  echo "Session size: ${JSONL_SIZE} lines"

  mkdir -p "${TARGET_DIR}/snapshots"

  # Delta extraction: if this session was saved before, skip the lines the
  # last successful save already processed — agents merge into existing files,
  # so they only need what's new. Keeps agent context (and time) flat no
  # matter how long the session grows.
  STATE_FILE="${TARGET_DIR}/snapshots/_save_state"
  OFFSET=0
  if [ -f "$STATE_FILE" ]; then
    read -r PREV_SESSION PREV_LINES < "$STATE_FILE" || true
    if [ "$PREV_SESSION" = "$SESSION_ID" ] && [ "${PREV_LINES:-0}" -gt 0 ] && [ "$PREV_LINES" -le "$JSONL_SIZE" ]; then
      OFFSET="$PREV_LINES"
      echo "Delta mode: skipping first ${OFFSET} lines (saved previously)"
    fi
  fi

  # Extract user/assistant text messages from the JSONL (from OFFSET onward)
  python3 -c "
import sys, json

offset = int(sys.argv[2])
messages = []
with open(sys.argv[1], 'r') as f:
    for i, line in enumerate(f):
        if i < offset:
            continue
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

for role, content in messages:
    print(f'=== [{role.upper()}] ===')
    print(content)
    print()
" "$JSONL_FILE" "$OFFSET" > "$EXTRACT" 2>/dev/null || true

  EXTRACT_LINES=$(wc -l < "$EXTRACT" | tr -d ' ')
  EXTRACT_BYTES=$(wc -c < "$EXTRACT" | tr -d ' ')
  echo "Extracted: ${EXTRACT_LINES} lines, ${EXTRACT_BYTES} bytes"

  if [ "$EXTRACT_BYTES" -lt 50 ]; then
    if [ "$OFFSET" -gt 0 ]; then
      echo "Nothing new since last save (delta empty). Save files already current."
      rm -f "$EXTRACT"
      exit 0
    fi
    echo "ERROR: Could not extract meaningful context from JSONL"
    rm -f "$EXTRACT"
    exit 1
  fi
fi

# ============================================================
# Resolve input file
# ============================================================
# Extract-mode (session id given) uses the extract Phase 1 just wrote.
# Snapshot-mode prefers the snapshot — a leftover extract from an earlier
# lite save is stale and must not shadow a freshly written snapshot.
INPUT_FILE=""
if [ -n "$SESSION_ID" ] && [ -f "$EXTRACT" ]; then
  INPUT_FILE="$EXTRACT"
elif [ -f "$SNAPSHOT" ]; then
  INPUT_FILE="$SNAPSHOT"
elif [ -f "$EXTRACT" ]; then
  INPUT_FILE="$EXTRACT"
else
  echo "ERROR: No input file found."
  echo "Expected either: ${EXTRACT} or ${SNAPSHOT}"
  echo "Either provide a session ID to extract from, or write the snapshot first."
  exit 1
fi

echo "Input file: ${INPUT_FILE} ($(wc -c < "$INPUT_FILE" | tr -d ' ') bytes)"
echo "Processing with 2 parallel agents..."
echo "Datestamp: ${DATESTAMP}"

# ============================================================
# Phase 2: Three parallel Claude agents
# ============================================================
mkdir -p "${TARGET_DIR}/tasks" "${TARGET_DIR}/memory" "${TARGET_DIR}/snapshots"

# --- Agent 1: Tasks ---
PROMPT_TASKS="You are a save-worker focused ONLY on extracting and writing TASK data.

NOTE: the session context file may be a DELTA (only activity since the last save).
The baseline files are authoritative for anything the context doesn't mention —
merge new info in; never drop existing entries just because the context omits them.

Do these steps:

1. Read the session context file: ${INPUT_FILE}
2. Read these baseline files if they exist (to merge with, not overwrite):
   - ${TARGET_DIR}/tasks/TASKS.md
   - ${TARGET_DIR}/tasks/tasks.yaml

3. If ${TARGET_DIR}/tasks/TASKS.md already exists, rename it to ${TARGET_DIR}/tasks/TASKS_${DATESTAMP}.md

4. Write ${TARGET_DIR}/tasks/TASKS.md as a compact INDEX, BUDGET 60 LINES MAX:
   ## Done (recent)   — one line per item: - [x] **title** (tasks/{slug}/ if it has a folder)
   ## In Progress / Blocked — one line per item + at most one indented line for the blocker
   ## Queued          — one line per item
   NO sub-bullet dumps, NO subtask lists — details live ONLY in tasks/{slug}/ files;
   every line should point at its per-task file when one exists.

5. Write ${TARGET_DIR}/tasks/tasks.yaml. (tasks.json mirror is DEPRECATED — do not
   write it; delete it if present.) YAML schema:
   last_synced: \"${ISO_TIMESTAMP}\"
   tasks:
     in_progress:
       - subject: \"Task name\"
         description: \"...\"
         status: in_progress
         slug: \"task-name\"
         subtasks_dir: \"${TARGET_DIR}/tasks/task-name/\"
         subtasks:
           - subject: \"Subtask\"
             status: pending
     pending:
       - subject: \"Task name\"
         description: \"...\"
         status: pending
         slug: \"task-name\"
     completed:
       - subject: \"Task name\"
         description: \"...\"
         status: completed
         slug: \"task-name\"
   The slug is the subject slugified (e.g. \"Fix auth bug\" -> \"fix-auth-bug\").

6. ONLY for tasks whose status or content CHANGED per the session context (skip
   unchanged tasks entirely — do not rewrite their folders), create/update:
   - ${TARGET_DIR}/tasks/SLUG/tasks.yaml
   - ${TARGET_DIR}/tasks/SLUG/TASKS.md
   (replace SLUG with the actual slug; SLUG/tasks.json is deprecated — don't write it)

7. Write ${TARGET_DIR}/tasks/INDEX.md:
   ## Current
   - [TASKS.md](./TASKS.md)
   - [tasks.yaml](./tasks.yaml)
   ## History
   - list all TASKS_*.md files found in ${TARGET_DIR}/tasks/, newest first

Print TASKS_DONE when complete."

# --- Agent 2: Memory + Projects ---
PROMPT_MEMORY="You are a save-worker focused ONLY on extracting and writing MEMORY and PROJECT data.

NOTE: the session context file may be a DELTA (only activity since the last save).
The baseline files are authoritative for anything the context doesn't mention —
merge new info in; never drop existing entries just because the context omits them.

Do these steps:

1. Read the session context file: ${INPUT_FILE}
2. Read these baseline files if they exist (to merge with, not overwrite):
   - ${TARGET_DIR}/memory/MEMORY.md
   - ${TARGET_DIR}/memory/memory.yaml
   - ${TARGET_DIR}/memory/projects.md

3. If ${TARGET_DIR}/memory/MEMORY.md already exists, rename it to ${TARGET_DIR}/memory/MEMORY_${DATESTAMP}.md

4. Write ${TARGET_DIR}/memory/MEMORY.md — a compact INDEX, BUDGET 40 LINES MAX.
   One line per durable memory note: - **topic** — one-line hook (where the detail lives).
   NO full context dump. Git history is the primary work log — memory records ONLY what
   git can't show: decisions, gotchas, architecture rationale, user preferences, blockers.
   Detail lives in memory.yaml / per-note files / journal; MEMORY.md just points at it.
   Merge: keep still-relevant lines from the old MEMORY.md, add new ones, drop stale ones.

5. Write ${TARGET_DIR}/memory/memory.yaml. (memory.json mirror is DEPRECATED — do not
   write it; delete it if present.) Update ONLY entries that changed; keep the rest.
   YAML schema:
   timestamp: \"${ISO_TIMESTAMP}\"
   project: \"${TARGET_DIR}\"
   context: \"Summary of what was being worked on\"
   active_work:
     - \"Item 1\"
   key_decisions:
     - \"Decision 1\"
   important_files:
     - path: \"/path/to/file\"
       description: \"What it is\"
   debugging_insights:
     - \"Insight 1\"
   user_preferences:
     - \"Preference 1\"
6. Read ${TARGET_DIR}/memory/projects.md if it exists. Update it (don't overwrite from scratch) with any NEW projects discovered in this session. Each project entry must include:
   - Type (app, website, pipeline, etc.)
   - CWD (working directory)
   - Git repo URL
   - Branch
   - What it is (1-2 sentences)
   - Key files
   - Status (active, pending, completed)
   Only add new projects or update existing ones. Do NOT remove projects not mentioned in this session.
   Write to ${TARGET_DIR}/memory/projects.md.

7. Write ${TARGET_DIR}/memory/INDEX.md:
   ## Current
   - [MEMORY.md](./MEMORY.md)
   - [memory.yaml](./memory.yaml)
   ## History
   - list all MEMORY_*.md files found in ${TARGET_DIR}/memory/, newest first

Print MEMORY_DONE when complete."

# Launch both agents in parallel
# (Work-history agent removed: git log is the primary work log — commit-often policy.
#  memory_last_10/20/30_items.md are DEPRECATED; existing files are left untouched.)
echo "Launching Agent 1 (tasks)..."
claude -p \
  --dangerously-skip-permissions \
  --model sonnet \
  --no-session-persistence \
  "$PROMPT_TASKS" > "${TARGET_DIR}/snapshots/_agent_tasks.log" 2>&1 &
PID_TASKS=$!

echo "Launching Agent 2 (memory + projects)..."
claude -p \
  --dangerously-skip-permissions \
  --model sonnet \
  --no-session-persistence \
  "$PROMPT_MEMORY" > "${TARGET_DIR}/snapshots/_agent_memory.log" 2>&1 &
PID_MEMORY=$!

echo "Both agents running (PIDs: ${PID_TASKS}, ${PID_MEMORY})"
echo "Waiting for completion..."

# ============================================================
# Phase 3: Wait, verify, cleanup
# ============================================================
FAIL=0

wait $PID_TASKS  || { echo "WARN: Tasks agent failed (exit $?) — see ${TARGET_DIR}/snapshots/_agent_tasks.log"; FAIL=1; }
echo "Agent 1 (tasks) finished."

wait $PID_MEMORY  || { echo "WARN: Memory agent failed (exit $?) — see ${TARGET_DIR}/snapshots/_agent_memory.log"; FAIL=1; }
echo "Agent 2 (memory) finished."

# Verify key outputs exist
echo ""
echo "Verifying outputs..."
for f in tasks/TASKS.md tasks/tasks.yaml memory/MEMORY.md memory/memory.yaml; do
  if [ -f "${TARGET_DIR}/$f" ]; then
    echo "  OK: $f"
  else
    echo "  MISSING: $f"
    FAIL=1
  fi
done

# Check optional outputs
for f in memory/projects.md; do
  if [ -f "${TARGET_DIR}/$f" ]; then
    echo "  OK: $f"
  else
    echo "  WARN: $f not created"
  fi
done

# ============================================================
# Phase 4: Out-of-process audit-fix (ALWAYS runs — it owns memory/full.md,
# the primary /refresh restore file, and scores the final Tier 1 state)
# ============================================================
echo ""
echo "Running out-of-process audit-fix agent..."
PROMPT_AUDIT="You are a save-audit agent. Ground truth: the session context at ${INPUT_FILE}.

NOTE: the session context may be a DELTA (only activity since the last save). Facts in
the Tier 1 files that the context doesn't mention are fine — only flag a gap when the
context ACTIVELY contradicts a file, or contains something the files lack.

1. Read the session context file, then read the TIER 1 restore set:
   - ${TARGET_DIR}/memory/full.md (ground truth file — CREATE it if missing, update if stale:
     active task pointer, next actions, recent decisions with file:line refs, <=120 lines)
   - ${TARGET_DIR}/tasks/TASKS.md
   - the active task file that those point to (e.g. ${TARGET_DIR}/tasks/<slug>/tasks.md)

2. Find gaps vs the session context: MISSING facts, STALE statuses, CONTRADICTIONS.

3. FIX every gap directly in the Tier 1 files (session context wins on conflicts).

4. THEN re-read the fixed Tier 1 files and score the FINAL state: could a fresh
   session resume correctly from those files ALONE, as they exist NOW after your
   fixes? Score what you leave behind, not what you found — the number tells the
   user whether it is safe to /clear.

5. Print exactly one final line: AUDIT_SCORE: <0-100>"
claude -p \
  --dangerously-skip-permissions \
  --model sonnet \
  --no-session-persistence \
  "$PROMPT_AUDIT" > "${TARGET_DIR}/snapshots/_agent_audit.log" 2>&1 || echo "WARN: audit agent failed — see snapshots/_agent_audit.log"
SCORE_LINE=$(grep -oE "AUDIT_SCORE: [0-9]+" "${TARGET_DIR}/snapshots/_agent_audit.log" | tail -1 || true)
echo "Recovery confidence: ${SCORE_LINE:-unknown (see snapshots/_agent_audit.log)}"

if [ ! -f "${TARGET_DIR}/memory/full.md" ]; then
  echo "  MISSING: memory/full.md (audit agent should have created it)"
  FAIL=1
fi

# ============================================================
# Phase 5: Archive with timestamp, then prune to the newest 5 of each
# ============================================================
if [ -f "$SNAPSHOT" ]; then
  cp "$SNAPSHOT" "${TARGET_DIR}/snapshots/_save_snapshot_${DATESTAMP}.md"
fi
if [ -f "$EXTRACT" ]; then
  cp "$EXTRACT" "${TARGET_DIR}/snapshots/_session_extract_${DATESTAMP}.txt"
fi
for pattern in "_save_snapshot_*.md" "_session_extract_*.txt"; do
  { ls -t "${TARGET_DIR}/snapshots/"$pattern 2>/dev/null || true; } | tail -n +6 | while read -r old; do
    rm -f "$old"
  done
done

# Record delta watermark (session + line count) only on a clean save, so a
# failed save never advances the offset and loses unsaved messages.
if [ "$FAIL" -eq 0 ] && [ "$INPUT_FILE" = "$EXTRACT" ] && [ -n "${SESSION_ID:-}" ]; then
  printf '%s %s\n' "$SESSION_ID" "$JSONL_SIZE" > "${TARGET_DIR}/snapshots/_save_state"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "SAVE COMPLETE"
else
  echo "SAVE COMPLETED WITH WARNINGS — check agent logs in ${TARGET_DIR}/snapshots/"
fi
