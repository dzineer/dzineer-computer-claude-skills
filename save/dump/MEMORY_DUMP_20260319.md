# Memory Dump - cmux-ai project - 2026-03-19

## What happened this session

### 1. Background image overlay (the main task)

Implemented a terminal background image system after many failed approaches.

**Failed approaches:**
1. **SwiftUI ZStack with TerminalMediaBackground at zIndex(0)**: Ghostty terminal surfaces are rendered via AppKit NSView portals which paint ABOVE SwiftUI views regardless of zIndex.
2. **NSImageView injected into NSWindow contentView (behind)**: Terminal Metal surface is opaque, covers everything beneath it.
3. **SwiftUI overlay at higher zIndex**: Same problem - AppKit portals sit above SwiftUI.
4. **Ghostty background-opacity hack**: Changed default from 1.0 to 0.85 in both GhosttyConfig.swift and GhosttyTerminalView.swift, also tried capping opacity after `ghostty_config_get` reads from Zig config. The Zig renderer fills its Metal texture with background color - even with opacity changes the SwiftUI layer behind wasn't visible.
5. **Asset catalog image (TerminalBackground.imageset)**: Suffered from aggressive caching - old images kept showing despite replacing the file and clearing .car files.

**Working approach: Child NSWindow overlay**
- `TerminalBackgroundOverlay` class in ContentView.swift (~line 9758)
- Creates a borderless transparent NSWindow as a child of the main window (`.above` ordering)
- `ignoresMouseEvents = true` so clicks pass through to terminal
- Image loaded from **`~/.config/cmux/terminal-bg.png`** (filesystem, not asset catalog)
- Uses `CALayer.contents` with `.resizeAspectFill` for proper aspect-fill (NSImageView's scaling modes don't do true aspect-fill)
- 35% opacity via `layer.opacity = 0.35`
- Full window coverage (was originally right-half only, user wanted full window)
- Auto-syncs frame with parent via `NSWindow.didResizeNotification` and `didMoveNotification`
- Tracked via `installedWindows` Set to avoid double-install
- Cleaned up via `willCloseNotification`

### 2. Usage panel layering fix

- Moved `ClaudeUsagePanel` from zIndex(1) to zIndex(1) ABOVE terminal (zIndex 0)
- Previously was below terminal and invisible
- Note: SwiftUI zIndex only works between SwiftUI siblings, not for AppKit portal views
- The usage panel IS SwiftUI so it respects zIndex relative to other SwiftUI content
- But the terminal portals still paint above it — this may still need testing

### 3. Reverted changes

- `GhosttyConfig.swift`: backgroundOpacity back to `1.0` (was changed to 0.85)
- `GhosttyTerminalView.swift`: defaultBackgroundOpacity back to `1.0` (was changed to 0.85)
- Removed opacity cap code (`if opacity > 0.85 { opacity = 0.85 }`)
- Removed NSWindow background image injection code
- Removed `makeViewHierarchyTransparent` skipTag parameter

## Key technical lessons

1. **Ghostty terminal surfaces are AppKit NSView portals** - they render via Metal CALayer and sit ABOVE SwiftUI views in the compositing order regardless of zIndex
2. **The only way to overlay something on top of the terminal** is via a child NSWindow (AppKit level) or by modifying the Ghostty renderer itself
3. **NSImageView does NOT support true aspect-fill** - `.scaleProportionallyUpOrDown` is aspect-fit (letterbox). For aspect-fill, use `CALayer.contents` with `.contentsGravity = .resizeAspectFill`
4. **Xcode asset catalog caching is aggressive** - even deleting .car files doesn't always clear it. Loading from filesystem (`NSImage(contentsOfFile:)`) is more reliable for frequently-changed images
5. **`ghostty_config_get` reads from Zig-side config** which defaults to `background-opacity: 1.0`, overriding any Swift-side defaults

## File changes (uncommitted)

### Sources/ContentView.swift
- `terminalContent` (~line 2317): Simplified ZStack - terminal at zIndex(0), usage panel at zIndex(1)
- `TerminalBackgroundOverlay` class (~line 9758): Child NSWindow overlay system
- `TerminalMediaBackground` struct: Still exists but UNUSED (was replaced by child window approach). Contains sci-fi Canvas renderer code.
- `SciFiRenderer` enum, `SeededRNG` struct: Still exist but UNUSED
- `installTerminalBackgroundImage` function: REMOVED
- `WindowAccessor` block calls `TerminalBackgroundOverlay.install(on: window)`

### Sources/GhosttyTerminalView.swift
- No net changes (opacity changes were reverted)

### Sources/GhosttyConfig.swift
- No net changes (opacity changes were reverted)

### Assets.xcassets/TerminalBackground.imageset/
- Created but now UNUSED (image loads from ~/.config/cmux/ instead)
- Contains terminal-bg.png and Contents.json

### ~/.config/cmux/terminal-bg.png
- Background image file loaded at runtime
- Currently: fotor_2026-03-19_01-09-45.png (cyan AI avatar, 3072x1929)
- User can replace this file to change background

## Build commands
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/o/cmux-build
xcodebuild -project GhosttyTabs.xcodeproj -scheme cmux -configuration Debug -destination 'platform=macOS' -derivedDataPath /tmp/cmux-layers build
./scripts/reload.sh --tag layers
```

## Disk space note
- Disk was nearly full (~172MB free), cleaned up old /tmp/cmux-* caches (sessions2, claude-btn, layers2 = ~10GB)
- Current free: ~8GB

## Current state
- App runs with background image overlay working
- Image covers full window at 35% opacity with aspect-fill
- All changes uncommitted
- Unused code to clean up: SciFiRenderer, SeededRNG, TerminalMediaBackground, TerminalBackground.imageset
