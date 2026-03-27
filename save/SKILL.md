---
name: save
description: Save session context by spawning a fresh Claude session to do the heavy lifting
disable-model-invocation: false
---
Save session tasks and memory. Can save the current session OR a different (full/dead) session from a fresh one.

## Usage

```
/save                              # save current session to {cwd}
/save {session_id}                 # resume that session to extract context, save to {cwd}
/save {session_id} {target_folder} # resume that session, save to target_folder
/save "" {target_folder}           # save current session to target_folder
```

## How it works

**If no session_id is given** (saving current session):

1. Write `{target}/.claude/_save_snapshot.md` with everything you know — raw dump, be fast:

```markdown
# Session Snapshot
Timestamp: {ISO timestamp}
Project: {target}

## Tasks — In Progress
- **{task subject}**: {description}
  - Subtasks:
    - [ ] {subtask}
    - [x] {done subtask}

## Tasks — Pending
- **{task subject}**: {description}

## Tasks — Completed (recent)
- [x] **{task subject}**: {description}

## Key Context / Memory
- What we were working on and why
- Important decisions made
- Architecture notes
- Debugging insights
- User preferences
- Key files modified and why
- Anything that would be lost on compaction

## Important File Paths
- {path}: {what it is}
```

2. Run the worker:
```bash
~/.claude/skills/save/save-worker.sh "" "{target}"
```

**If session_id IS given** (saving a different/dead session):

Just run the worker — it will resume that session to extract the snapshot automatically:
```bash
~/.claude/skills/save/save-worker.sh "{session_id}" "{target}"
```

Where `{target}` is the target_folder argument if provided, otherwise `{cwd}`.

## Step: Confirm

Tell the user whether it succeeded or failed.
