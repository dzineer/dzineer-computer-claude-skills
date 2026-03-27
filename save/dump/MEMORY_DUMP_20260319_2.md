# Memory Dump - cmux-ai project - 2026-03-19 (session 2, continued)

## What happened this session (continuation)

### Sidebar-offset fix for background overlay

User noticed the background image overlay was covering the **entire window** including the sidebar (left panel). Fixed by:

1. Captured `sidebarWidth` in the WindowAccessor closure
2. Added `sidebarWidth` parameter to `TerminalBackgroundOverlay.install(on:sidebarWidth:)`
3. Added `terminalContentFrame()` helper that calculates the terminal area frame:
   - x = parentFrame.origin.x + sidebarWidth
   - width = parentFrame.width - sidebarWidth
4. Resize/move notification handlers also use `terminalContentFrame()` to keep overlay aligned

**Key code locations:**
- WindowAccessor closure: `~line 3083` - captures `sidebarWidth` and passes to install
- `TerminalBackgroundOverlay.install(on:sidebarWidth:)`: `~line 9763`
- `terminalContentFrame()`: `~line 9827`
- `sidebarWidth` @State: `line 1668`, default 200

### Current state of TerminalBackgroundOverlay (ContentView.swift ~line 9760)

```swift
final class TerminalBackgroundOverlay {
    private static var installedWindows = Set<ObjectIdentifier>()

    static func install(on parentWindow: NSWindow, sidebarWidth: CGFloat) {
        // Load from ~/.config/cmux/terminal-bg.png
        // Create borderless transparent child NSWindow
        // CALayer with .resizeAspectFill, opacity 0.35
        // Offset by sidebarWidth to only cover terminal area
        // Auto-sync on resize/move/close
    }

    private static func terminalContentFrame(parentWindow: NSWindow, sidebarWidth: CGFloat) -> NSRect {
        let parentFrame = parentWindow.frame
        return NSRect(
            x: parentFrame.origin.x + sidebarWidth,
            y: parentFrame.origin.y,
            width: parentFrame.width - sidebarWidth,
            height: parentFrame.height
        )
    }
}
```

### Important architectural notes

1. **Ghostty terminal surfaces are AppKit NSView portals** - they paint ABOVE SwiftUI views regardless of zIndex
2. **Only child NSWindow overlay works** for putting content on top of terminal
3. **NSImageView does NOT support true aspect-fill** - must use CALayer.contents with .resizeAspectFill
4. **Asset catalog caching** - extremely aggressive, switched to filesystem loading from `~/.config/cmux/terminal-bg.png`
5. **sidebarWidth** is a @State var (default 200), user can resize it via drag

### Git status
- Latest pushed commit: `02e19d8` - "Add background image overlay, usage panel layering, and sci-fi renderer"
- Uncommitted: sidebar-offset fix for TerminalBackgroundOverlay

### Build commands
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/o/cmux-build
xcodebuild -project GhosttyTabs.xcodeproj -scheme cmux -configuration Debug -destination 'platform=macOS' -derivedDataPath /tmp/cmux-layers build
./scripts/reload.sh --tag layers
```

### File locations
- Background image: `~/.config/cmux/terminal-bg.png`
- TerminalBackgroundOverlay class: ContentView.swift ~line 9760
- WindowAccessor install call: ContentView.swift ~line 3152
- sidebarWidth state: ContentView.swift line 1668
- SciFiRenderer (unused): ContentView.swift ~line 9840+
- ClaudeUsagePanel: ContentView.swift ~line 10050+
- ClaudeUsageStatusBar: ContentView.swift ~line 10120+
