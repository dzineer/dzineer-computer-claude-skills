---
name: continue
description: "Resume work after /clear or new session. Reads CLAUDE.md, phase task files, and memory to restore full context."
user-invocable: true
---

# Continue Session

Restores full working context after `/clear` or a new session by reading the project's CLAUDE.md, phase task progress, and memory.

## Usage

```
/continue          — Full recovery
/continue quick    — Skip build verification
```

## Procedure

### Step 1: Read CLAUDE.md

Read `{cwd}/CLAUDE.md` for architecture, governance rules, active state, and key facts.

### Step 2: Read phase task progress

Scan `{cwd}/phases/` to find the current active phase(s). For each phase directory (sorted numerically), check its `tasks/*.json` files for `"passes": false` to identify incomplete work.

```bash
for f in {cwd}/phases/phase_*/tasks/*.json; do grep -l '"passes": false' "$f"; done
```

Read the first incomplete phase's task JSON(s) to understand what's next.

### Step 3: Read memory

Read these files (skip any that don't exist):

1. `{cwd}/memory/MEMORY.md` — full context, decisions, debugging insights, preferences
2. `{cwd}/memory/memory.yaml` — structured state (active_work, key_decisions, important_files)
3. `{cwd}/memory/memory_last_10_items.md` — recent work history

### Step 4: Verify build state (skip if "quick" arg)

Run:
```bash
rtk cargo test --workspace
```

If tests fail, report which tests failed and what the likely cause is.

### Step 5: Present status

Give the user a concise summary:

1. **Active work** — current phase, which tasks are in progress or next
2. **Recent completions** — last phase(s) finished
3. **Next up** — next incomplete tasks with VIBE IDs
4. **Build state** — pass/fail (if checked)
5. **Key context** — decisions, blockers, or gotchas that affect next steps

End with: "Ready to continue. What do you want to work on?"
