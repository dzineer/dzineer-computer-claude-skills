# Memory Dump - cmux-ai project - 2026-03-18

## Project Overview

Building a customized version of **cmux** (a terminal multiplexer app for macOS based on Ghostty) with integrated Claude Code AI support. The project is at `/Users/dzineer/Clients/Dzineer/Projects/o/cmux-build/`.

The repo was cloned from `https://github.com/dzineer/cmux-build.git` but the `.git` directory appears to be missing now. Need to reinitialize git and push to a new private repo called `cmux-ai` on the user's GitHub (dzineer).

## Architecture

- **macOS SwiftUI app** built with Xcode 26.3 (Swift 6.1+)
- **Ghostty** terminal emulator as a submodule (fork at manaflow-ai/ghostty)
- **Bonsplit** split pane library as a submodule (vendor/bonsplit)
- **GhosttyKit.xcframework** built via zig + xcodebuild
- Build system: Xcode project `GhosttyTabs.xcodeproj`, scheme `cmux`
- Development: `./scripts/reload.sh --tag <tag>` to build and launch debug app

## Key Files Modified

### 1. Sources/ContentView.swift
- Line ~10: Added `claudeLaunchCommand(args:)` free function - returns "claude" or "claude <args>"
- Line ~10172: Changed "THIS IS A DEV BUILD" to "Dzineer AISHELL"
- Line ~9031: `SidebarFooterButtons` - added `@EnvironmentObject var tabManager: TabManager`, `Spacer()`, and `SidebarClaudeButton`
- Line ~9050: `SidebarClaudeButton` struct - orange ClaudeLogo image with rotation animation, popover with two options
- Line ~10106: `ArrowlessPopoverAnchor` is private to this file (caused build error when used in UpdateTitlebarAccessory.swift)

### 2. Sources/Update/UpdateTitlebarAccessory.swift
- Line ~238: `TitlebarControlsView` - added `var onLaunchClaude: ((String) -> Void)?` property
- Line ~320: `controlsGroup` - added `TitlebarClaudeButton` as first button (conditional on onLaunchClaude != nil)
- Line ~725: Second call site - added `launchClaude` closure that creates workspace with claude command
- End of file: `TitlebarClaudeButton` struct using `.popover` (NOT ArrowlessPopoverAnchor)

### 3. vendor/bonsplit/Sources/Bonsplit/Internal/Views/TabBarView.swift
- Line ~467: Added Claude button as first button in `splitButtons` HStack
- Uses `Text("\u{273B}")` (teardrop-spoked asterisk) in orange, font size 14
- Calls `controller.requestNewTab(kind: "claude", inPane: pane.id)`

### 4. Sources/Workspace.swift
- Line ~9722: `splitTabBar(_:didRequestNewTab:inPane:)` - added "claude" case
- Gets `currentDirectory`, calls `owningTabManager?.addWorkspace(workingDirectory:initialTerminalCommand: claudeLaunchCommand(args: ""))`

### 5. Resources/bin/claude (shell wrapper)
- Modified from `exec` to non-exec so we can capture exit
- Added: Check for `resume.md` in current directory - if exists, read session ID and use `--resume`
- Added: After Claude exits, save session ID to `resume.md` (just the UUID, not full command)
- Added: Set terminal title to `Claude [shortID]` while running, `Claude [shortID] (exited)` after exit
- resume.md contains just the session UUID (e.g., `5687d8e4-2617-4af0-91bf-66eac68b0c16`)

### 6. Resources/Localizable.xcstrings
- Line ~1001: Changed "THIS IS A DEV BUILD" to "Dzineer AISHELL"

### 7. Assets.xcassets/ClaudeLogo.imageset/
- New: `claude-logo.svg` - Claude sparkle/asterisk SVG (first instance from the full logo SVG the user provided)
- New: `Contents.json` - template rendering, preserves vector representation
- Used by SidebarClaudeButton and TitlebarClaudeButton (but NOT accessible from bonsplit package)

## Build Commands

```bash
# Setup (first time)
./scripts/setup.sh

# Build and launch debug
./scripts/reload.sh --tag first-run

# Build only (verify compilation)
xcodebuild -project GhosttyTabs.xcodeproj -scheme cmux -configuration Debug -destination 'platform=macOS' -derivedDataPath /tmp/cmux-claude-btn build

# GhosttyKit rebuild
cd ghostty && zig build -Demit-xcframework=true -Dxcframework-target=universal -Doptimize=ReleaseFast
```

## Environment

- macOS Sequoia (Darwin 24.6.0), ARM64
- Xcode 26.3 (Build 17C529), Swift 6.1+
- Zig 0.15.2 (installed via homebrew)
- GhosttyKit cached at ~/.cache/cmux/ghosttykit/<sha>/

## User Preferences

- User is dzineer, GitHub username: dzineer
- Wants the project pushed as private repo "cmux-ai"
- Orange color for Claude icon
- No emojis in codebase
- Prefers modular code
- Uses `--dangerously-skip-permissions` option for Claude

## Known Issues

1. `.git` directory missing from cmux-build - need to reinitialize
2. Pane button uses Unicode character (looks like Gemini to user) - can't use ClaudeLogo asset from bonsplit package
3. The bonsplit submodule was modified directly - per CLAUDE.md, submodule changes should be pushed to fork first
