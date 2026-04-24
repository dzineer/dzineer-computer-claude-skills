---
name: llm-porter
description: Specialized skill for porting LLM provider implementations from TypeScript to Rust, handling SSE streaming, tool-call parsing, and provider-specific response formats.
---

## Core Logic

### 1. Provider Trait Implementation
Each TS LLM provider (Anthropic, OpenAI, Gemini, Groq, Ollama, OpenRouter) implements `LLMProvider`.
In Rust, each becomes a struct implementing the `LLMProvider` trait with `#[async_trait]`.

### 2. SSE Stream Porting Pattern
Every provider has an `async *stream()` method that:
1. Builds an HTTP request with `reqwest`
2. Sends it and gets a streaming response
3. Parses SSE `text/event-stream` lines
4. Yields `LLMStreamEvent` variants (text_delta, tool_call, done, error)

**Rust pattern:**
```rust
use async_stream::stream;
use tokio_stream::Stream;

fn stream(&self, messages: Vec<LLMMessage>, opts: LLMOptions)
    -> Pin<Box<dyn Stream<Item = Result<LLMStreamEvent>> + Send>>
{
    let client = self.client.clone();
    Box::pin(stream! {
        let response = client.post(&url).json(&body).send().await?;
        let mut bytes_stream = response.bytes_stream();
        let mut buffer = String::new();

        while let Some(chunk) = bytes_stream.next().await {
            buffer.push_str(&String::from_utf8_lossy(&chunk?));
            // Parse SSE lines from buffer
            while let Some(line_end) = buffer.find('\n') {
                let line = buffer[..line_end].to_string();
                buffer = buffer[line_end + 1..].to_string();
                if let Some(event) = parse_sse_line(&line) {
                    yield Ok(event);
                }
            }
        }
    })
}
```

### 3. Provider-Specific SSE Formats
- **Anthropic**: `message_start`, `content_block_start`, `content_block_delta` (text_delta + input_json_delta), `message_delta`, `message_stop`
- **OpenAI/Groq/OpenRouter**: `data: {"choices":[{"delta":{"content":"..."}}]}`, tool calls as `function` in delta
- **Gemini**: Non-SSE streaming JSON chunks with `candidates[].content.parts[]`
- **Ollama**: Newline-delimited JSON `{"message":{"content":"..."},"done":false}`

### 4. Tool Call Extraction
Tool calls arrive as partial JSON across multiple SSE events. Must accumulate `input_json_delta` chunks and parse the complete JSON only when the content block ends.

### 5. Retry Logic
Port `LLMManager.isRetryableError()` — classify HTTP 429 (rate limit), 529 (overloaded), 500+ (server error) as retryable. Use exponential backoff.

## Usage
"Use llm-porter to port the Anthropic provider from `src/llm/anthropic.ts` to `crates/jarvis-llm/src/providers/anthropic.rs`."

## TDD Requirement
Before implementing any provider:
1. Record real SSE responses as fixture files
2. Write replay tests that feed fixtures into the parser
3. Assert correct `LLMStreamEvent` sequence
4. Then implement the provider
