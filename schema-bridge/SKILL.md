---
name: schema-bridge
description: Validates and ports SQL schema definitions from TS to Rust, ensuring data-level parity.
---

## Core Logic
1. **Schema Extraction**:
   - Parse `src/vault/schema.ts` to identify table structures, constraints, and indices.
   - Map TS `sqlite` types (`TEXT`, `INTEGER`, `BLOB`) to their `rusqlite` equivalents.
2. **Parity Validation**:
   - Generate a `schema_parity_test.rs` that attempts to open an existing `brain.db` created by the Bun version.
   - Verify that `SELECT *` from every table maps correctly to the new Rust structs without serialization errors.
3. **Migration Prevention**: 
   - Prohibit the creation of NEW columns or tables during the porting phase. 
   - Rule: "If it exists in Bun, it must look identical in Rust. No 'cleanup' allowed until Phase 9."
4. **BLOB Handling**:
   - Ensure `Uint8Array` in TS is mapped to `Vec<u8>` in Rust to prevent encoding corruption of vector embeddings or keys.

## Usage
"Use schema-bridge to compare `src/vault/schema.ts` with my new `crates/jarvis-vault/src/schema.rs`. Report any field mismatches or type-width risks."
