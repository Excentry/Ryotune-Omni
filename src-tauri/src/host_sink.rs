//! `EventSink` for the Tauri host: every core event becomes a Tauri event on every window.

use std::sync::{Arc, Mutex};

use ryotunes_core::host::EventSink;
use serde_json::Value;
use tauri::{AppHandle, Emitter};

pub struct LoginCommandState {
    serial: tokio::sync::Mutex<()>,
    errors: Arc<Mutex<Option<String>>>,
}

impl Default for LoginCommandState {
    fn default() -> Self {
        Self { serial: tokio::sync::Mutex::new(()), errors: Arc::new(Mutex::new(None)) }
    }
}

impl LoginCommandState {
    pub(crate) async fn lock(&self) -> tokio::sync::MutexGuard<'_, ()> {
        self.serial.lock().await
    }

    pub(crate) fn error_slot(&self) -> Arc<Mutex<Option<String>>> {
        Arc::clone(&self.errors)
    }

    pub(crate) fn clear_error(&self) {
        *self.errors.lock().unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    pub(crate) fn take_error(&self) -> Option<String> {
        self.errors.lock().unwrap_or_else(std::sync::PoisonError::into_inner).take()
    }
}

pub struct TauriSink {
    app: AppHandle,
    login_errors: Arc<Mutex<Option<String>>>,
}

impl TauriSink {
    pub fn new(app: AppHandle, login_errors: Arc<Mutex<Option<String>>>) -> Self {
        Self { app, login_errors }
    }
}

fn capture_login_error(errors: &Mutex<Option<String>>, event: &str, payload: &Value) {
    if event == "login-error" {
        if let Some(message) = payload.as_str() {
            *errors.lock().unwrap_or_else(std::sync::PoisonError::into_inner) =
                Some(message.to_owned());
        }
    }
}

impl EventSink for TauriSink {
    fn emit(&self, event: &'static str, payload: Value) {
        capture_login_error(&self.login_errors, event, &payload);
        // The Windows taskbar thumbnail toolbar isn't a webview event, and the core no longer holds
        // an AppHandle to poke it. Drive its play/pause glyph off the same playback-state the UI
        // gets. cfg-gated so non-Windows builds stay byte-identical.
        #[cfg(target_os = "windows")]
        if event == "playback-state" {
            if let Some(state) = payload.as_str() {
                crate::taskbar::set_playing(&self.app, state == "playing");
            }
        }
        if let Err(e) = self.app.emit(event, payload) {
            tracing::debug!(event, error = %e, "event emit failed (no window?)");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn captures_login_error_for_command_result() {
        let errors = Mutex::new(None);

        capture_login_error(
            &errors,
            "login-error",
            &Value::String("Sign-in timed out. Please try again.".into()),
        );

        assert_eq!(errors.lock().unwrap().as_deref(), Some("Sign-in timed out. Please try again."));
    }

    #[test]
    fn ignores_non_login_errors() {
        let errors = Mutex::new(None);

        capture_login_error(&errors, "playback-error", &Value::String("ignored".into()));

        assert!(errors.lock().unwrap().is_none());
    }

    #[test]
    fn login_command_clears_and_consumes_errors() {
        let state = LoginCommandState::default();
        let errors = state.error_slot();
        *errors.lock().unwrap() = Some("previous login failure".into());

        state.clear_error();
        assert_eq!(state.take_error(), None);

        *errors.lock().unwrap() = Some("current login failure".into());
        assert_eq!(state.take_error().as_deref(), Some("current login failure"));
        assert_eq!(state.take_error(), None);
    }
}
