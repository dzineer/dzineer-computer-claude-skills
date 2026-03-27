# Memory Dump - cmux-ai project - 2026-03-18 (session 3)

## What happened this session

### 1. Usage panel redesign (committed)
- Changed from drawer pushing content to **floating overlay panel** at bottom-right
- Panel: 360px wide, max 400px tall, solid `windowBackgroundColor` at 92% opacity
- Orange border accent, drop shadow, close button header
- Bottom status bar ("Today: X msgs | 3.2M out | N sessions") **always visible**

### 2. Layered terminal architecture (committed)
Refactored `terminalContent` in ContentView.swift to use a ZStack with explicit layers:
- **Layer 0 (zIndex 0)**: `TerminalMediaBackground` - for ambient visuals
- **Layer 1 (zIndex 1)**: `ClaudeUsagePanel` - bottom-right floating panel
- **Layer 2 (zIndex 2)**: Terminal shell content (BonsplitView, workspaces, tabs)
- Status bar as overlay on top of everything

### 3. Removed "Dzineer AISHELL" label
Removed from `SidebarDevFooter` in ContentView.swift (~line 10981). Just shows the footer buttons now.

### 4. Sci-fi background (IN PROGRESS - not yet built/committed)
User asked to port `/Users/dzineer/Clients/Dzineer/Projects/voice-assistant-2.0/frontend/src/components/SciFiBackground.jsx` to SwiftUI.

Replaced the placeholder `TerminalMediaBackground` with a full sci-fi renderer:

**Key components added at ~line 9758:**
- `TerminalMediaBackground` - Uses `TimelineView(.animation(minimumInterval: 1.0/30.0))` + `Canvas` for GPU-accelerated drawing, `.drawingGroup()` for offscreen compositing
- `SciFiRenderer` enum with static `draw()` method containing:
  - **120 stars**: Diamond shapes with 3D tumble rotation (xorshift spin), twinkle via sin(), cross flares on bright stars, wrap-around drifting
  - **8 nebula clouds**: Elliptical radial gradients, drifting with wrap-around, pulsing alpha, blue/purple/teal colors
  - **Subtle grid**: 40px spacing, cyan at 3% opacity
- `SeededRNG` struct: xorshift64-based PRNG for deterministic placement
- `Star` struct: x0, y0, vx, vy, size, phase, brightness, r/g/b, spin, rotAngle0
- `Nebula` struct: x0, y0, vx, vy, radius, rotSpeed, stretch, r/g/b, alpha, phase

**STATUS: Code written but user interrupted before `xcodebuild` could run. May have compilation errors. Need to build and verify.**

## Uncommitted changes in working tree

```
M Sources/ContentView.swift  (sci-fi background + label removal + panel redesign)
```

The label removal and panel redesign changes were committed in a previous commit but the sci-fi background was added after. Need to verify which parts are committed vs uncommitted.

Actually checking git history:
- Commit `08a4b61`: "Add Claude usage tracker with bottom drawer and popover tabs" - pushed
- After that commit: panel redesign (overlay), label removal, layered architecture, sci-fi background - ALL uncommitted

## Key file locations

### ContentView.swift structure (approximate line numbers after all edits):
- Line ~12: `claudeLaunchCommand()`
- Line ~19: `ClaudeSessionInfo` model (has `project` field)
- Line ~50: `ClaudeSessionLoader` - scans all `~/.claude/projects/*/`
- Line ~155: `ClaudeUsageInfo`, `ClaudeUsageModelInfo`, etc.
- Line ~230: `ClaudeUsageLoader` - reads stats-cache.json
- Line ~2317: `terminalContent` - layered ZStack (Layer 0/1/2)
- Line ~9370: `SidebarClaudeButton` - with tabbed popover (Launch/Usage)
- Line ~9595: `ClaudeUsageView` - detailed usage display
- Line ~9755: `TerminalMediaBackground` - sci-fi Canvas renderer
- Line ~9755+: `SciFiRenderer` enum, `SeededRNG` struct
- Line ~9950+: `ClaudeUsagePanel` - floating overlay bottom-right
- Line ~10050+: `ClaudeUsageStatusBar` - always-visible bottom bar
- Line ~10975: `SidebarDevFooter` - label removed

### UpdateTitlebarAccessory.swift:
- Line ~1325: `TitlebarClaudeButton` - with tabbed popover (Launch/Usage), session list

### Resources/bin/:
- `claude` - wrapper with session tracking, hooks, resume.md
- `claude-sessions` - scans ALL projects for session JSONL files
- `claude-usage` - reads stats-cache.json and per-session usage

## Build commands
```bash
xcodebuild -project GhosttyTabs.xcodeproj -scheme cmux -configuration Debug -destination 'platform=macOS' -derivedDataPath /tmp/cmux-usage build
./scripts/reload.sh --tag usage
```

## GitHub
- Repo: https://github.com/dzineer/cmux-ai (private)
- Latest pushed commit: `08a4b61`
- Uncommitted changes: panel redesign, label removal, layered architecture, sci-fi background
