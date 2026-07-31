---
name: plan-split
description: Split a single plan document into numbered sub-files using parallel agents. Usage: /plan-split <file-or-url>
user-invocable: true
---

# Plan Splitter

Takes a single plan document (local file, pasted text, or URL) and splits it into a Tony-style numbered plan folder with parallel agent processing.

## Usage

```
/plan-split <file>                     # Split a local markdown file
/plan-split <url>                      # Fetch and split a web document
/plan-split                            # Split from clipboard/pasted text (ask user)
```

## What It Does

1. **Read the source document**
   - If file path: Read the file
   - If URL: WebFetch the content
   - If neither: Ask the user to paste the content

2. **Analyze structure** — identify natural sections:
   - H2 headings (## sections)
   - Numbered items (1., 2., etc.)
   - Topic breaks with clear boundaries
   - Target: 3-12 sub-plans (if more, group related items)

3. **Generate a slug** from the document title or first heading
   - kebab-case, max 4 words
   - Example: "Q3 Revenue Growth Strategy" -> `q3-revenue-growth`

4. **Create the sprint folder:**
   ```
   ~/Documents/DZ-Brain/Plans/YYYY-MM-DD-<slug>-sprint/
   ```

5. **Split into numbered files** using parallel agents:
   - Spawn one agent per section for extraction + formatting
   - Each agent writes its `NN-<section-slug>.md` file
   - All run in parallel for speed

6. **Generate 00-README.md** — meta-index with:
   - Source reference (file path or URL)
   - List of all sub-plans with checkbox status
   - Tags and created date in frontmatter

7. **Print the tree and path**

## File Format

Each sub-plan file:
```yaml
---
title: "<Section Title>"
tags: [plan, sprint, <slug>, <section-tag>]
created: YYYY-MM-DD
source: "<original file or URL>"
---
```

Body: the section content, cleaned and formatted as actionable items.

## Parallel Processing

When splitting a document with many sections, use the Agent tool to spawn parallel workers:
- Each agent gets one section to extract and format
- All agents write to the same sprint folder
- Agents should use `Write` tool, not `Bash`
- Wait for all agents to complete before generating README

## Example

```
/plan-split ~/Documents/q3-strategy.md

Analyzing... found 8 sections.
Creating: ~/Documents/DZ-Brain/Plans/2026-05-27-q3-strategy-sprint/

Spawning 8 parallel agents...
  [1/8] 01-market-positioning.md
  [2/8] 02-content-pipeline.md
  [3/8] 03-lead-gen-automation.md
  ...

Done. 8 sub-plans + README created.
~/Documents/DZ-Brain/Plans/2026-05-27-q3-strategy-sprint/
```
