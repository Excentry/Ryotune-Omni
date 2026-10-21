#!/usr/bin/env python3
"""Check release identity and shipped capability policy, not source spelling.

Builds, runtime smoke checks and behavioral tests cover implementation behavior;
matching comments, UI copy or function bodies cannot prove those contracts.
"""
from pathlib import Path
import json
import re
import tomllib
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]


def read(rel):
    return (root / rel).read_text()


def req(ok, msg):
    if not ok:
        raise SystemExit(f'release invariant failed: {msg}')


cargo = tomllib.loads(read('Cargo.toml'))
lock = tomllib.loads(read('Cargo.lock'))
version = cargo['workspace']['package']['version']
req(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?', version),
    'workspace version is not SemVer MAJOR.MINOR.PATCH with an optional pre-release')
locked = {package['name']: package['version'] for package in lock['package']}
for member in cargo['workspace']['members']:
    manifest = tomllib.loads(read(f'{member}/Cargo.toml'))['package']
    member_version = manifest.get('version')
    if isinstance(member_version, dict) and member_version.get('workspace'):
        req(locked.get(manifest['name']) == version,
            f'Cargo.lock {manifest["name"]} version does not match {version}')

config = json.loads(read('src-tauri/tauri.conf.json'))
req(config.get('version') == version, 'Tauri version does not match workspace')
req(config.get('identifier') == 'dev.excentry.ryotune-omni', 'Tauri application identifier is not Ryotune Omni')
req(config.get('productName') == 'Ryotunes Omni', 'Tauri product name is not Ryotunes Omni')
req(config.get('mainBinaryName') == 'ryotune-omni', 'Tauri main binary is not ryotune-omni')
req(json.loads(read('ui/package.json')).get('version') == version,
    'UI version does not match workspace')
req(read('client/version').strip() == version,
    'native QML client version file does not match workspace')
appstream = ET.fromstring(read('packaging/linux/dev.excentry.ryotune-omni.metainfo.xml'))
req(appstream.findtext('id') == 'dev.excentry.ryotune-omni', 'AppStream application identifier is not Ryotune Omni')
req(appstream.findtext('name') == 'Ryotunes Omni', 'AppStream display name is not Ryotunes Omni')
req(appstream.find('releases/release').get('version') == version,
    'AppStream release version does not match workspace')
arch = read('packaging/arch/PKGBUILD')
req(re.search(rf'^pkgver={re.escape(version.replace("-", ""))}$', arch, re.M),
    'Arch package version does not match workspace')
req(re.search(r'^pkgrel=1$', arch, re.M), 'release asset contract requires pkgrel=1')
req(re.search(r'^pkgname=ryotune-omni$', arch, re.M), 'Arch package name is not ryotune-omni')
req(not re.search(r'^(?:epoch|replaces|conflicts)=', arch, re.M),
    'coexisting package must not use epoch, replaces, or conflicts')
for manifest, package_name, bin_name in [
    ('src-tauri/Cargo.toml', 'ryotunes', 'ryotune-omni'),
    ('crates/ryotunesd/Cargo.toml', 'ryotunesd', 'ryotune-omni-daemon'),
    ('crates/ryotunes-cli/Cargo.toml', 'ryotunes-cli', 'ryotune-omni-cli'),
    ('crates/sync-server/Cargo.toml', 'sync-server', 'ryotune-omni-sync-server'),
]:
    data = tomllib.loads(read(manifest))
    req(data['package']['name'] == package_name, f'{manifest} package name changed unexpectedly')
    req(any(target.get('name') == bin_name for target in data.get('bin', [])),
        f'{manifest} does not declare binary {bin_name}')

desktop = read('packaging/linux/ryotune-omni.desktop')
req('Name=Ryotunes Omni' in desktop and 'Exec=ryotune-omni' in desktop
    and 'Icon=ryotune-omni' in desktop, 'desktop launcher identity is inconsistent')
socket_unit = read('packaging/linux/ryotune-omni-daemon.socket')
req('ListenStream=%t/ryotune-omni/daemon.sock' in socket_unit,
    'systemd socket path does not match Omni protocol path')
req('daemon.sock' in read('client/Daemon.qml') and 'ryotune-omni' in read('client/Daemon.qml'),
    'QML client socket path is not Omni-specific')
updater = read('crates/core/src/update.rs')
req('github.com/Excentry/Ryotune-Omni' in updater and 'ryotune-omni' in updater
    and 'github.com/ryoku-dev/ryotunes' not in updater,
    'self-updater is not restricted to Omni releases/packages')
for legacy_installer in ('aur/PKGBUILD', 'scripts/install-void.sh', 'scripts/build-replacement-package.sh'):
    content = read(legacy_installer)
    req('exit 2' in content[:500], f'{legacy_installer} must fail closed in this fork')

tauri_version = tuple(map(int, locked['tauri'].split('.')[:3]))
req(tauri_version >= (2, 11, 1),
    'Tauri regressed into the GHSA-7gmj-67g7-phm9 affected range')

for filename, window in [('default', 'main'), ('mini', 'mini')]:
    capability = json.loads(read(f'src-tauri/capabilities/{filename}.json'))
    req(capability.get('windows') == [window],
        f'{window} capability applies to unintended WebViews')
    permissions = set(capability.get('permissions', []))
    req({'allow-ui-commands', 'core:app:allow-version', 'core:event:default'} <= permissions,
        f'{window} capability is missing required application/event permissions')
    forbidden = {'dialog:allow-open', 'core:default', 'core:image:default',
                 'core:path:default', 'core:tray:default', 'core:menu:default',
                 'core:resources:default'}
    req(not permissions.intersection(forbidden),
        f'{window} capability exposes unnecessary native permissions')

print(f'Release invariants v{version}: OK')
