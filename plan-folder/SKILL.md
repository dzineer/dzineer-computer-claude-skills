---
name: plan-folder
description: Create new sprint plan folders with Tony-style date-slug naming and numbered sub-files. Usage: /plan-folder <slug> [count]
user-invocable: true
---

# Plan Folder Creator

Creates structured sprint folders in the DZ-Brain vault using the Tony-style filing pattern.

## Usage

```
/plan-folder <slug>                    # Create folder with README
/plan-folder <slug> <count>            # Create folder with N numbered sub-plan stubs
/plan-folder <slug> --from <file>      # Split an existing plan doc into numbered sub-files
```

## What It Does

When the user runs `/plan-folder <slug>`:

1. **Generate the folder path:**
   ```
   ~/Documents/DZ-Brain/Plans/YYYY-MM-DD-<slug>-sprint/
   ```
   Use today's date. Slug should be kebab-case.

2. **Create the index file:**
   ```
   00-README.md
   ```
   With frontmatter:
   ```yaml
   ---
   title: "<Slug> Sprint"
   tags: [plan, sprint, <slug>]
   created: YYYY-MM-DD
   ---
   ```
   Body: meta-index listing all sub-plans with status checkboxes.

3. **If count is provided**, create numbered stub files:
   ```
   01-<name>.md
   02-<name>.md
   ...
   ```
   Ask the user for names, or generate them from context.

4. **If --from <file> is provided**, read the file and split it into numbered sub-files based on:
   - H2 headings (## sections)
   - Numbered lists (1., 2., etc.)
   - Or natural topic breaks

## Naming Rules

- Folder: `YYYY-MM-DD-<slug>-sprint/`
- Files: `NN-<kebab-case-name>.md` (00 = README, 01+ = sub-plans)
- All files get frontmatter with title, tags, created
- Tags always include: plan, sprint, the slug

## After Creation

- Print the tree structure
- Print the full path
- Remind: "Push to git to trigger Brain sync" (if git is set up)

## Example

```
/plan-folder batcave-cleanup 5

Creates:
~/Documents/DZ-Brain/Plans/2026-05-27-batcave-cleanup-sprint/
├── 00-README.md
├── 01-audit-current-state.md
├── 02-organize-knowledge-base.md
├── 03-clean-stale-deliverables.md
├── 04-update-skills.md
└── 05-final-review.md
```
