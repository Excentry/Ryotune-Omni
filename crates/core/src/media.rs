//! OS media integration (MPRIS / SMTC / NowPlaying) via `souvlaki`. fail-soft policy, D11.
//!
//! `souvlaki`'s `MediaControls` isn't `Send`, and on Windows/macOS its events arrive on the
//! platform's own loop — so we give it a dedicated owner thread. The app talks to that thread over
//! a channel ([`MediaHandle`]); OS control presses route back out over an mpsc channel of
//! [`MediaControlEvent`]s that the host drains into `AppState`. The two share the same commands the
//! UI uses, so they never drift.

use std::sync::mpsc::{channel, Sender};
use std::sync::Arc;
use std::time::Duration;

use souvlaki::{MediaControls, MediaMetadata, MediaPlayback, PlatformConfig};
use tokio::sync::mpsc::UnboundedSender;

use crate::host::EventSink;

/// Re-exported for hosts that drain [`spawn`]'s control-event channel into `AppState`. The daemon
/// pattern-matches these to route OS media-key presses, and cannot depend on `souvlaki` directly
/// without pulling a second copy of the crate; sourcing them from the core keeps one type.
pub use souvlaki::{MediaControlEvent, MediaPosition, SeekDirection};

/// Update messages: app → media-controls owner thread.
enum MediaUpdate {
    Metadata {
        title: String,
        artist: String,
        album: Option<String>,
        cover: Option<String>,
    },
    Duration(f64),
    Playback {
        playing: bool,
        pos: f64,
    },
    /// Deterministic teardown for explicit Quit. The acknowledgement is sent only after the
    /// platform media object has been stopped/cleared and is about to be dropped.
    Shutdown(Sender<()>),
}

/// App-side handle to the media-controls thread. Cheap to clone-send into. `None` when the OS
/// integration failed to initialize (e.g. no session bus) — every push is then a no-op.
pub struct MediaHandle {
    tx: Sender<MediaUpdate>,
}

impl MediaHandle {
    pub fn set_metadata(
        &self,
        title: &str,
        artist: &str,
        album: Option<&str>,
        cover: Option<&str>,
    ) {
        let _ = self.tx.send(MediaUpdate::Metadata {
            title: title.to_owned(),
            artist: artist.to_owned(),
            album: album.map(str::to_owned),
            cover: cover.map(str::to_owned),
        });
    }

    pub fn set_duration(&self, secs: f64) {
        let _ = self.tx.send(MediaUpdate::Duration(secs));
    }

    pub fn set_playback(&self, playing: bool, pos: f64) {
        let _ = self.tx.send(MediaUpdate::Playback { playing, pos });
    }

    /// Tear down MPRIS/SMTC synchronously enough for a user-facing Quit to disappear from the
    /// desktop media island before the process exits. Bounded so a broken platform service can
    /// never hang application shutdown.
    pub fn shutdown(&self) {
        let (ack_tx, ack_rx) = channel();
        if self.tx.send(MediaUpdate::Shutdown(ack_tx)).is_ok() {
            let _ = ack_rx.recv_timeout(Duration::from_millis(900));
        }
    }
}

/// Spawn the media-controls owner thread. Returns `None` if the platform controls can't be
/// created (integration simply absent then — MPRIS-only fallback is blessed, fail-soft policy).
///
/// `_sink` is reserved for future media-originated events; today OS control presses travel out
/// over `commands`, which the host drains into `AppState`.
pub fn spawn(
    _sink: Arc<dyn EventSink>,
    commands: UnboundedSender<MediaControlEvent>,
) -> Option<MediaHandle> {
    let (tx, rx) = channel::<MediaUpdate>();
    let spawned =
        std::thread::Builder::new().name("media-controls".into()).spawn(move || run(commands, rx));
    match spawned {
        Ok(_) => Some(MediaHandle { tx }),
        Err(e) => {
            tracing::warn!(error = %e, "media-controls thread spawn failed");
            None
        }
    }
}

// `duration` is reset per track in the Metadata arm; the lint can't see the loop's later reads.
#[allow(unused_assignments)]
fn run(commands: UnboundedSender<MediaControlEvent>, rx: std::sync::mpsc::Receiver<MediaUpdate>) {
    // The core owns no window handle; on Windows the host would supply one for SMTC. Linux/MPRIS
    // ignores it.
    let hwnd = None;

    let config = PlatformConfig { dbus_name: "ryotune-omni", display_name: "Ryotune Omni", hwnd };
    let mut controls = match MediaControls::new(config) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!(error = ?e, "OS media controls unavailable — skipping (fail-soft policy)");
            return;
        }
    };
    if let Err(e) = controls.attach(move |event| {
        let _ = commands.send(event);
    }) {
        tracing::warn!(error = ?e, "media controls attach failed");
        return;
    }
    tracing::info!("OS media controls attached");

    // Owner-thread-local mirror of what the OS should show; rebuilt on each change.
    let mut title = String::new();
    let mut artist = String::new();
    let mut album: Option<String> = None;
    let mut cover: Option<String> = None;
    let mut duration: Option<f64> = None;

    // `recv` blocks until the sender drops (app shutdown), keeping `controls` alive.
    while let Ok(update) = rx.recv() {
        match update {
            MediaUpdate::Metadata { title: t, artist: a, album: al, cover: c } => {
                title = t;
                artist = a;
                album = al;
                cover = c;
                duration = None; // new track — length not known until mpv reports it
                apply_metadata(&mut controls, &title, &artist, &album, &cover, duration);
            }
            MediaUpdate::Duration(secs) => {
                duration = Some(secs);
                apply_metadata(&mut controls, &title, &artist, &album, &cover, duration);
            }
            MediaUpdate::Playback { playing, pos } => {
                let progress = Some(MediaPosition(Duration::from_secs_f64(pos.max(0.0))));
                let state = if playing {
                    MediaPlayback::Playing { progress }
                } else {
                    MediaPlayback::Paused { progress }
                };
                let _ = controls.set_playback(state);
            }
            MediaUpdate::Shutdown(ack) => {
                // Explicit Quit is semantically different from close-to-tray. Take the player out
                // of the OS media namespace and *drop the platform owner* before acknowledging.
                // On MPRIS the drop releases the DBus name; this ordering prevents the desktop
                // music island from lingering after the user has already chosen Quit.
                let _ = controls.set_playback(MediaPlayback::Stopped);
                let _ = controls.set_metadata(MediaMetadata {
                    title: None,
                    artist: None,
                    album: None,
                    cover_url: None,
                    duration: None,
                });
                drop(controls);
                let _ = ack.send(());
                return;
            }
        }
    }
}

fn apply_metadata(
    controls: &mut MediaControls,
    title: &str,
    artist: &str,
    album: &Option<String>,
    cover: &Option<String>,
    duration: Option<f64>,
) {
    let _ = controls.set_metadata(MediaMetadata {
        title: Some(title),
        artist: Some(artist),
        album: album.as_deref(),
        cover_url: cover.as_deref(),
        duration: duration.map(Duration::from_secs_f64),
    });
}
