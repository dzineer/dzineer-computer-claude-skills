#!/usr/bin/env bash
# save-worker.sh — Processes a save snapshot into structured task/memory files.
# No AI required — pure shell + python.
#
# Usage: save-worker.sh [session_id] [target_folder]
#
#   session_id     (optional) Claude session ID to extract context from.
#                  If omitted, expects a pre-written snapshot at <target>/snapshots/_save_snapshot.md
#   target_folder  (optional) Directory to save tasks/ and memory/ into.
#                  Defaults to current working directory.

set -euo pipefail

SESSION_ID="${1:-}"
TARGET_DIR="${2:-$(pwd)}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

SNAPSHOT="${TARGET_DIR}/snapshots/_save_snapshot.md"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ISO_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- If session ID provided, extract context from the JSONL file ---
if [ -n "$SESSION_ID" ]; then
  echo "Extracting context from session: ${SESSION_ID}"

  JSONL_FILE=""
  for f in ~/.claude/projects/*/"${SESSION_ID}.jsonl"; do
    if [ -f "$f" ]; then
      JSONL_FILE="$f"
      break
    fi
  done

  if [ -z "$JSONL_FILE" ]; then
    echo "ERROR: Could not find JSONL file for session ${SESSION_ID}"
    exit 1
  fi

  echo "Found session file: ${JSONL_FILE}"
  mkdir -p "${TARGET_DIR}/snapshots"

  # Extract user/assistant messages and build snapshot directly with python
  python3 "${SKILL_DIR}/snapshot_from_jsonl.py" "$JSONL_FILE" "$SNAPSHOT" "$TARGET_DIR" "$SESSION_ID"

  if [ ! -f "$SNAPSHOT" ]; then
    echo "ERROR: Failed to create snapshot from session ${SESSION_ID}"
    exit 1
  fi
  echo "Snapshot created from session."
fi

# --- Validate snapshot exists ---
if [ ! -f "$SNAPSHOT" ]; then
  echo "ERROR: Snapshot not found at ${SNAPSHOT}"
  echo "Either provide a session ID or write the snapshot first."
  exit 1
fi

echo "Processing snapshot into structured files..."
echo "Target: ${TARGET_DIR}"

# --- Process snapshot into structured files ---
python3 "${SKILL_DIR}/process_snapshot.py" "$SNAPSHOT" "$TARGET_DIR" "$TIMESTAMP" "$ISO_TIMESTAMP"

# --- Sync global auto memory into local memory ---
# The auto memory system writes to ~/.claude/projects/.../memory/
# We copy those frontmatter-based .md files into {cwd}/memory/ so everything is local.
GLOBAL_MEMORY_DIR=""
# Find the global memory dir that matches this project path (or a parent path)
SEARCH_DIR="$TARGET_DIR"
while [ "$SEARCH_DIR" != "/" ] && [ -z "$GLOBAL_MEMORY_DIR" ]; do
  PROJECT_KEY="$(echo "$SEARCH_DIR" | sed 's|[/_]|-|g; s|^-||')"
  for d in ~/.claude/projects/*/memory; do
    [ -d "$d" ] || continue
    DIR_KEY="$(basename "$(dirname "$d")")"
    if [ "$DIR_KEY" = "$PROJECT_KEY" ] || [ "$DIR_KEY" = "-${PROJECT_KEY}" ]; then
      GLOBAL_MEMORY_DIR="$d"
      break
    fi
  done
  SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

if [ -n "$GLOBAL_MEMORY_DIR" ] && [ -d "$GLOBAL_MEMORY_DIR" ]; then
  echo "Syncing global auto memory from ${GLOBAL_MEMORY_DIR} -> ${TARGET_DIR}/memory/"
  mkdir -p "${TARGET_DIR}/memory"
  for f in "$GLOBAL_MEMORY_DIR"/*.md; do
    [ -f "$f" ] || continue
    fname="$(basename "$f")"
    # Skip MEMORY.md — we generate our own
    [ "$fname" = "MEMORY.md" ] && continue
    cp "$f" "${TARGET_DIR}/memory/${fname}"
  done
  echo "Global auto memory synced."
else
  echo "No global auto memory dir found for project key: ${PROJECT_KEY}"
fi

# --- Cleanup ---
rm -f "$SNAPSHOT"
echo "SAVE COMPLETE"
