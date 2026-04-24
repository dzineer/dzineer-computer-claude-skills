---
name: trait-interface-gen
description: Ports TypeScript Class hierarchies and Interface contracts into Rust Traits and impl blocks.
---

## Core Logic
1. **Contract Mapping**:
   - TS Interface with methods -> Rust `pub trait`.
   - TS Abstract Class -> Rust `pub trait` with default implementations where possible.
2. **Async Trait Support**:
   - Use the `#[async_trait]` macro (from the `async-trait` crate) for any trait containing `async fn`.
3. **Dependency Injection**:
   - Convert TS constructor dependencies into Rust struct fields (e.g., `db: Arc<Database>`).
4. **Error Return**:
   - Every trait method that can fail MUST return `Result<T, JarvisError>`.
5. **Generic Handling**:
   - Map TS Generics `<T>` to Rust Trait Generics or Associated Types depending on usage patterns in the source.

## Usage
"Use trait-interface-gen to port the `LLMProvider` interface from `src/llm/types.ts` to a Rust trait in `crates/jarvis-llm/src/trait.rs`."
