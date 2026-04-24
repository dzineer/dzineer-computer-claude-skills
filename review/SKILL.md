---
name: review
description: Review saved session state to restore context after /clear or new session. Use when starting fresh or after compaction.
disable-model-invocation: false
---
Review saved tasks and memory to restore context. Run this after `/clear` or at the start of a new session to pick up where you left off.

## Usage

```
/review                # review saved state in {cwd}
/review {target}       # review saved state in a specific folder
```

## How it works

Read the following files in order from `{target}` (defaults to `{cwd}`). For each file that exists, read it and internalize the context:

1. **`{target}/tasks/TASKS.md`** — current task list (in-progress, pending, completed)
2. **`{target}/memory/MEMORY.md`** — key context, decisions, important files
3. **`{target}/tasks/tasks.yaml`** — structured task data with slugs and subtask pointers
4. **`{target}/memory/memory.yaml`** — structured memory data
5. **`{target}/snapshots/_save_snapshot.md`** — latest raw snapshot (if exists)

Also check for global auto memory files in `{target}/memory/`:
- `session_summary.md`
- `user_preferences.md`
- `feedback_*.md`
- `project_*.md`
- `ui_*.md`

## Step: Present

After reading everything, give the user a concise summary:

1. **Where we left off** — what was actively being worked on
2. **What's done** — recently completed tasks (brief)
3. **What's pending** — remaining work
4. **Key context** — important decisions, preferences, or gotchas that affect next steps

Keep it short. The point is to show the user you have the context, not to recite everything back. End with: "Ready to continue. What do you want to work on?"
