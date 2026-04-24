---
name: type-porter
description: Converts TypeScript interfaces/types to Rust structs/enums with Serde derives.
---

## Core Logic
1. **Structural Mapping**: 
   - TS Interface -> Rust `pub struct`
   - TS Union (String literals) -> Rust `pub enum`
   - TS Union (Discriminated) -> Rust `pub enum` with `#[serde(tag = "type")]`
2. **Mandatory Derives**: Every generated type must have:
   `#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]`
3. **Optional Handling**: Convert `prop?: type` to `Option<type>`.
4. **Naming**: Convert `camelCase` fields to `snake_case` using `#[serde(rename_all = "camelCase")]` on the struct to maintain API compatibility.

## Usage
"Use type-porter to convert `src/types/auth.ts` to `crates/jarvis-types/src/auth.rs`."
