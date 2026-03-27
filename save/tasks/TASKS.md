# Tasks
Last synced: 2026-03-19T23:30:00

## In Progress
(none)

## Pending
- [ ] **Test Rust GUI with daemon integration**
  - Build and run the .app bundle, verify Start/Stop buttons call `./va`
  - Verify log tailing works (service logs stream into GUI)
  - Verify status polling detects externally started/stopped services
  - RUN_README.md + BUILD.md created with full test checklist
- [ ] **Install launchd plist for auto-start**
  - `cp scripts/com.voiceassistant.daemon.plist ~/Library/LaunchAgents/`
  - `launchctl load ~/Library/LaunchAgents/com.voiceassistant.daemon.plist`
  - Test auto-restart
- [ ] **Frontend showing wrong character (Alan instead of Amy)**
  - Unresolved from previous sessions
- [ ] **Push latest changes to public repo** (voice-assist-services-control-rs)
- [ ] **Code graph comparison tools** (deferred -- user wanted daemon first)
  - 4 tools: compare_codebases, compare_structures, compare_dependencies, find_similar_entities
  - File: `extensions/core/code_graph/mcp_server.py`
- [ ] **Connect Rust GUI to daemon CLI** (plan exists in mellow-honking-kite.md)
  - services.rs: replace direct spawning with `./va` CLI calls, PID file reading, log tailing
  - app.rs: update DevPanel struct, drain_async_results, poll_status, stop, startup detection
  - Plan fully written, not yet implemented

## Completed (recent)
- [x] **Feature 0A: Daemon Mode -- ALL COMMITTED AND MERGED**
  - [x] PR #51 merged: daemon mode + Rust GUI daemon integration
  - [x] PR #52 merged: watchdog, dynamic paths, improved GUI, BUILD.md, NEW_FEATURES.md
  - [x] daemon.py: multi-service manager + watchdog (`./va watch`)
  - [x] va CLI wrapper: start|stop|restart|status|fg|watch|help
  - [x] launchd plist: reads install_path dynamically
  - [x] bundle-app.sh: simplified (copies config.json as-is)
  - [x] install_path mechanism: va writes, main.rs reads
  - [x] Rust GUI: 4-priority config resolution, dependency support, dark theme
  - [x] BUILD.md, RUN_README.md, NEW_FEATURES.md created
  - [x] Vite PORT env var support added
- [x] Diagnosed "hey amy" not responding issue (dedup filter in App.jsx)
- [x] Identified 4 TTS calls issue -- normal behavior (sentence chunking)
