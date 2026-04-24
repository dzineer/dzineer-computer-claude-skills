# macOS Headless Daemon in Rust (2026)

Use this skill when building persistent background daemons on macOS with tray icons, global hotkeys, screen capture, and audio. Covers threading requirements, permissions, and lifecycle management.

## daemon-base (v0.1.1, Mar 2025) - Lifecycle Management

```toml
daemon-base = "0.1"
```

- Cross-platform: Linux, macOS, Windows
- Lifecycle: `Daemon::new()`, `.start()`, `.stop()`, `.start_async()`
- Callbacks: `on_start()`, `on_shutdown()` for graceful cleanup
- JSON config: `DaemonConfig::load("config.json")`
- State persistence across restarts

## tray-icon (v0.19+) - Menu Bar Icon

```toml
tray-icon = "0.19"
```

**CRITICAL: Must run on main thread on macOS.**

```rust
let menu = Menu::new();
menu.append(&MenuItem::new("Status", false, None))?;
menu.append(&PredefinedMenuItem::separator())?;
menu.append(&quit_item)?;

let tray = TrayIconBuilder::new()
    .with_tooltip("App Name")
    .with_menu(Box::new(menu))
    .with_title("AB")  // Menu bar text on macOS
    .build()?;

// Poll events (main thread loop)
if let Ok(event) = MenuEvent::receiver().try_recv() {
    if event.id() == quit_item.id() { /* handle */ }
}
```

## global-hotkey (v0.7.0, May 2025) - System Hotkeys

```toml
global-hotkey = "0.7"
```

**CRITICAL: Must create manager on main thread on macOS.**

```rust
use global_hotkey::{GlobalHotKeyManager, GlobalHotKeyEvent, HotKeyState, hotkey::{HotKey, Modifiers, Code}};

let manager = GlobalHotKeyManager::new()?;
let hotkey = HotKey::new(Some(Modifiers::META | Modifiers::SHIFT), Code::KeyT);
manager.register(hotkey)?;

// Poll
if let Ok(event) = GlobalHotKeyEvent::receiver().try_recv() {
    if event.state == HotKeyState::Pressed { /* triggered */ }
}
```

## screencapturekit (v1.5.4, Mar 2026) - Screen Capture

```toml
screencapturekit = "1.5"
```

- Zero-copy IOSurface GPU access (Metal/OpenGL)
- macOS 12.3+ base, 13.0+ audio, 14.0+ screenshots, 15.0+ recording
- Async API, runtime-agnostic
- Requires Screen Recording permission

## Threading Architecture

```
Main Thread (macOS requirement):
  - tray-icon event loop
  - global-hotkey polling
  - 16ms sleep between polls (~60fps)

Tokio Runtime (separate threads):
  - Audio capture + VAD
  - S2S pipeline (STT -> translate -> TTS -> playback)
  - OCR processing
  - Lesson scheduler
```

### rusqlite Send/Sync Fix
`rusqlite::Connection` is NOT Send/Sync (contains RefCell). Fix:

```rust
pub struct Database {
    conn: Mutex<Connection>,
}

// SAFETY: All access serialized through Mutex
unsafe impl Send for Database {}
unsafe impl Sync for Database {}
```

### Tokio Spawn Pattern
```rust
// Move ownership into async task
let scheduler = LessonScheduler::new(20);
runtime.spawn(async move { scheduler.run(db).await });
```

## macOS Permissions Required

| Permission | Crate | Trigger |
|-----------|-------|---------|
| Screen Recording | screencapturekit | First screen capture attempt |
| Microphone | cpal | First audio input stream |
| Accessibility | global-hotkey | Some hotkey combinations |
| Notifications | notify-rust | First notification sent |

Users must grant these in System Settings > Privacy & Security.

## Main Event Loop Pattern

```rust
fn main() -> Result<()> {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(4)
        .enable_all()
        .build()?;

    // Spawn async tasks on tokio
    runtime.spawn(audio_loop(...));
    runtime.spawn(ocr_loop(...));

    // Main thread: tray + hotkeys (macOS requirement)
    let mut tray = TrayMenu::new()?;
    loop {
        if let Some(action) = tray.poll_action() {
            match action {
                TrayAction::Quit => {
                    runtime.shutdown_timeout(Duration::from_secs(5));
                    break;
                }
                _ => { /* handle */ }
            }
        }
        std::thread::sleep(Duration::from_millis(16));
    }
    Ok(())
}
```
