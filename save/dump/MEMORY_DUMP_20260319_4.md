# Memory Dump - cmux-ai/VibeAi OS project - 2026-03-19 (session 6)

## What happened this session

### 1. Unified Task System
Replaced per-session TASKS_*.md snapshots with single living TASKS.md.

**New files:**
- `~/.claude/scripts/sync-tasks.py` — Stop hook, parses JSONL for TaskCreate/TaskUpdate, writes to TASKS.md
- `~/.claude/scripts/restore-tasks.py` — UserPromptSubmit hook, injects active tasks on session start
- `~/.claude/scripts/archive-tasks.py` — One-time migration, moved 7 old snapshots to archive/

**Modified files:**
- `~/.claude/settings.json` — Added both hooks
- `~/.claude/scripts/rag/config.py` — Fixed paths: skills/dump → skills/save/dump, skills/tasks → skills/save/tasks
- `~/.claude/scripts/rag/ingester.py` — Updated glob for TASKS.md + archive/
- `~/.claude/skills/save/SKILL.md` — /save updates TASKS.md in-place
- MEMORY.md — Simplified task references

### 2. Task Panel (NSWindow Overlay)
**Critical lesson: ALL SwiftUI overlays are invisible behind Ghostty terminal.** Not just zIndex — even `.overlay(alignment: .bottom)`. Only sidebar, titlebar, and tab bar are visible. Must use child NSWindow.

**Implementation:**
- `TaskPanelOverlay` class — child NSWindow, hosts SwiftUI via NSHostingView
- `TaskPanelOverlay.TaskPanelContent` — SwiftUI view with task list
- `SessionTaskLoader` — parses JSONL for task tool calls
- `SessionTaskInfo` — task model struct
- Toggle: cyan checklist icon in sidebar footer (SidebarFooterButtons)
- Installed from WindowAccessor closure alongside TerminalBackgroundOverlay

**JSONL format for tasks:**
- Tool calls: `{type:"assistant", message:{content:[{type:"tool_use", name:"TaskCreate", input:{subject,description,activeForm}}]}}`
- Results: `{type:"user", message:{content:[{type:"tool_result", tool_use_id:"...", content:"Task #1 created successfully: ..."}]}}`
- NOT `{type:"tool_result"}` at top level — this was the parser bug

### 3. Session Loading Optimization
- Preload at window startup (windowSessionLoader in ContentView onAppear)
- Shared loader threaded through: ContentView → VerticalTabsSidebar → SidebarFooter → SidebarDevFooter → SidebarFooterButtons → SidebarClaudeButton
- Cache: `loadSessions(force:false)` skips if already loaded
- Fast scan: 8KB per file, mtime sort, top 20 only

### 4. Session Resume Fix
- Added `; exec $SHELL` so terminal doesn't close when Claude exits
- Added `resolvedCwd`/`decodedProjectPath` to ClaudeSessionInfo
- Added `projectDirEncoded` field

### 5. App Renamed to "VibeAi OS"
- project.pbxproj: PRODUCT_NAME = "VibeAi OS"
- reload.sh: BASE_APP_NAME/APP_NAME = "VibeAi OS", tag NOT appended

## Key file locations (ContentView.swift)
- TaskPanelOverlay (NSWindow class): ~line 9960
- SessionTaskLoader: ~line 10490
- SessionTaskInfo: ~line 10370
- Task toggle in SidebarFooterButtons: ~line 9445
- ClaudeSessionInfo with resolvedCwd: line 21
- fetchSessionsDirect (optimized): line 105
- windowSessionLoader/windowTaskLoader: line 1745
- TaskPanelOverlay.install in WindowAccessor: ~line 3260

## Build
```bash
cd /Users/dzineer/Clients/Dzineer/Projects/o/cmux-build
xcodebuild -project GhosttyTabs.xcodeproj -scheme cmux -configuration Debug -destination 'platform=macOS' -derivedDataPath /tmp/cmux-tasks build
./scripts/reload.sh --tag tasks
```
