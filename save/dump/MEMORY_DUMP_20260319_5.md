# Memory Dump -- 2026-03-19 19:15

## Session Context
Continued from previous compacted session. Feature 0A (Daemon Mode) is now fully complete -- all code changes done, not yet committed.

## What Was Done This Session

### 1. Simplified bundle-app.sh
- Removed Python-based `base_dir` override (lines 24-34 old)
- Replaced with simple `cp "$SCRIPT_DIR/config.json" "$APP_DIR/Contents/MacOS/config.json"`
- App now resolves paths at runtime via `~/.voice-assistant/install_path`, no build-time hardcoding
- File: `voice-assist-services-control-rs/bundle-app.sh`

### 2. Added watchdog to daemon.py (Task 0A.5)
- New `watch()` function at line 296
- Monitors services every 5 seconds, checks PID file + process liveness
- Auto-restarts dead services with timestamped logging
- Usage: `./va watch` or `./va watch va-backend`
- Catches KeyboardInterrupt for clean exit
- Added to COMMANDS dict and docstring
- File: `backend/daemon.py`

### 3. Fixed launchd plist (dynamic paths)
- Changed from hardcoded absolute paths to reading `~/.voice-assistant/install_path`
- ProgramArguments now: `/bin/bash -c 'INSTALL_PATH=$(cat "$HOME/.voice-assistant/install_path") && exec "$INSTALL_PATH/va" start'`
- Removed WorkingDirectory (va handles cwd)
- Changed KeepAlive to false (daemon manages its own processes)
- Removed VA_HOST/VA_PORT env vars (daemon.py reads config.json)
- File: `scripts/com.voiceassistant.daemon.plist`

### 4. Created BUILD.md
- Full build guide: prerequisites, binary build, .app bundle, install to /Applications
- Config resolution chain (4 priorities)
- Daemon CLI reference (7 commands including watch)
- launchd install/uninstall instructions
- Watchdog usage
- File locations table
- Quick start from scratch
- File: `voice-assist-services-control-rs/BUILD.md`

### 5. Cargo build verified
- 0 errors, 9 pre-existing warnings
- Binary: `target/release/voice-assist-services-control`

## Used Multi-Agent Approach
- 3 agents ran in parallel for the 3 code changes (bundle-app.sh, daemon.py, plist)
- All completed successfully

## Current File State

### bundle-app.sh (lines 24-31)
```bash
# Copy config.json as-is — the app resolves paths at runtime via ~/.voice-assistant/install_path
if [ -f "$SCRIPT_DIR/config.json" ]; then
    cp "$SCRIPT_DIR/config.json" "$APP_DIR/Contents/MacOS/config.json"
    echo "Copied config.json"
else
    echo "WARNING: No config.json found at $SCRIPT_DIR/config.json"
    echo "The app will use built-in defaults."
fi
```

### daemon.py watch function (lines 296-318)
```python
def watch(service_filter=None):
    """Monitor services and auto-restart if they die."""
    import datetime
    _ensure_state_dir()
    print("Watchdog started — monitoring services (Ctrl+C to stop)")
    try:
        while True:
            services = _load_services()
            for svc in services:
                name = svc["name"]
                if service_filter and name != service_filter:
                    continue
                pid = _read_pid(name)
                pf = _pid_file(name)
                if pf.exists() and not _is_running(pid):
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"  [{ts}] {name}: died (was PID {pid}), restarting...")
                    pf.unlink(missing_ok=True)
                    _start_one(svc)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nWatchdog stopped")
```

### daemon.py COMMANDS dict (line 321-328)
```python
COMMANDS = {
    "start": start,
    "stop": stop,
    "restart": restart,
    "status": status,
    "fg": fg,
    "watch": watch,
}
```

### com.voiceassistant.daemon.plist
- Uses `/bin/bash -c` with `cat "$HOME/.voice-assistant/install_path"` to find va script
- KeepAlive: false
- No hardcoded project paths

### .app bundle output path
- `$PROJECT_ROOT/VoiceAssistServicesControl.app` (project root, NOT inside target/)
- PROJECT_ROOT = parent of voice-assist-services-control-rs/

## Git State
- Branch: `main`
- ALL UNCOMMITTED -- needs commit + push
- Modified files:
  - `backend/daemon.py` (watchdog + help text fix)
  - `va` (install_path writing)
  - `voice-assist-services-control-rs/src/main.rs` (install_path resolution)
  - `voice-assist-services-control-rs/bundle-app.sh` (simplified)
  - `voice-assist-services-control-rs/src/config.rs` (prior changes)
  - `voice-assist-services-control-rs/src/theme.rs` (prior changes)
  - `voice-assist-services-control-rs/config.json` (prior changes)
  - `scripts/com.voiceassistant.daemon.plist` (dynamic paths)
  - `CLAUDE.md` (prior changes)
  - `frontend/vite.config.js` (prior changes)
- New/untracked files:
  - `voice-assist-services-control-rs/BUILD.md`
  - `voice-assist-services-control-rs/RUN_README.md`
  - `NEW_FEATURES.md`
  - `voice-assist-services-control/` (built binary directory?)

## Environment
- macOS Darwin 24.6.0
- Backend venv: /Users/dzineer/Clients/Dzineer/Projects/voice-assistant-2.0/.venv (Python 3.11)
- Rust: cargo build --release succeeds (0 errors)
- LM Studio: running with qwen3.5-35b-a3b model on port 1234

## User Preferences
- Author: Frank Decker frank@dzineer.com, no co-authoring on commits
- Wants .app to work from /Applications without hardcoded paths
- Uses `~/.voice-assistant/` as the standard state directory
- Prefers multi-agent parallel execution for multiple tasks

## Feature 0A Status: COMPLETE (all code)
All 5 tasks done:
1. daemon.py multi-service manager -- done (PR #51)
2. va CLI wrapper -- done (PR #51)
3. launchd plist -- done (fixed dynamic paths this session)
4. /api/health endpoint -- done (PR #51)
5. Watchdog auto-restart -- done (added this session)

Plus supporting work:
- install_path mechanism -- done
- bundle-app.sh simplified -- done
- BUILD.md created -- done
- RUN_README.md created -- done (previous session)

## Next Steps
1. Commit all changes (use /git-up skill)
2. Test Rust GUI end-to-end with daemon
3. Install launchd plist
4. Move to Feature 0B or next feature from NEW_FEATURES.md
