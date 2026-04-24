---
name: gibber-executor
description: Execute .gibber task files by spawning sub-agents, validating results, and updating task status automatically. Use when a .gibber task file exists with §status:§queued and needs to be executed, or when orchestrating multi-task builds from a parent .gibber file.
---

# Gibber Executor Skill

Reads `.gibber` task files and autonomously executes them by spawning sub-agents, validating their output, and updating task status. Closes the loop between Gibber-as-spec and Gibber-as-execution.

## When to invoke

- A `.gibber` file has `§status:§queued` and needs execution
- A parent `.gibber` has `§todo` subtasks that need to be worked through
- User says "execute", "run", "build this" while a `.gibber` task is in context
- After a sub-agent completes, to validate and update the `.gibber` status

## Execution Protocol

### Step 1 — Parse the task

Read the `.gibber` file. Extract:
- `§id` — task identifier
- `§goal` — what needs to be built
- `§files` — expected output files
- `§notes` — implementation details (these become the sub-agent prompt)
- `§tests` — validation criteria
- `§depends` — prerequisite tasks (check they are `§done` first)

### Step 2 — Check dependencies

For each ID in `§depends`, find its `.gibber` file and confirm `§status:§done`.
If any dependency is not `§done`, skip this task and report the blocker.

### Step 3 — Update status to §wip

Edit the `.gibber` file: change `§status:§queued` to `§status:§wip`.

### Step 4 — Build the sub-agent prompt

Generate the sub-agent prompt from the task. The prompt MUST include:

```
PREAMBLE (always include):

You are executing a Gibber-tracked task. When you complete your work:

1. Write the code/files specified in the task
2. Create or update the .gibber task file with your results:
   - Set §status:§done if successful
   - Set §status:§verifying-failed if something is incomplete
   - Add §result with a gibber-form summary of what you built
   - Add §risk if there are known limitations
3. For any NEW subtasks you discover during implementation,
   create a new .gibber file in the tasks/ directory with §status:§queued
4. Never write English task descriptions — use gibber forms only for task state
5. English is for code, comments, and human conversation only

TASK CONTEXT:
- Task ID: {§id}
- Goal: {render §goal as English}
- Files to create/modify: {§files}
- Implementation notes: {§notes}
- Tests that must pass: {render §tests}

GIBBER TASK FILE: {path to .gibber file}
Update this file when done.
```

### Step 5 — Launch the sub-agent

Use the Agent tool with:
- `mode: auto` (so it can write files without asking)
- `run_in_background: true` if there are parallel tasks
- Include the full preamble + task context

### Step 6 — Validate on completion

When the sub-agent finishes:

1. **Check files exist**: Every path in `§files` must exist on disk
2. **Check types match**: If `§result` claims `actor`, verify the file contains `actor`
3. **Run tests**: If `§tests` are defined, execute them
4. **Read the .gibber file**: Confirm the sub-agent updated it
5. **If validation fails**: Set `§status:§verifying-failed` with `§risk` explaining what failed

### Step 7 — Report

After all subtasks in a parent `.gibber` are processed, summarize:
- How many `§done`
- How many `§verifying-failed` (and why)
- How many `§queued` remain
- Update the parent `.gibber` status if all children are done

## Executing a parent task with §todo subtasks

When a `.gibber` has `§todo` containing nested `§task` forms:

1. Extract each subtask
2. Check if it already has a standalone `.gibber` file (e.g., `tasks/voice001-1.gibber`)
3. If not, create one from the inline definition
4. Identify which subtasks can run in parallel (no mutual `§depends`)
5. Launch parallel sub-agents for independent subtasks
6. Wait for completion, validate, then launch dependent subtasks

## Sub-Agent Gibber Preamble

This is the standard preamble injected into every sub-agent prompt. It teaches the sub-agent to speak Gibber for task tracking:

```
=== GIBBER PROTOCOL FOR SUB-AGENTS ===

You are working in a Gibber-tracked project. Gibber is a compact symbolic
format for AI task files. You do NOT need to learn the full spec — just
follow these rules:

WHEN YOU FINISH YOUR WORK:
1. Update the .gibber task file you were given
2. Set §status:§done (or §verifying-failed if incomplete)
3. Add §result with what you built, using this format:

   §result:(§created §ClassName §type
     §with:[§method1 §method2 §method3]
     §any §other §relevant §details)

4. If you discover issues, add:
   §risk:["description of issue"]

5. If you find new work needed, create a NEW .gibber file:
   ---
   id: PARENT_ID.N
   gibber_dict: meta/v2
   ---
   (§task §id:PARENT_ID.N §status:§queued §owner:§ai
     §goal:(§what §needs §to §be §done)
     §notes:"English details here")

RULES:
- Task files are ALWAYS .gibber format, never English markdown
- Code files are ALWAYS normal (Swift, Rust, Python, etc.)
- Comments in code are English
- §status values: §queued §wip §done §verifying-failed §blocked
- Use § prefix for all gibber symbols
- Keep §result compact — one form, not paragraphs
=== END GIBBER PROTOCOL ===
```

## Example: Executing voice-loop.gibber

```
1. Read tasks/voice-loop.gibber
2. Extract 9 subtasks from §todo
3. Find standalone .gibber files: voice001-1.gibber through voice001-6.gibber
4. Check statuses: 1,2,4,5,6 are §done. 3 is §verifying-failed.
5. Subtasks 7,8,9 are §queued with no standalone files yet — create them
6. 7 depends on 1-6 (STT+TTS). 3 is failed — flag as blocked or fix first
7. Launch fix for voice001-3, then 7,8,9 in sequence
8. Validate each on completion
9. Update voice-loop.gibber parent status
```

## Validation checklist

For each completed subtask, verify:
- [ ] §files paths exist on disk
- [ ] Type claims match (actor/class/enum/struct)
- [ ] Public methods/properties claimed in §result exist in code
- [ ] Implementation is substantive (not stubs returning nil)
- [ ] §status updated in .gibber file
- [ ] §result present with accurate summary
