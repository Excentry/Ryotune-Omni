#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
profile=debug
skip_frontend=0
run=0

usage() {
    cat <<'EOF'
Build Ryotune Omni locally, separately from upstream Ryotunes.

Usage: scripts/dev/omni.sh [--release] [--skip-frontend] [--run] [--help]

  --release        Build optimized binaries instead of the development profile.
  --skip-frontend  Reuse ui/build instead of installing/building the frontend.
  --run            Launch the native Quickshell client after the build.

Build outputs are target/debug or target/release:
  ryotune-omni
  ryotune-omni-daemon

The app uses the Ryotune Omni identity, socket and profile. On Linux, --run
also requires Quickshell and the Ryoku QML runtime.
EOF
}

while (($#)); do
    case "$1" in
        --release)
            profile=release
            ;;
        --skip-frontend)
            skip_frontend=1
            ;;
        --run)
            run=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'omni: unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

cd "$root"

if ! command -v cargo >/dev/null 2>&1; then
    printf 'omni: cargo is required\n' >&2
    exit 1
fi

if ((skip_frontend)); then
    if [[ ! -d ui/build ]]; then
        printf 'omni: ui/build is missing; run without --skip-frontend\n' >&2
        exit 1
    fi
else
    if ! command -v pnpm >/dev/null 2>&1; then
        printf 'omni: pnpm is required to build the frontend\n' >&2
        exit 1
    fi
    (cd ui && pnpm install --frozen-lockfile)
    (cd ui && pnpm build)
fi

cargo_args=(build --locked --package ryotunes --package ryotunesd)
if [[ "$profile" == release ]]; then
    cargo_args+=(--release)
fi
cargo "${cargo_args[@]}"

bin_dir="$root/target/$profile"
launcher="$bin_dir/ryotune-omni"
daemon="$bin_dir/ryotune-omni-daemon"
for binary in "$launcher" "$daemon"; do
    if [[ ! -x "$binary" ]]; then
        printf 'omni: expected executable was not produced: %s\n' "$binary" >&2
        exit 1
    fi
done

printf 'Built Ryotune Omni (%s profile):\n  %s\n  %s\n' "$profile" "$launcher" "$daemon"
printf 'Separate app id: dev.excentry.ryotune-omni\n'
printf 'Separate data profile: %s/dev.excentry.ryotune-omni\n' "${XDG_DATA_HOME:-$HOME/.local/share}"
if [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
    socket_path="$XDG_RUNTIME_DIR/ryotune-omni/daemon.sock"
else
    login_uid="$(cat /proc/self/loginuid 2>/dev/null || true)"
    [[ "$login_uid" =~ ^[0-9]+$ ]] || login_uid=0
    socket_path="${TMPDIR:-/tmp}/ryotune-omni-$login_uid/daemon.sock"
fi
printf 'Separate socket: %s\n' "$socket_path"

if ((run)); then
    if ! command -v qs >/dev/null 2>&1; then
        printf 'omni: qs (Quickshell) is required for --run\n' >&2
        exit 1
    fi
    dev_bin="$bin_dir/omni-dev-bin"
    mkdir -p "$dev_bin"
    cat > "$dev_bin/ryotune-omni-qml" <<'EOF'
#!/bin/sh
exec qs -p "$RYOTUNE_OMNI_SOURCE/client" "$@"
EOF
    chmod 755 "$dev_bin/ryotune-omni-qml"
    export RYOTUNE_OMNI_SOURCE="$root"
    export PATH="$bin_dir:$dev_bin:$PATH"
    exec "$launcher"
fi
