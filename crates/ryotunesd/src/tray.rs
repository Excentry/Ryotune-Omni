//! System tray: app icon + menu (Show / Play-Pause / Next / Previous / Quit), a straight port of
//! the Linux backend in `src-tauri/src/tray.rs`. `ksni` speaks StatusNotifierItem directly, so a
//! left-click reaches [`RyotunesTray::activate`] (libappindicator never delivers one). Menu actions
//! route into the same [`AppState`] methods the OS media keys use, so the tray can never behave
//! differently from MPRIS. Show goes through [`show`], the daemon's single "come back" path.

use std::sync::Arc;
use std::sync::OnceLock;

use ksni::menu::{MenuItem, StandardItem};
use ksni::{Handle, Tray, TrayMethods};
use ryotunes_core::host::EventSink;
use ryotunes_core::state::AppState;
use serde_json::Value;
use tokio::sync::mpsc::UnboundedSender;

use crate::sink::SocketSink;

/// The `Handle` isn't `Clone` and lives for the process, so it sits in a `OnceLock` the same way
/// the Tauri backend keeps it out of managed state — that also lets [`set_playing`] update the
/// label without borrowing across an await.
static HANDLE: OnceLock<Handle<RyotunesTray>> = OnceLock::new();

struct RyotunesTray {
    state: Arc<AppState>,
    quit: UnboundedSender<()>,
    sink: Arc<SocketSink>,
    playing: bool,
}

impl RyotunesTray {
    /// Menu ids are the contract with [`menu`](RyotunesTray::menu); Show/Quit are handled inline and
    /// the transport actions spawn onto the runtime like the Tauri backend's `handle_menu`.
    fn handle_menu(&self, id: &str) {
        match id {
            "show" => show(&self.sink),
            "quit" => {
                let _ = self.quit.send(());
            }
            other => {
                let state = self.state.clone();
                let id = other.to_string();
                tokio::spawn(async move {
                    match id.as_str() {
                        "play_pause" => state.resume_or_toggle().await,
                        "next" => state.next_in_queue().await,
                        "prev" => state.prev_in_queue().await,
                        _ => {}
                    }
                });
            }
        }
    }
}

impl Tray for RyotunesTray {
    fn id(&self) -> String {
        "ryotune-omni".into()
    }

    fn title(&self) -> String {
        "Ryotunes Omni".into()
    }

    /// The packaged `ryotune-omni` hicolor icon (installed by the PKGBUILD); the StatusNotifierItem
    /// resolves it from the theme, so no in-process pixmap is needed without an `AppHandle`.
    fn icon_name(&self) -> String {
        "ryotune-omni".into()
    }

    /// The entire reason this backend exists: the desktop dispatches a left-click here.
    fn activate(&mut self, _x: i32, _y: i32) {
        show(&self.sink);
    }

    fn menu(&self) -> Vec<MenuItem<Self>> {
        let item = |label: &str, id: &'static str| {
            MenuItem::from(StandardItem {
                label: label.into(),
                activate: Box::new(move |t: &mut Self| t.handle_menu(id)),
                ..Default::default()
            })
        };
        vec![
            item("Show Ryotunes Omni", "show"),
            MenuItem::Separator,
            item(if self.playing { "Pause" } else { "Play" }, "play_pause"),
            item("Next", "next"),
            item("Previous", "prev"),
            MenuItem::Separator,
            item("Quit", "quit"),
        ]
    }
}

/// The daemon's "come back" path, shared by the tray (Show / left-click), the `show` socket
/// method (a second `ryotunesd` launch) and the Tauri binary deferring to a live daemon. A
/// subscribed client is told to raise its window; with no client listening the native client
/// (`ryotunes-qml`) is spawned detached. It is the only client that speaks to this daemon: the
/// Tauri app carries its own player, so launching it here would put two engines on the same audio
/// device (it was once selected by `RYOTUNES_CLIENT`; that produced exactly that bug).
pub fn show(sink: &Arc<SocketSink>) {
    if sink.subscriber_count() > 0 {
        sink.emit("show", Value::Null);
        return;
    }
    if let Err(e) = std::process::Command::new("ryotune-omni-qml").spawn() {
        tracing::warn!(error = %e, "`show` could not launch ryotune-omni-qml");
    }
}

/// Register the tray. Registration with the StatusNotifierWatcher is async and can fail (no
/// watcher on the bus); that costs the tray, not the daemon, so it is logged, not propagated.
pub fn spawn(state: Arc<AppState>, quit: UnboundedSender<()>, sink: Arc<SocketSink>) {
    let tray = RyotunesTray { state, quit, sink, playing: false };
    tokio::spawn(async move {
        match tray.spawn().await {
            Ok(handle) => {
                let _ = HANDLE.set(handle);
            }
            Err(e) => tracing::error!("tray: StatusNotifierItem registration failed: {e}"),
        }
    });
}

/// Flip the Play/Pause label to match playback, driven from the event pump's `Playing` arm.
pub fn set_playing(playing: bool) {
    let Some(handle) = HANDLE.get() else { return };
    tokio::spawn(async move {
        handle.update(|t| t.playing = playing).await;
    });
}
