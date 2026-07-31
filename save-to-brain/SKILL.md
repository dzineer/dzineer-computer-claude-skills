---
name: save-to-brain
description: Save notes, research, intel, or plans to the DZ-Brain Obsidian vault with proper routing and frontmatter. Usage: /save-to-brain
user-invocable: true
---

# Save to Brain

Routes content to the correct folder in the DZ-Brain Obsidian vault (`~/Documents/DZ-Brain/`).

## Usage

```
/save-to-brain                         # Interactive — asks what to save
/save-to-brain <folder> <title>        # Direct — saves to specified folder
```

## Routing Table

| Content Type | Route | Example |
|---|---|---|
| Lead info | `Leads/<name>/` | Leads/john-smith/profile.md |
| Sprint plan | `Plans/<date-slug>/` | Plans/2026-05-27-cleanup-sprint/ |
| Project notes | `Projects/<name>/` | Projects/agentquoter/architecture.md |
| Daily log | `Journal/` | Journal/2026-05-27.md |
| YouTube/podcast/Reddit | `Intel/` | Intel/yt-ai-seo-breakdown.md |
| Course notes | `Courses/<name>/` | Courses/aeo-masterclass/01-intro.md |
| Reference material | `Reference/` | Reference/pgvector-cheatsheet.md |

## Frontmatter

Every file MUST have:

```yaml
---
title: "<descriptive title>"
tags: [<relevant>, <tags>]
created: YYYY-MM-DD
source: "<url or 'manual' or 'voice-dump'>"
---
```

## Behavior

1. If the user provides content inline, write it directly
2. If the user references a file, read it and route it
3. If the user provides a URL, fetch it and save a distilled version
4. Always confirm the destination path before writing
5. After saving, remind: "Run `npm run sync` in brain-rag/mcp-server to index"

## Lead Workspace Convention

When saving to `Leads/<name>/`, check if `00-README.md` exists. If not, create it as an index file listing all files in the lead folder.

## Journal Convention

Journal entries go to `Journal/YYYY-MM-DD.md`. If the file already exists, append to it under a new H2 heading with the current time.
