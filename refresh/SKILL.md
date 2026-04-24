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

## Step 2: Read saved state

Read the following files in order from `{target}`. For each file that exists, read it and internalize the context:

1. **`{target}/tasks/TASKS.md`** — current task list (in-progress, pending, completed)
2. **`{target}/memory/MEMORY.md`** — key context, decisions, important files
3. **`{target}/tasks/tasks.yaml`** — structured task data with slugs and subtask pointers
4. **`{target}/memory/memory.yaml`** — structured memory data
5. **`{target}/snapshots/_save_snapshot.md`** — latest raw snapshot (if exists)

Also check for additional memory files in `{target}/memory/`:
- `session_summary.md`
- `user_preferences.md`
- `feedback_*.md`
- `project_*.md`
- `ui_*.md`

## Step 3: Present

After reading everything, give the user a concise summary:

1. **Where we left off** — what was actively being worked on
2. **What's done** — recently completed tasks (brief)
3. **What's pending** — remaining work
4. **Key context** — important decisions, preferences, or gotchas that affect next steps

Keep it short. The point is to show the user you have the context, not to recite everything back. End with: "Ready to continue. What do you want to work on?"
