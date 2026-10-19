#!/usr/bin/env bash
set -euo pipefail

bump="${1:-patch}"
case "$bump" in
  major|minor|patch) ;;
  *)
    echo "usage: $0 [major|minor|patch]" >&2
    exit 2
    ;;
esac

if [[ -n "${RYOTUNE_OMNI_TAGS+x}" ]]; then
  tags="$RYOTUNE_OMNI_TAGS"
else
  tags="$(git tag -l 'omni-v*')"
fi

best_major=-1
best_minor=-1
best_patch=-1
for tag in $tags; do
  if [[ "$tag" =~ ^omni-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[3]}"
    if (( major > best_major || (major == best_major && minor > best_minor) || (major == best_major && minor == best_minor && patch > best_patch) )); then
      best_major="$major"
      best_minor="$minor"
      best_patch="$patch"
    fi
  fi
done

if (( best_major < 0 )); then
  echo "0.1.0"
  exit 0
fi

case "$bump" in
  major)
    best_major=$((best_major + 1))
    best_minor=0
    best_patch=0
    ;;
  minor)
    best_minor=$((best_minor + 1))
    best_patch=0
    ;;
  patch)
    best_patch=$((best_patch + 1))
    ;;
esac

echo "$best_major.$best_minor.$best_patch"
