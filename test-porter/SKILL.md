---
name: test-porter
description: Converts bun:test suites to Rust #[tokio::test] suites.
---

## Core Logic
1. **Framework**: Use `tokio::test` and `anyhow` for test results.
2. **Matchers**: 
   - `expect(a).toBe(b)` -> `assert_eq!(a, b)`
   - `expect(a).toBeDefined()` -> `assert!(a.is_some())`
3. **Async**: Wrap test logic in `async` blocks.
4. **Mocks**: Replace TS `jest.fn()` mocks with explicit trait implementations or the `mockall` crate.

## Usage
"Use test-porter to create the Rust equivalent of `tests/vault.test.ts` in `crates/jarvis-vault/tests/`."
