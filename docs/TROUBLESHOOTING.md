# Troubleshooting

## The app does not start

Run `ryotunes-diagnostics` after a package install (or `./scripts/diagnostics.sh` from the source tree) and check that WebKitGTK 4.1 and mpv are present. If you installed the package, `pacman -Q ryotunes` should report the installed version.

## Build fails because `rust` conflicts with `rustup`

Do not install both. Ryotunes accepts either provider. If `cargo --version` already works, keep the existing toolchain. The included installer only installs `rustup` when Cargo is missing.

## The interface is too large or too small

Use **Settings → General → Interface scale**. `Ctrl+0` restores the Ryotunes default (120%).

## Signed-in content is empty or stale

Confirm the network is available, then reopen the affected page. If the Google session expired, sign out and sign in again. Ryotunes keeps signed-out playback/search usable and should not require deleting the whole data directory for an account refresh.

## A track cannot play

Some tracks are region/account restricted or can temporarily fail across YouTube playback clients. Ryotunes tries its normal fallback chain automatically. Personal uploads require an active signed-in YouTube Music session.

## Cover art is blank everywhere

Qt has no TLS backend, so the QML client can't fetch any images (`qs log` shows `No functional TLS backend was found`). On Void install `qt6-plugin-tls-openssl` and restart Ryotunes. `ryotunes-diagnostics` checks for it.

## Touchpad scrolling stops over cards

This should not happen in current builds: album art and cards do not capture wheel/two-finger events for volume. Only the actual volume slider handles a wheel gesture. Please attach a sanitized diagnostics report if you can reproduce it.

## Full reset

Uninstalling the package intentionally preserves personal application data. For a complete reset, first sign out of Ryotunes, close the app, then remove its `dev.ryoku.ryotunes` application-data directory using your desktop's normal per-user data location. Do not post that directory publicly because it can contain session state.
