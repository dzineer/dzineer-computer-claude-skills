---
name: save
description: Save session context — pure shell+python, no AI invocation needed
disable-model-invocation: false
---
Save session tasks and memory. Processes snapshots into structured files without spawning any AI sessions.

## Usage

```
/save                              # save current session (snapshot -> {cwd}/snapshots/, tasks -> {cwd}/tasks/, memory -> {cwd}/memory/)
/save {session_id}                 # extract from that session's JSONL, save to {cwd}
/save {session_id} {target_folder} # extract from that session, save to target_folder
/save "" {target_folder}           # save current session to target_folder
```

## How it works

**If no session_id is given** (saving current session):

1. Write `{target}/snapshots/_save_snapshot.md` with everything you know — raw dump, be fast:

```markdown
# Session Snapshot
Timestamp: {ISO timestamp}
Project: {target}

## Tasks - In Progress
- [ ] **{task subject}**: {description}
  - [ ] {subtask}
  - [x] {done subtask}

## Tasks - Pending
- [ ] **{task subject}**: {description}

## Tasks - Completed (recent)
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

2. Run the worker (pass the target directory — defaults to cwd):
```bash
~/.claude/skills/save/save-worker.sh "" "{target}"
```

**If session_id IS given** (saving a different/dead session):

Just run the worker — it extracts context from the JSONL directly (no AI needed):
```bash
~/.claude/skills/save/save-worker.sh "{session_id}" "{target}"
```

Where `{target}` is the target_folder argument if provided, otherwise `{cwd}`.

## Output files

- `{target}/tasks/TASKS.md` — human-readable task list
- `{target}/tasks/tasks.yaml` — structured YAML (read by the app)
- `{target}/tasks/tasks.json` — JSON mirror
- `{target}/tasks/INDEX.md` — index with history
- `{target}/tasks/{slug}/` — subtask directories for active tasks
- `{target}/memory/MEMORY.md` — human-readable memory dump
- `{target}/memory/memory.yaml` — structured YAML
- `{target}/memory/memory.json` — JSON mirror
- `{target}/memory/INDEX.md` — index with history

## Step: Confirm

Tell the user whether it succeeded or failed.
