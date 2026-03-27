---
name: tasks
description: Build out the tasks list that we have planned.
disable-model-invocation: false
---
Create a tasks snapshot from your current context.

**Storage locations**:
- `.claude/tasks/` — top-level task list (project root, NOT ~/.claude/skills/)
- `.tasks/<slug>/` — per-task subtask breakdown (project root)

Steps:
1. Create `.claude/tasks/` directory if it doesn't exist.
2. If `.claude/tasks/TASKS.md` already exists, rename it to `TASKS_{timestamp}.md` in the same directory.
3. Write your current task state to `.claude/tasks/TASKS.md`. Use sections: `## In Progress`, `## Pending`, `## Completed (recent)` with `- [ ]` / `- [x]` checkboxes. Include task descriptions as sub-bullets.
4. Write `.claude/tasks/tasks.json` with the same data as structured JSON. Each active task must include:
   - `subject`, `description`, `status`
   - `slug` — slugified subject (e.g. "Fix auth bug" -> "fix-auth-bug")
   - `subtasks_dir` — pointer to `.tasks/<slug>/` where subtasks live
5. For each active (non-completed) task, create `.tasks/<slug>/tasks.json` if it doesn't exist. This file has the same schema as `.claude/tasks/tasks.json` but scoped to subtasks of that parent task. Add a `parent_task` field.
6. If you have subtasks for a task, write them into the corresponding `.tasks/<slug>/tasks.json`.
7. Update `.claude/tasks/INDEX.md` — `## Current` pointing to `TASKS.md` and `tasks.json`, `## History` listing all `TASKS_{timestamp}.md` files (newest first).

### Subtask Directory Structure
```
.tasks/
  fix-auth-bug/
    tasks.json        # subtasks for "Fix auth bug"
  add-dark-mode/
    tasks.json        # subtasks for "Add dark mode"
```

Each subtask `tasks.json` follows the same schema: `{ parent_task, last_synced, tasks: { in_progress: [], pending: [], completed: [] } }`

We have to run a compact soon and you will forget again.
