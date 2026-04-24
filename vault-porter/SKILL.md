---
name: vault-porter
description: Ports TypeScript SQLite CRUD modules to Rust using rusqlite.
---

## Core Logic
1. **Pattern**: Use the "Prepared Statement" pattern.
2. **Type Safety**: 
   - Map `rows.map(...)` to a dedicated `FromRow` trait implementation or a closure that maps `rusqlite::Row` to a `jarvis-type` struct.
3. **Error Handling**: Map `sqlite` errors to the project's `JarvisError::Database` variant using `?`.
4. **Connection Management**: Assume a `Connection` or `Pool` is passed in as a reference.

## Usage
"Use vault-porter to migrate `src/vault/modules/facts.ts` to `crates/jarvis-vault/src/facts.rs`."
