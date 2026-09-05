---
name: safe-unwind-restore
description: Safely undo work that was merged or committed the wrong way (self-merged to main, committed to main without a branch, or otherwise landed without the user's approval), then put the good code back the proper way. Use whenever you must remove/rewind changes from a shared branch, unwind your own improper merges, back up files before a risky repo operation, or restore work through a clean branch→PR the user merges. Follow it any time the task is "revert what I did", "fix the branch", "undo the merge", "put it back properly", or "back up before you change anything". Enforces: back up with proof → fix file-by-file with proof → restore from the verified backup → the USER merges. NEVER git revert, NEVER reset/force-push a shared branch, NEVER self-merge.
---

# Safe Unwind & Restore

A three-phase procedure for undoing improperly-landed work and putting the good code back cleanly, with proof at every gate. Born from a real incident (2026-09-05): five PRs were self-merged to `main` without approval and one commit landed on `main` with no branch. This skill is how that gets fixed without a shortcut and without losing the work.

## Absolute rules (never violate)

1. **Never `git revert`.** Forbidden outright (and often permission-blocked). Undo by hand — forward edits and restores.
2. **Never `git reset --hard` or force-push a shared branch** (`main` especially). It rewrites history others may hold.
3. **Never self-merge.** The merge is the USER's gate. You open the PR and present proof; the user merges — unless they explicitly grant a one-time merge conditioned on proof.
4. **Branch BEFORE the first change.** Run `git checkout -b <branch>` first, then `git branch --show-current` to confirm, and re-verify the branch before every commit. The root cause of the incident was committing while still on `main`.
5. **No blind bulk operations.** Handle files individually with per-file verification. No `git checkout . `, no rebuild-in-place of generated output when a faithful restore is available.
6. **Prove, don't claim.** Every phase ends with printed evidence (counts, hashes, empty diffs, green tests), never an assertion. The user's own check is the only acceptance.
7. **No subagents** unless the project explicitly allows them.

## Establish the facts first (read-only)

- Current branch and whether local == remote: `git branch --show-current`, `git rev-parse HEAD origin/main`.
- The **pristine target**: the commit the tree should look like after the fix. If keeping some good change (e.g. a wanted bugfix) and unwinding the rest, the pristine target is the commit right AFTER the kept change and BEFORE the mess.
- Confirm every commit in `<pristine>..HEAD` is yours to unwind: `git log --oneline <pristine>..HEAD`.
- The exact file set touched: `git diff --name-status <first-bad-commit>^..HEAD`. Classify each: added / modified / generated-output.

## Phase A — back up everything, with proof (no repo changes yet)

1. Temp folder **outside the repo** so it can never be committed (a scratchpad dir). State the full path.
2. Copy **every** changed file into it, preserving relative paths — no exception, including generated output if the user says "everything".
3. **Backup proof (gate):** `sha256sum` every repo file AND its backup copy; write both to an `INDEX.md` + `checksums.txt`; print `expected N / copied N / MATCH N / mismatch 0 / missing 0`. If anything mismatches or is missing, STOP — do not touch the repo.
4. `INDEX.md` documents the whole plan: one row per file — path · type · action (remove / restore-to-`<pristine>` / KEEP) · backup path · re-add target.

## Phase B — fix (unwind) file-by-file, with proof

1. `git checkout -b fix/<slug>` off the current branch; confirm you're on it.
2. Per file, the smallest honest action:
   - **added file** → `git rm <path>` (each listed explicitly).
   - **modified file** → `git checkout <pristine> -- <path>` (restore its pristine content).
   - **generated output** (bundles, lockfiles) → restore the pristine committed version, do NOT rebuild in place (a rebuild makes new hashes and isn't a faithful undo).
   - **KEEP files** → do not touch them; verify they stay unchanged.
3. Undo any working-tree ledger/journal edits you made too (they may not be in the PR commits).
4. Commit in small reviewed commits; verify branch before each.
5. **Revert proof:** `git diff <pristine> HEAD -- .` prints **empty** (tree identical to pristine). Plus targeted checks: removed dir gone, kept change intact, offending strings absent.
6. Open the PR. Present the full proof set. **The user merges** (or grants a one-time merge with proof). Never merge on your own initiative.

## Phase C — put the good work back, the proper way

Only after Phase B is merged and the branch is clean.

1. `git checkout -b feat/<slug>-restore`; confirm branch.
2. Restore the good files **from the Phase-A verified backup**, file-by-file.
3. **Restore proof:**
   - each restored file's `sha256` == its backup (all-match);
   - `git diff <pre-revert-commit> HEAD -- <restored paths>` empty **excluding generated files** (source is byte-identical to the original work); regenerate lockfiles/bundles via the real build so they match the source;
   - the project builds and its tests pass (`cargo build` + `cargo test`, or the project's equivalent) — the work is re-proven, not assumed;
   - files that were deliberately kept out stay untouched (0 diff).
4. Commit, push, open the PR with the proof set. **The user merges.**

## What "proof" looks like (paste real output)

- Backup: `expected 92 / copied 92 / sha256 MATCH 92 / mismatch 0 / missing 0`.
- Revert: `git diff <pristine> HEAD` → `0` lines; `git ls-files <removed-dir>` → `0`.
- Restore: `22/22 sha256 MATCH`; source diff vs pre-revert `0` lines; `21 tests passed`.

## Failure handling

If any gate's proof fails (a hash mismatches, a diff is non-empty when it should be empty, a test fails): STOP at that gate, report the exact evidence, and do not proceed to the next phase or the merge. A failed gate is information for the user, never something to work around.
