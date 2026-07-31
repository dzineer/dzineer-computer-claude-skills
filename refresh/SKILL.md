---
name: refresh
description: Refresh context from saved session state after /clear or new session. Use when starting fresh or after compaction.
disable-model-invocation: false
---
Refresh context by reading saved tasks and memory. Run this after `/clear` or at the start of a new session to pick up where you left off.

## Usage

```
/refresh                    # refresh from saved state in {cwd}
/refresh {session_id}       # refresh by session ID (UUID) — finds the JSONL, resolves project path
/refresh {alias}            # refresh by project alias (e.g. "desktop", "omi")
/refresh {folder_path}      # refresh from a specific folder
```

## Step 1: Resolve target

The argument is auto-detected:

1. **No argument** → use `{cwd}`
2. **UUID pattern** (matches `[0-9a-f-]{36}`) → it's a session ID. Find the JSONL file:
   ```bash
   find ~/.claude/projects/ -name "{session_id}.jsonl" 2>/dev/null
   ```
   Extract the project path from the directory name (reverse the Claude key encoding: hyphens back to `/`, strip the leading `-`). That becomes `{target}`.
3. **Known alias** → map to a project path. Check `~/.claude/skills/refresh/aliases.json` if it exists. If not, try common patterns:
   - `desktop` → look for `*/desktop/tasks/TASKS.md` under common project roots
   - `omi` → look for `*/omi/tasks/TASKS.md`
   - Match against directory basenames in `~/.claude/projects/`
4. **Absolute or relative path** → use it directly as `{target}`

If resolution fails, tell the user what was tried and ask them to provide the full path.

## Step 2: Read saved state — TIERED (token discipline)

The restore cost lives here. Read Tier 1 always; read Tier 2 files ONLY when Tier 1 points at
them for the work you're about to do. Do NOT sweep the memory/ folder "for broader context" —
that burns ~25k tokens restating what Tier 1 already says.

### Tier 1 — always read (target: under ~10KB total)

1. **`{target}/memory/full.md`** — ground truth: active task pointer, next actions, recent
   decisions with file:line refs. This is the primary restore file.
2. **`{target}/tasks/TASKS.md`** — the task INDEX (done / blocked / queued, one line each,
   pointing at per-task files).
3. **The active task file** that full.md / TASKS.md / CLAUDE.md "Active Task" points to
   (e.g. `tasks/<slug>/tasks.md` or `tasks/<slug>/tasks.gibber`). Read only the ACTIVE one.

### Tier 2 — on demand only (never by default)

- `tasks/tasks.yaml`, `memory/memory.yaml` — structured lookups when you need a specific slug/decision
- `snapshots/_save_snapshot.md` — only if full.md looks stale (older timestamp than the snapshot)
- `journal/INDEX.md` — scan ONLY when starting work in an area; surface matching gotchas
  ("heads up: J003 — CLI ignores --model after session init")
- `memory/session_summary.md`, `memory/feedback_*.md`, `memory/project_*.md`, `memory/ui_*.md`,
  `memory/projects.md`, rolling `memory_last_*.md` — reference library; read a specific file only
  when the task touches its topic. (Auto-memory already loads the important ones each session.)

If Tier 1 files are missing or contradict each other, THEN fall back to the snapshot and yaml
files, and say so in the summary.

## Step 3: Present

After reading everything, give the user a concise summary:

1. **Where we left off** — what was actively being worked on
2. **What's done** — recently completed tasks (brief)
3. **What's pending** — remaining work
4. **Key context** — important decisions, preferences, or gotchas that affect next steps

Keep it short. The point is to show the user you have the context, not to recite everything back. End with: "Ready to continue. What do you want to work on?"
