//! The daemon's socket protocol. One JSON object per line in both directions.
pub mod wire;

pub use wire::{ErrorBody, Event, Incoming, Outgoing, Request, Response, PROTOCOL_VERSION};

use std::path::PathBuf;

/// `$XDG_RUNTIME_DIR/ryotune-omni/daemon.sock`, or `/tmp/ryotune-omni-<uid>/daemon.sock` without a
/// runtime dir (a bare TTY login). The directory is created by the daemon with mode 0700.
pub fn socket_path() -> PathBuf {
    match std::env::var_os("XDG_RUNTIME_DIR").map(PathBuf::from) {
        Some(dir) => dir.join("ryotune-omni").join("daemon.sock"),
        None => std::env::temp_dir()
            .join(format!("ryotune-omni-{}", unsafe { libc_uid() }))
            .join("daemon.sock"),
    }
}

#[cfg(test)]
mod tests {
    use super::socket_path;

    #[test]
    fn socket_uses_omni_specific_path() {
        let path = socket_path();
        assert_eq!(path.file_name().unwrap(), "daemon.sock");
        let parent = path.parent().unwrap();
        assert!(
            parent.ends_with("ryotune-omni") || parent.to_string_lossy().contains("ryotune-omni-")
        );
    }
}

// No libc dependency for one call: read the uid from the kernel.
unsafe fn libc_uid() -> u32 {
    std::fs::read_to_string("/proc/self/loginuid")
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(0)
}
