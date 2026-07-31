---
name: save
description: Save session context by spawning a fresh Claude session to do the heavy lifting
disable-model-invocation: false
---
Save session tasks and memory. Can save the current session OR a different (full/dead) session from a fresh one.

## Usage

```
/save                              # save current session (snapshot → {cwd}/snapshots/, tasks → {cwd}/tasks/, memory → {cwd}/memory/)
/save lite                         # LOW-CONTEXT save: near-zero in-session tokens (see below)
/save {session_id}                 # extract that session's transcript, save to {cwd}
/save {session_id} {target_folder} # extract that session, save to target_folder
/save "" {target_folder}           # save current session to target_folder
```

## Low-context mode (`/save lite`) — when the context window is nearly full

The current session spends almost nothing: do NOT write a snapshot, do NOT run the in-session
audit loop. Run ONE command and report its output:

```bash
~/.claude/skills/save/save-worker.sh latest "{target}"
```

The worker resolves the current session's transcript from disk (newest JSONL in the project
dir), extracts it with Python (no AI), writes all save files with fresh out-of-process agents,
and runs the audit-fix as an out-of-process agent too — it prints `Recovery confidence: N`.
Total in-session cost: one Bash call + reading a few output lines.

**Auto-select lite mode** whenever context is tight (post-compaction, or the session is long) —
that is exactly when an in-session snapshot dump would hurt most. Regular `/save` remains better
early in a session, when in-session knowledge is richer than the transcript text.

## Principles (token discipline)

- **Git history is the primary work log.** Per the commit-often policy, `git log` narrates
  what was done. Save files record ONLY what git can't show: decisions, blockers, gotchas,
  research findings, next actions. Never restate work that a commit message already covers.
- **One source per fact.** A fact lives in exactly ONE file; everything else points at it.
  Duplication is what makes saves go stale — the audit loop exists to catch drift, but the
  cheapest fix is not duplicating in the first place.
- **Hard size budgets.** When a file exceeds its budget, PRUNE it during the save (move
  history to a rotated `{name}_{timestamp}.md` snapshot, keep only what's live).
- **Delta, not dump.** The snapshot records what changed THIS session, not everything known.

## What Gets Saved (with budgets)

### Tier 1 — the restore set (what /refresh reads; keep small)
- `memory/full.md` — ground truth: active task pointer, next actions, recent decisions with
  file:line refs, last ~5 actions. **Budget: ≤120 lines.** Rewrite in place; prune anything
  already recorded in a per-task file or journal.
- `tasks/TASKS.md` — task INDEX only: done / blocked / queued, one line each, each pointing
  at its per-task file. **Budget: ≤60 lines.** Details go in `tasks/{slug}/`, never here.
- `tasks/{slug}/` — per-task breakdowns (the ONLY place for task detail and status notes).

### Tier 2 — reference (written when changed, not read on refresh)
- `tasks/tasks.yaml`, `memory/memory.yaml` — structured data. Update ONLY entries that
  changed this session; never regenerate wholesale.
- `memory/MEMORY.md` — INDEX of memory notes, one line per note. **Budget: ≤40 lines.**
  Never a "full context dump" — content lives in the per-note files.
- `memory/memory_last_10_items.md` — **DEPRECATED along with `last_20`/`last_30` — do not
  write any of them.** Git history is the work log now (commit-often policy); `git log`
  replaces the rolling item list. Leave existing files untouched.
- `memory/projects.md` — projects index; touch only the current project's entry.

## How it works

**If no session_id is given** (saving current session):

1. Write `{target}/snapshots/_save_snapshot.md` — a SESSION DELTA, **budget ≤80 lines**.
   Record only what changed or was learned this session that is not already in a Tier 1 file.
   Anything durable (decisions, gotchas, task status) belongs in full.md / per-task files /
   journal — put it THERE and let the snapshot reference it, not restate it:

```markdown
# Session Snapshot (delta)
Timestamp: {ISO timestamp}
Project: {target}
Branch/PR: {branch, PR#, merged?}

## Next action (one line — what to do first after restore)
{the single most important next step, with file:line if applicable}

## Changed this session
- {file or area}: {what changed and why} ({file:line})

## Decisions made this session
- {decision} → recorded in {which durable file}

## New blockers / open questions
- {blocker}: {what's needed to unblock}
```

(No work-item list — `git log` on the feature branch is the work history.)

2. Run the worker (pass the target directory — defaults to cwd):
```bash
~/.claude/skills/save/save-worker.sh "" "{target}"
```

**If session_id IS given** (saving a different/dead session):

Just run the worker — it will resume that session to extract the snapshot automatically:
```bash
~/.claude/skills/save/save-worker.sh "{session_id}" "{target}"
```

Where `{target}` is the target_folder argument if provided, otherwise `{cwd}`.

## Step: Audit (worker-owned, all modes)

The worker ALWAYS runs an out-of-process audit-fix agent as its final phase. That agent
owns `memory/full.md` (creates it if missing), fixes MISSING/STALE/CONTRADICTORY gaps in
the Tier 1 restore set (full.md + TASKS.md + active task file), then scores the final
state and prints `Recovery confidence: N`. There is no in-session audit loop — just
relay the score.

- Score >= 85: safe to /clear.
- Score below 85 (or `unknown`): read `snapshots/_agent_audit.log` for the remaining
  gaps, fix them from in-session knowledge if you still have it, and warn the user that
  /clear may lose context.

Why the threshold matters: a save that scores 60% is worse than no save — the next
session reads stale data and wastes time undoing wrong assumptions.

## Step: Confirm

Tell the user whether it succeeded or failed, including the recovery confidence score.

Example outputs:
- "Saved. Recovery confidence: 93%. Safe to /clear."
- "Saved. Recovery confidence: 72%. Remaining gaps: [list]. Staying in session recommended."
