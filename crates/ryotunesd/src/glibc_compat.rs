//! QuickJS (via rustypipe) calls libm's sinh/cosh. glibc 2.44 moved both to a new symbol
//! version, so a daemon built on current Arch refused to start on older glibc (Void ships 2.41).
//! Defining them here means the binary never imports them from libm.

#[unsafe(no_mangle)]
pub extern "C" fn sinh(x: f64) -> f64 {
    libm::sinh(x)
}

#[unsafe(no_mangle)]
pub extern "C" fn cosh(x: f64) -> f64 {
    libm::cosh(x)
}
