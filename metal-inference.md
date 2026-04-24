# Metal-Accelerated ML Inference in Rust (macOS / Apple Silicon)

Use this skill when working on ML inference tasks targeting macOS with Apple Silicon (M-series chips), especially when the project involves Rust-based inference engines, text/speech/vision models, TTS, or audio playback. This reference encodes hard-won compatibility findings and performance patterns as of April 2026.

---

## aha crate (v0.2.5, Apr 2026)

Unified Candle-based inference engine for on-device ML.

### Cargo dependency

```toml
aha = { version = "0.2", features = ["metal"] }
```

### Supported model families

| Domain  | Models                                      |
|---------|---------------------------------------------|
| Text    | Qwen3, Qwen2.5                              |
| Speech  | Whisper, Qwen3-ASR                          |
| Vision  | DeepSeek-OCR, PaddleOCR-VL                  |

### Model loading pattern

- **Lazy init**: load models on first use, not at daemon startup.
- This keeps daemon startup fast and avoids blocking the event loop.

```rust
// Pseudocode pattern
static MODEL: OnceLock<AhaModel> = OnceLock::new();

fn get_model() -> &'static AhaModel {
    MODEL.get_or_init(|| AhaModel::load("qwen3-0.6b", &device).unwrap())
}
```

### Quantization

- FP16 quantization yields sub-100ms inference on M-series chips.
- RAM usage stays under 500MB with FP16.

### Streaming generation

Use aha's async stream API for token-by-token output:

```rust
let stream = model.stream_generate(&prompt, &params).await;
while let Some(token) = stream.next().await {
    // send token to client
}
```

---

## any-tts crate (v0.1.1, Apr 2026)

Text-to-speech with Metal acceleration and multiple backends.

### Cargo dependency

```toml
any-tts = { version = "0.1", features = ["metal"] }
```

### Backends (6 total)

1. **Kokoro** -- lightweight, fast
2. **OmniVoice** -- multi-speaker
3. **Qwen3-TTS** -- LLM-based TTS
4. **VibeVoice** -- reference-audio-conditioned voice cloning
5. **VibeVoice Realtime** -- low-latency streaming variant
6. **Voxtral** -- high-fidelity

### Voice cloning

Use the **VibeVoice** backend with a reference audio clip to clone a voice.

### IMPORTANT

`f5-tts-rs` does **NOT** exist on crates.io. If you encounter references to it, use `any-tts` instead.

---

## rodio (v0.22.2, Mar 2026) -- Audio Playback

The rodio 0.22 release contains breaking API changes. Code written for rodio 0.19-0.21 will not compile.

### Removed types

- `OutputStream` -- removed
- `OutputStreamHandle` -- removed
- `Sink` -- removed

### New API

```rust
use rodio::{DeviceSinkBuilder, MixerDeviceSink, Player};

// Open default audio output
let sink: MixerDeviceSink = DeviceSinkBuilder::open_default_sink();

// Create a player attached to the mixer
let player = Player::connect_new(sink.mixer());

// Play audio
player.append(source);
```

### Source trait changes (v0.22)

| Old name              | New name / type            |
|-----------------------|----------------------------|
| `current_frame_len()` | `current_span_len()`       |
| `u16` channel count   | `ChannelCount = NonZero<u16>` |
| `u32` sample rate     | `SampleRate = NonZero<u32>`   |

---

## Key Pitfalls -- DO NOT Ignore

These are real dependency conflicts discovered through debugging. Always vet crate dependencies before adding them to `Cargo.toml`.

### 1. metal-candle v1.3.0 -- AVOID

`metal-candle` v1.3.0 has a **safetensors version conflict** with aha's `candle-core`. Using both crates in the same project will produce irreconcilable version errors.

**Rule**: Do NOT add `metal-candle` alongside `aha`. The `aha` crate already provides Metal support via its own Candle integration.

### 2. rust-bert v0.23.0 -- AVOID

`rust-bert` v0.23.0 depends on `ort` v1.16.3, which has been **yanked from crates.io**. Cargo will refuse to resolve it.

**Rule**: Do NOT use `rust-bert`. Use `aha` for transformer-based inference instead.

### 3. voice-stream -- AVOID

`voice-stream` transitively pulls in `ort`, which **breaks on Rust 2024 edition** (edition = "2024" in Cargo.toml).

**Rule**: Use `webrtc-vad` for voice activity detection instead of `voice-stream`.

### 4. General dependency hygiene

Before adding any ML crate to a Rust project:

1. Check crates.io for yanked versions in the dependency tree.
2. Verify compatibility with the Rust edition in use (especially 2024).
3. Check for `safetensors` / `candle-core` version conflicts if `aha` is already a dependency.
4. Prefer crates with the `metal` feature flag over CPU-only alternatives.

---

## Performance Patterns Summary

| Pattern                     | Benefit                                  |
|-----------------------------|------------------------------------------|
| Lazy model loading          | Fast daemon startup, load on first call  |
| FP16 quantization           | RAM < 500MB, sub-100ms inference         |
| Metal GPU acceleration      | On-device, zero network latency          |
| Async streaming generation  | Token-by-token output, responsive UX     |
| webrtc-vad over voice-stream | Avoids ort dependency breakage          |
