---
name: context-calc
description: >
  Find the JSONL session file for the current Claude Code project and calculate
  context size in tokens. Use when the user asks about context usage, token count,
  session size, how much context is left, or wants to find their session JSONL file.
user-invocable: true
---

# Context Calculator

Run the script and output the results directly to the user. Do NOT describe what you are going to do — just run it and show the output.

## Steps

1. Run this command silently:
```bash
python3 ~/.claude/skills/context-calc/scripts/context_calc.py --project "$(pwd)"
```

2. Take the output and present it to the user as a clean summary. Do NOT run the command a second time. Example format:

```
Context: 45.2K / 200.0K tokens (22.6%)
Remaining: 154.8K tokens
Messages: 34 (12 user, 22 assistant)
Tool uses: 18
Compactions: 1x
Duration: ~2 hours
```

That's it. No banners, no tables, no extra explanation. Just the stats.
