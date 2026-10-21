//! Mini player: a small always-on-top widget that stands in for the main window.
//!
//! It loads the same SPA as the main window — the root layout branches on the window label — so
//! there is no second bundle and no second copy of the playback state: every event this app emits
//! is global (`app.emit`, never `emit_to`), so both webviews are driven by the same stream.
//!
//! On Linux the mini player replaces the main WebKit view: opening it hibernates/destroys the
//! main webview while the native playback backend keeps running. On other platforms the main
//! window is hidden instead. Restoring always goes through [`crate::tray::show_main`] so the
//! widget button, tray actions and a second launch share the same lifecycle path.
//!
//! Linux therefore avoids retaining an invisible main renderer alongside the mini player. The
//! rebuilt main window resynchronizes from the native playback state when it is shown again.

use std::sync::Arc;

use tauri::{
    AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder,
};

use crate::state::AppState;

pub const LABEL: &str = "mini";

/// Logical size of the widget. Fixed: compact enough to live beside Ryoku shell widgets, but
/// wide enough for artwork, metadata and transport controls without cramming.
const W: f64 = 724.0;
const H: f64 = 356.0;
/// Inset from the screen edge the first time it opens.
const MARGIN: f64 = 24.0;
/// Where the user last dragged it, as physical `"x,y"`. Physical because monitor geometry is, and
/// two displays can disagree on scale factor.
const POS_KEY: &str = "mini_position";

/// Build (or re-show) the widget, then hibernate/hide the main window for the platform.
///
/// **Main thread only** — GTK wants window creation there, same rule as the login and cipher
/// webviews. `commands::open_mini` does the hop.
pub fn open(app: &AppHandle) -> Result<(), String> {
    if let Some(w) = app.get_webview_window(LABEL) {
        let _ = w.show();
        let _ = w.set_focus();
        crate::main_window::hibernate_main(app);
        return Ok(());
    }

    let win = WebviewWindowBuilder::new(app, LABEL, WebviewUrl::App("index.html".into()))
        .title("Ryotunes Omni Mini")
        .inner_size(W, H)
        .resizable(false)
        .decorations(false)
        .transparent(true)
        .always_on_top(true)
        .skip_taskbar(true)
        .shadow(false)
        // First paint is coordinated by `frontend_ready`; never expose the boot document.
        .visible(false)
        .build()
        .map_err(|e| format!("couldn't open the mini player: {e}"))?;

    if let Some(p) = placement(app, &win) {
        let _ = win.set_position(p);
    }
    #[cfg(target_os = "linux")]
    crate::tune_webview_labelled(app, LABEL);
    // Do NOT hibernate main yet. If the mini WebView fails to mount, the user must retain the
    // existing full app instead of being stranded with only a tray icon.
    Ok(())
}

/// Reveal the mini only after its Svelte tree exists, then hibernate the expensive main WebView.
pub fn frontend_ready(app: &AppHandle) -> Result<(), String> {
    let Some(w) = app.get_webview_window(LABEL) else {
        return Err("mini player window is missing".into());
    };
    w.show().map_err(|e| format!("show mini player: {e}"))?;
    let _ = w.set_focus();
    crate::main_window::hibernate_main(app);
    Ok(())
}

/// Remember where the widget currently sits. No-op when it isn't up. Its own function because
/// quitting from the tray is a way down that never reaches [`close`].
pub fn save_position(app: &AppHandle) {
    let Some(w) = app.get_webview_window(LABEL) else { return };
    if let (Ok(p), Some(state)) = (w.outer_position(), app.try_state::<Arc<AppState>>()) {
        state.db.set_setting(POS_KEY, &format!("{},{}", p.x, p.y));
    }
}

/// Take the widget down, remembering where it ended up. Callable from any thread; bringing the
/// main window back is [`crate::tray::show_main`]'s job, which is what calls this.
pub fn close(app: &AppHandle) {
    if app.get_webview_window(LABEL).is_none() {
        return;
    }
    save_position(app);
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || {
        if let Some(w) = handle.get_webview_window(LABEL) {
            let _ = w.destroy();
        }
    });
}

/// Where to put it: the last position if that spot still exists (a display can be unplugged
/// between sessions), otherwise the bottom-right of whichever display the app is on.
fn placement(app: &AppHandle, win: &WebviewWindow) -> Option<PhysicalPosition<i32>> {
    app.try_state::<Arc<AppState>>()
        .and_then(|s| s.db.get_setting(POS_KEY))
        .and_then(|v| parse_pos(&v))
        .filter(|p| on_a_display(win, *p))
        .or_else(|| bottom_right(app, win))
}

/// `"x,y"` in physical pixels, as [`close`] wrote it.
fn parse_pos(s: &str) -> Option<PhysicalPosition<i32>> {
    let (x, y) = s.split_once(',')?;
    Some(PhysicalPosition::new(x.trim().parse().ok()?, y.trim().parse().ok()?))
}

/// Is that point on a display that is currently connected? Checked on the top-left corner, which
/// is what `set_position` sets and what the WM keeps reachable.
fn on_a_display(win: &WebviewWindow, p: PhysicalPosition<i32>) -> bool {
    win.available_monitors()
        .is_ok_and(|monitors| monitors.iter().any(|m| contains(*m.position(), *m.size(), p)))
}

/// Bottom-right of the display the main window is on, inside its *work area* so a taskbar or dock
/// doesn't end up sitting on top of the widget.
fn bottom_right(app: &AppHandle, win: &WebviewWindow) -> Option<PhysicalPosition<i32>> {
    let anchor = app.get_webview_window("main").unwrap_or_else(|| win.clone());
    let m = anchor
        .current_monitor()
        .ok()
        .flatten()
        .or_else(|| anchor.primary_monitor().ok().flatten())?;
    let area = m.work_area();
    let px = |logical: f64| (logical * m.scale_factor()).round() as i32;
    Some(PhysicalPosition::new(
        area.position.x + area.size.width as i32 - px(W + MARGIN),
        area.position.y + area.size.height as i32 - px(H + MARGIN),
    ))
}

/// Point-in-rect, physical pixels. Its own function because a second monitor placed left of or
/// above the primary has a negative origin, which is exactly the case that goes wrong.
fn contains(
    origin: PhysicalPosition<i32>,
    size: PhysicalSize<u32>,
    p: PhysicalPosition<i32>,
) -> bool {
    (origin.x..origin.x + size.width as i32).contains(&p.x)
        && (origin.y..origin.y + size.height as i32).contains(&p.y)
}

#[cfg(test)]
mod tests {
    use super::{contains, parse_pos};
    use tauri::{PhysicalPosition, PhysicalSize};

    #[test]
    fn parses_what_close_wrote() {
        assert_eq!(parse_pos("120,64"), Some(PhysicalPosition::new(120, 64)));
        // A monitor left of the primary gives negative coordinates.
        assert_eq!(parse_pos("-1800,-200"), Some(PhysicalPosition::new(-1800, -200)));
        assert_eq!(parse_pos("garbage"), None);
        assert_eq!(parse_pos("12,"), None);
    }

    #[test]
    fn point_lands_on_the_right_display() {
        let primary = (PhysicalPosition::new(0, 0), PhysicalSize::new(1920u32, 1080));
        // Second monitor to the *left* of the primary: origin is negative.
        let left = (PhysicalPosition::new(-1920, 0), PhysicalSize::new(1920u32, 1080));

        assert!(contains(primary.0, primary.1, PhysicalPosition::new(1300, 800)));
        assert!(!contains(primary.0, primary.1, PhysicalPosition::new(-500, 800)));
        assert!(contains(left.0, left.1, PhysicalPosition::new(-500, 800)));
        // Right/bottom edges are exclusive — that pixel belongs to the next display.
        assert!(!contains(primary.0, primary.1, PhysicalPosition::new(1920, 500)));
        assert!(!contains(primary.0, primary.1, PhysicalPosition::new(500, 1080)));
    }
}
