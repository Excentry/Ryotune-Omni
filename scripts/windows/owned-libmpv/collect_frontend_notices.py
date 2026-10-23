import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def collect(node_modules, output):
    if output.exists():
        raise ValueError("Notice output must be new; existing evidence will not be overwritten")
    store = node_modules / ".pnpm"
    if not store.is_dir():
        raise ValueError("Expected an installed pnpm dependency tree")
    manifests = sorted(store.glob("*/node_modules/*/package.json"))
    manifests += sorted(store.glob("*/node_modules/@*/*/package.json"))
    packages = {}
    for manifest in manifests:
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        name = metadata.get("name", "")
        version = metadata.get("version", "")
        if not name or not version or (name, version) in packages:
            continue
        if not re.fullmatch(r"(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+", name) or not re.fullmatch(r"[a-zA-Z0-9_.+-]+", version):
            raise ValueError("Unsafe dependency name or version")
        target = output / "packages" / f"{name.replace('/', '__')}@{version}"
        target.mkdir(parents=True)
        selected = [manifest]
        license_files = []
        for path in sorted(manifest.parent.iterdir()):
            if path.is_file() and re.match(r"(?i)^(?:licen[cs]e|copying|copyright|notice|authors)(?:[._-]|$)", path.name):
                license_files.append(path)
                selected.append(path)
            elif path.is_dir() and path.name.lower() in {"licenses", "licences"}:
                nested = [item for item in sorted(path.rglob("*")) if item.is_file()]
                license_files.extend(nested)
                selected.extend(nested)
        if not license_files:
            selected += [path for path in sorted(manifest.parent.glob("README*")) if path.is_file()]
        files = []
        for path in selected:
            destination = target / path.relative_to(manifest.parent)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            files.append({"path": destination.relative_to(output).as_posix(), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
        packages[(name, version)] = {"name": name, "version": version, "declared_license": metadata.get("license"), "root_notice_files_present": bool(license_files), "files": files}
    if not packages:
        raise ValueError("No package manifests found in pnpm dependency tree")
    inventory = {"state": "installed-dependency-notice-superset-not-a-bundle-license-clearance", "packages": list(packages.values()), "missing_root_notice_files": [f"{name}@{version}" for (name, version), record in packages.items() if not record["root_notice_files_present"]]}
    (output / "frontend-notice-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-modules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = collect(args.node_modules.resolve(), args.output.resolve())
    print(f"Preserved notices/metadata for {len(inventory['packages'])} installed packages; {len(inventory['missing_root_notice_files'])} lack a root notice file and require review")
