---
name: test-driven-development
description: Specialized skill for language porting and feature implementation using a strict Red-Green-Refactor cycle.
license: MIT
metadata:
  workflow: red-green-refactor
  priority: accuracy-over-speed
---

## What I Do
I guide the agent through a disciplined Test-Driven Development (TDD) cycle. I am specifically optimized for **language porting**, ensuring that logic is preserved by validating it against test suites in the target language before implementation begins.

## When To Use Me
- **Porting Code:** When migrating logic from one language (e.g., Python) to another (e.g., Go/Rust).
- **Bug Fixing:** When a specific logic error needs a regression test before the fix.
- **Refactoring:** When you need to ensure "functional parity" after changing internals.

## My Workflow (The Porting Protocol)

### Phase 1: Red (Discovery & Tests)
1. **Analyze Source:** I read the source file and identify all "Happy Paths," "Edge Cases," and "Error States."
2. **Setup Test Harness:** I initialize the test framework in the target language (e.g., Pytest, Jest, Vitest, Go Test).
3. **Write Failing Tests:** I write the equivalent tests in the target language. These **must fail** initially because the implementation does not yet exist.
   - *Requirement:* Run the test command and verify a `404` or `Method Not Found` error.

### Phase 2: Green (Implementation)
1. **Minimal Logic:** I write the minimum amount of code in the target language to make the tests pass.
2. **Iterative Fix:** If the compiler or test runner returns an error, I fix it and re-run immediately without asking for permission.
3. **Verification:** I do not proceed until all tests are **Green**.

### Phase 3: Refactor (Idiomatic Polish)
1. **Cleanup:** I refactor the code to ensure it follows the target language's idioms (e.g., using Go interfaces instead of Java-style classes).
2. **Final Pass:** I run the tests one last time to ensure refactoring didn't break the logic.

## Usage Instructions
To trigger this skill for your porting task, use the following prompt:
> "Use the test-driven-development skill to port `src/logic.py` to `pkg/logic.go`. Start with Phase 1 by writing the failing tests in Go first."

## Constraints
- Do NOT write implementation code until the tests have been run and seen to fail.
- Do NOT ignore linter errors; treat them as test failures.
- Always check `CLAUDE.md` for project-specific testing patterns before starting.
