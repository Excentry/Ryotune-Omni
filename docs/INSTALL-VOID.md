# Install on Void Linux

Releases only ship an Arch package. On Void it gets repacked into an `.xbps` on your machine and installed with xbps, so it's tracked like any other package.

## Install or update

From a clone or the release source tarball:

```bash
scripts/install-void.sh
```

It downloads the latest release, checks the sha256, drops the systemd units (Void doesn't use them; `ryotunes` starts the daemon itself), builds `ryotunes-<version>_1` with the dependencies in `packaging/void/depends`, and installs it with `sudo xbps-install`.

Then quit Ryotunes and open it again (closing the window isn't enough):

```bash
ryotunes-cli quit
ryotunes
```

## Updating from inside the app

Once installed this way (or from Ryoku's Void repo), **Settings → About → Update** works too. It does the same repack and asks polkit to run `xbps-install`, so you need a polkit agent running.

v1.2.1 and older were built against glibc 2.44 and the daemon won't start on Void (glibc 2.41). Both the script and the in-app updater refuse such a release instead of installing it.

## No cover art

If songs play but covers stay blank, Qt can't do HTTPS. Void ships Qt's TLS backend separately:

```bash
sudo xbps-install qt6-plugin-tls-openssl
```

Then restart Ryotunes. The repacked package already depends on it. `ryotunes-diagnostics` shows whether it's there.
