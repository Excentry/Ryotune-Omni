#!/usr/bin/env bash
# Fail when a binary in the package needs a newer glibc than the oldest distro we ship to.
# Void is the floor right now (2.41); Arch moves ahead of it on its own.
#
#   scripts/check-glibc.sh dist/ryotunes-<ver>-1-x86_64.pkg.tar.zst [max]
set -euo pipefail

pkg=${1:?usage: check-glibc.sh <package> [max-glibc]}
max=${2:-2.41}
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
bsdtar -xf "$pkg" -C "$dir" usr

newer() { [[ $1 != "$2" && $(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n1) == "$1" ]]; }

bad=0
while IFS= read -r -d '' f; do
  [[ $(od -An -N4 -tx1 "$f" | tr -d ' \n') == 7f454c46 ]] || continue
  syms=$(objdump -T "$f" | grep -o 'GLIBC_[0-9.]*) *[^ ]*$' || true)
  while read -r ver sym; do
    [[ -n $ver ]] || continue
    ver=${ver#GLIBC_}; ver=${ver%)}
    if newer "$ver" "$max"; then
      echo "${f#"$dir"/}: $sym needs glibc $ver (max $max)" >&2
      bad=1
    fi
  done <<<"$syms"
done < <(find "$dir/usr" -type f -print0)

((bad == 0)) && echo "glibc: every binary runs on $max"
exit "$bad"
