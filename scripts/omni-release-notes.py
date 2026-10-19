#!/usr/bin/env python3
import datetime
import re
import subprocess
import sys
from pathlib import Path

OMNI_TAG = re.compile(r'^v0\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$')

CATEGORIES = [
    ('New features', re.compile(r'^(feat|add)\b|^feat[:(!]', re.I)),
    ('Improvements', re.compile(r'^(improve|perf|refactor|style|update)\b', re.I)),
    ('Bug fixes', re.compile(r'^(fix|bugfix|patch|hotfix)\b', re.I)),
    ('Breaking changes', re.compile(r'(^|\W)breaking(\W|$)', re.I)),
]


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def changelog_section(tag):
    path = Path('CHANGELOG.md')
    if not path.exists():
        return ''
    text = path.read_text()
    match = re.search(
        rf'^## {re.escape(tag)}(?:\s[^\n]*)?\n(.*?)(?=^## |\Z)',
        text, re.S | re.M,
    )
    return match.group(1).strip() if match else ''


def categorize(subjects):
    grouped = {name: [] for name, _ in CATEGORIES}
    other = []
    for subject in subjects:
        if re.match(r'^release:', subject):
            continue
        placed = False
        for name, pattern in CATEGORIES:
            if pattern.search(subject):
                grouped[name].append(subject)
                placed = True
                break
        if not placed:
            other.append(subject)
    return grouped, other


def main(tag):
    if not OMNI_TAG.fullmatch(tag):
        raise SystemExit(f'omni-release-notes: {tag} is not a Ryotune-Omni v0 tag')
    version = tag[1:]
    previous = max(
        (t for t in git('tag', '--list').splitlines()
         if OMNI_TAG.fullmatch(t) and t != tag
         and subprocess.run(['git', 'merge-base', '--is-ancestor', t, tag],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0),
        default=None,
    )
    if previous:
        subjects = [
            line for line in
            git('log', '--no-merges', '--format=%s', f'{previous}..{tag}').splitlines()
        ]
    else:
        subjects = []
    grouped, other = categorize(subjects)

    parts = [f'# Ryotune-Omni {tag}']
    authored = changelog_section(tag)
    if authored:
        parts.append(authored)

    parts.append('## Platform availability\n\n'
                 '- **Linux (x86_64):** inherited from upstream Ryotunes; packaging and '
                 'distribution for Ryotune-Omni are not validated yet, so this release '
                 'carries no Linux installable.\n'
                 '- **Windows:** not implemented yet.\n'
                 '- **Android:** not implemented yet.')

    commit_parts = []
    for name, _ in CATEGORIES:
        if grouped[name]:
            lines = '\n'.join(f'- {s}' for s in grouped[name])
            commit_parts.append(f'### {name}\n\n{lines}')
    if other:
        lines = '\n'.join(f'- {s}' for s in other)
        commit_parts.append(f'### Other changes\n\n{lines}')
    if commit_parts:
        scope = f'Since {previous}' if previous else 'Since the fork baseline'
        parts.append(f'## Changes in this release ({scope})\n\n' + '\n\n'.join(commit_parts))

    parts.append('## Known limitations\n\n'
                 '- Ryotune-Omni is in initial development (0.x): interfaces and '
                 'behaviour may change between releases without a major-version bump.\n'
                 '- No platform build of Ryotune-Omni has been validated and published '
                 'yet; see the release assets for what this tag actually carries.\n'
                 '- Windows and Android ports are planned but not implemented; '
                 'feature parity with upstream Ryotunes on those platforms must not '
                 'be assumed.')

    parts.append('## Install or upgrade\n\n'
                 'Build from the tagged source: this repository plus the '
                 '`ryotune-omni-' + version + '.tar.gz` source archive and its SHA-256 '
                 'sidecar. Verify with `sha256sum -c` before use. When validated '
                 'platform artifacts exist they are attached next to the source '
                 'archive with `SHA256SUMS.txt`.')

    parts.append('## Attribution\n\n'
                 'Ryotune-Omni is an independent fork of '
                 '[Ryotunes](https://github.com/Ryoku-dev/ryotunes) (itself derived '
                 'from [LiMusic](https://github.com/SimoHypers/limusic)), licensed '
                 'under GPL-3.0-or-later. Version numbers and releases under the '
                 '`v0.*` line are Ryotune-Omni releases, not releases of upstream '
                 'Ryotunes. Upstream changes reaching this repository through its '
                 'shared history are credited in the upstream project.')

    date = datetime.date.today().isoformat()
    parts.append(f'Released {date} from tag `{tag}`.')
    return '\n\n'.join(parts) + '\n'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: omni-release-notes.py <tag>')
    print(main(sys.argv[1]), end='')
