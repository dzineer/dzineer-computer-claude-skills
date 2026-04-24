---
name: stream-translator
description: Converts TS Async Generators (async *) to Rust Streams using the async-stream crate.
---

## Core Logic
1. **Dependency**: Use `async_stream::stream!` macro.
2. **Signature**: Return `impl Stream<Item = T>` or `Pin<Box<dyn Stream<Item = T> + Send>>` for public traits.
3. **Yield Mapping**: 
   - TS `yield value` -> Rust `yield value`.
   - TS `yield* stream` -> Rust `for await item in stream { yield item; }`.
4. **Context**: Ensure `CancellationToken` is checked within the loop to mirror Bun's signal handling.

## Usage
"Use stream-translator to port the streaming logic in `src/llm/stream.ts` to Rust."
