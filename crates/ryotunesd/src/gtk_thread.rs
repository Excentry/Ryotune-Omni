//! One thread owns GTK. Everything WebKit is marshalled onto it; nothing else touches GTK.

use std::future::Future;

use tokio::sync::oneshot;

#[derive(Clone)]
pub struct Gtk {
    ctx: glib::MainContext,
}

impl Gtk {
    /// Start the GTK main loop on its own thread and return a handle. Panics if GTK cannot
    /// initialise (no display): the daemon then refuses to start, which is the right answer
    /// because the cipher/PoToken path needs a display.
    pub fn start() -> Gtk {
        // WebKitGTK defaults to a GL-accelerated compositor. Headless/offscreen (and some
        // Wayland + proprietary-GPU sessions) can't hand it a GL context, and WebKit then aborts
        // the whole process with "GDK is not able to create a GL context". The cipher/PoToken
        // views never paint, so force the software path before GTK or any web process starts.
        // (`set_var` is safe on the 2021 edition and this runs before the GTK thread exists.)
        std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        // The views are never shown, so they need no accessibility. GTK otherwise loads the
        // AT-SPI bridge in `gtk::init`, and when the session's a11y bus is stale or replaced
        // mid-session the bridge segfaults the daemon the next time a view is built, killing
        // playback and the client with it. Scoped to init so the client and the browser the
        // daemon opens keep their accessibility.
        let inherited_no_at_bridge = std::env::var_os("NO_AT_BRIDGE");
        std::env::set_var("NO_AT_BRIDGE", "1");
        let (tx, rx) = std::sync::mpsc::channel();
        std::thread::Builder::new()
            .name("gtk".into())
            .spawn(move || {
                gtk::init().expect("GTK init (is WAYLAND_DISPLAY/DISPLAY set?)");
                // Acquire the thread-default context this thread owns so `invoke` from other
                // threads queues onto *our* loop, and `gtk::main` below pumps it.
                let ctx = glib::MainContext::default();
                tx.send(ctx.clone()).unwrap();
                gtk::main();
            })
            .expect("spawn gtk thread");
        let ctx = rx.recv().expect("gtk thread reported its context");
        match inherited_no_at_bridge {
            Some(v) => std::env::set_var("NO_AT_BRIDGE", v),
            None => std::env::remove_var("NO_AT_BRIDGE"),
        }
        Gtk { ctx }
    }

    /// Run `f` on the GTK thread and await its result.
    pub fn call<R: Send + 'static>(
        &self,
        f: impl FnOnce() -> R + Send + 'static,
    ) -> impl Future<Output = R> {
        let (tx, rx) = oneshot::channel();
        self.ctx.invoke(move || {
            let _ = tx.send(f());
        });
        async move { rx.await.expect("gtk closure ran") }
    }
}

/// Short-circuit process exit so WebKitGTK's own atexit teardown never runs.
///
/// GTK/WebKit are initialised on the GTK worker thread, so WebKit treats that thread as its main
/// thread. libc runs exit handlers on the *process* main thread, and WebKit's global-context unref
/// there trips a main-thread `RELEASE_ASSERT` and `abort()`s — after all real work is done. We
/// register a glibc `on_exit` handler (it receives the true status) that `_exit`s immediately,
/// preserving the exit code and skipping WebKit's broken teardown.
///
/// WebKit registers its global-context destructor lazily, when the first `WebView` is built, so
/// this MUST be called *after* that (exit handlers run last-registered-first). Callers install it
/// once, right after building their first view; the `Once` makes repeat calls free.
pub(crate) fn install_clean_exit() {
    use std::os::raw::{c_int, c_void};
    use std::sync::Once;

    extern "C" {
        fn on_exit(f: extern "C" fn(c_int, *mut c_void), arg: *mut c_void) -> c_int;
    }
    extern "C" fn hard_exit(status: c_int, _: *mut c_void) {
        unsafe { libc::_exit(status) }
    }

    static ONCE: Once = Once::new();
    ONCE.call_once(|| unsafe {
        on_exit(hard_exit, std::ptr::null_mut());
    });
}
