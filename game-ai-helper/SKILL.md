---
name: game-ai-helper
description: >
  Launch the real-time Game AI Helper that captures your screen or camera
  and provides tactical coaching advice using Claude Vision. Use when the
  user wants to start game coaching, configure game profiles, or get help
  with the game AI assistant.
user-invocable: true
---

# Game AI Helper - Real-time Game Coach

Captures your screen or camera feed and uses Claude Vision to provide real-time tactical advice while you play games.

## When to Use

- User asks to start game coaching / game AI helper
- User wants real-time game advice or tactical coaching
- User asks about game AI profiles or configuration

## Quick Start

The project lives at: `/Users/dzineer/Clients/Dzineer/Projects/game-ai-helper`

### Launch with defaults (screen capture, generic profile, TTS on):
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/game-ai-helper && python3 -m game_ai_helper
```

### Launch with a specific game profile:
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/game-ai-helper && python3 -m game_ai_helper --profile fps
```

### Launch with camera/OBS virtual camera:
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/game-ai-helper && python3 -m game_ai_helper --mode camera --camera-index 0
```

### Launch with custom profile:
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/game-ai-helper && python3 -m game_ai_helper --custom-profile profiles/example_custom.json
```

## Available Profiles

| Profile | Best For | Analysis Interval |
|---------|----------|-------------------|
| `generic` | Any game | 3.0s |
| `fps` | Valorant, CS2, Apex | 2.0s |
| `rts` | StarCraft, AoE | 4.0s |
| `moba` | LoL, Dota 2 | 3.0s |
| `fighting` | Street Fighter, Tekken | 2.0s |
| `battle_royale` | Fortnite, PUBG, Apex | 2.5s |

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--profile`, `-p` | Built-in game profile | `generic` |
| `--custom-profile` | Path to custom JSON profile | - |
| `--mode`, `-m` | `screen` or `camera` | `screen` |
| `--camera-index` | Camera device index | `0` |
| `--monitor` | Monitor index (1=primary) | `1` |
| `--model` | Claude model ID | `claude-haiku-4-5-20251001` |
| `--interval` | Override analysis interval (seconds) | profile default |
| `--no-tts` | Disable voice output | TTS on |
| `--fps` | Frame capture rate | `5` |
| `--list-profiles` | Show available profiles | - |

## Creating Custom Profiles

Create a JSON file in `profiles/`:

```json
{
  "name": "my-game",
  "prompt": "You are a coach for MyGame. Look for: <specific elements>. Give 1-2 sentence tactical advice.",
  "analysis_interval": 2.5,
  "capture_width": 1280,
  "capture_height": 720,
  "jpeg_quality": 65
}
```

## Architecture

```
Screen/Camera -> Capture Thread (mss/cv2) -> Frame Queue
  -> Frame Diff (skip unchanged) -> JPEG compress
  -> Claude Haiku Vision API (with conversation history)
  -> Console print + TTS voice callout
```

## Requirements

Needs: `ANTHROPIC_API_KEY` env var set. Install deps with:
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/game-ai-helper && pip3 install -r requirements.txt
```

macOS screen capture requires Screen Recording permission for the terminal app.

## Troubleshooting

- **"Cannot open camera"**: Try different `--camera-index` values (0, 1, 2)
- **No TTS sound**: Use `--no-tts` for text-only mode, or install `pyobjc` for macOS TTS
- **Slow analysis**: Use `--model claude-haiku-4-5-20251001` (fastest) or increase `--interval`
- **Screen recording denied**: Grant Screen Recording permission in System Preferences > Privacy
