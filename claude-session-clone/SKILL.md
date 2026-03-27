---
name: claude-session-clone
description: Clone a Claude Code session's transcript into another session. Usage: /claude-session-clone {source_session_id} [target_session_id]
disable-model-invocation: false
---

Clone the full data from one Claude Code session into another — transcript, subagents, tool-results, everything.

## Usage

- `/claude-session-clone {source_id}` — Show info about the source session (size, files, stats)
- `/claude-session-clone {source_id} {target_id}` — Full clone: copies transcript + subagents + tool-results into a new session
- `/claude-session-clone` — List recent sessions to pick from

## How to execute

Run the clone script:

```bash
python3 ~/.claude/skills/claude-session-clone/bin/clone-session.py {ARGS}
```

Where `{ARGS}` are the arguments passed to this skill (the session IDs).

### What the script does

1. **Finds the source session** across all project directories under `~/.claude/projects/`
2. **Shows stats**: transcript size, line count, number of subagent files, tool-result files
3. **If a target ID is given**, performs a full clone:
   - Copies the entire `.jsonl` transcript, rewriting `sessionId` fields to the new target ID
   - Copies the `subagents/` directory (all sub-agent `.jsonl` files)
   - Copies the `tool-results/` directory (all tool result files)
   - Appends a clone marker so the target session knows it was cloned
4. **Reports** what was copied (lines, files, bytes)

### After the script runs

- If it was info-only (no target), present the stats to the user
- If it was a full clone, tell the user the clone is complete and where the files are
- The cloned session can be resumed by Claude Code using the target session ID

### Generating a target session ID

If the user doesn't provide a target session ID, generate one:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

## Notes

- Source sessions can be very large (600MB+, 100K+ lines, 500+ subagent files). The script handles this efficiently by streaming line-by-line.
- The script searches ALL project directories, so cross-project cloning works.
- If the target session already exists, the script refuses to overwrite (safety check).
