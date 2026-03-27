---
name: dump
description: Do a full memory dump from your current context
disable-model-invocation: false
---
We are out of memory. Do a full context memory dump.

**Storage location**: `.claude/memory/` in the current project root (NOT ~/.claude/skills/).

Steps:
1. Create `.claude/memory/` directory if it doesn't exist.
2. If `.claude/memory/MEMORY.md` already exists, rename it to `MEMORY_{timestamp}.md` (e.g. `MEMORY_20260319_120000.md`) in the same directory.
3. Write your full memory dump to `.claude/memory/MEMORY.md`.
4. Also write `.claude/memory/memory.json` with the same content as structured JSON (keys: `timestamp`, `session_id`, `project`, `context`, `active_work`, `key_decisions`, `important_files`, etc.).
5. Update `.claude/memory/INDEX.md` — it should have:
   - A `## Current` section pointing to `MEMORY.md` and `memory.json`
   - A `## History` section listing all `MEMORY_{timestamp}.md` files (newest first)

We have to run a compact soon and you will forget again.
