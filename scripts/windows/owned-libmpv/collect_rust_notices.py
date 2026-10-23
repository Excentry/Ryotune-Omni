import argparse
import concurrent.futures
import hashlib
import io
import json
import re
import tarfile
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


NOTICE_NAME = re.compile(r"(?i)^(?:(?:licen[cs]e|copying|copyright|notice|author)s?|third[-_]party[-_](?:licen[cs]e|notice)s?)(?:[._-]|$)")


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("Unsafe source or notice path")
    return path


def checked_bytes(package, relative, checksums):
    safe_relative(relative)
    path = package / relative
    if not path.resolve().is_relative_to(package.resolve()):
        raise ValueError("Notice escapes vendored package")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != checksums.get(relative):
        raise ValueError(f"Vendored notice checksum mismatch: {package.name}/{relative}")
    return data


def repository_identity(source, metadata, vcs):
    if source.startswith("git+"):
        parsed = urllib.parse.urlsplit(source[4:])
        revision = parsed.fragment
        repository = parsed.path.strip("/").removesuffix(".git")
    else:
        parsed = urllib.parse.urlsplit(metadata.get("repository", "").removesuffix(".git"))
        revision = vcs.get("git", {}).get("sha1", "")
        repository = parsed.path.strip("/")
    if parsed.scheme != "https" or parsed.hostname != "github.com" or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        return None
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        return None
    return repository, revision


def archive_notices(data, package_paths):
    notices = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            relative = PurePosixPath(*parts[1:])
            safe_relative(relative.as_posix())
            if not member.isfile() or not NOTICE_NAME.match(relative.name):
                continue
            if len(relative.parts) > 1 and not any(
                path is not None and (relative.is_relative_to(path) or path.is_relative_to(relative.parent))
                for path in package_paths
            ):
                continue
            if member.size > 2 * 1024 * 1024:
                raise ValueError("Unexpectedly large repository notice")
            name = relative.as_posix()
            if name in notices:
                raise ValueError("Duplicate repository notice")
            notices[name] = archive.extractfile(member).read()
    return notices


def download_repository(item):
    identity, package_paths = item
    repository, revision = identity
    url = f"https://codeload.github.com/{repository}/tar.gz/{revision}"
    request = urllib.request.Request(url, headers={"User-Agent": "Ryotunes-Omni-license-evidence"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("Repository archive exceeds collection limit")
        return identity, url, data, archive_notices(data, package_paths), None
    except (OSError, ValueError, tarfile.TarError) as error:
        return identity, url, None, {}, f"{type(error).__name__}: {error}"


def collect(vendor, inventory, output, fetch_missing=False):
    if output.exists():
        raise ValueError("Notice output must be new")
    packages = json.loads(inventory.read_text(encoding="utf-8"))["packages"]
    rows = []
    requests = {}
    for package in packages:
        if not package["source"]:
            continue
        name = package["name"]
        version = package["version"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not re.fullmatch(r"[A-Za-z0-9_.+-]+", version):
            raise ValueError("Unsafe Cargo package identity")
        directory = vendor / f"{name}-{version}"
        checksums = json.loads((directory / ".cargo-checksum.json").read_text(encoding="utf-8"))["files"]
        metadata = tomllib.loads(checked_bytes(directory, "Cargo.toml", checksums).decode("utf-8"))["package"]
        if metadata["name"] != name or metadata["version"] != version:
            raise ValueError("Vendored package identity differs from inventory")
        paths = {relative for relative in checksums if NOTICE_NAME.match(PurePosixPath(relative).name) or any(part.lower() in {"licenses", "licences"} for part in PurePosixPath(relative).parts[:-1])}
        license_file = metadata.get("license-file")
        if license_file:
            paths.add(license_file)
        notices = []
        for relative in sorted(paths):
            data = checked_bytes(directory, relative, checksums)
            target = output / "packages" / directory.name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            notices.append({"path": target.relative_to(output).as_posix(), "sha256": hashlib.sha256(data).hexdigest()})
        root_notices = [relative for relative in paths if len(PurePosixPath(relative).parts) == 1]
        row = {"name": name, "version": version, "declared_license": metadata.get("license"), "license_file": license_file, "notices": notices, "root_notice_present": bool(root_notices)}
        if not root_notices:
            vcs = json.loads(checked_bytes(directory, ".cargo_vcs_info.json", checksums)) if ".cargo_vcs_info.json" in checksums else {}
            identity = repository_identity(package["source"], metadata, vcs)
            row["vcs_dirty"] = vcs.get("git", {}).get("dirty", False)
            row["repository_evidence"] = "/".join(identity) if identity else None
            if identity:
                path = vcs.get("path_in_vcs")
                if path:
                    safe_relative(path)
                requests.setdefault(identity, []).append(PurePosixPath(path) if path is not None else None)
        rows.append(row)
    repositories = []
    if fetch_missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for identity, url, data, notices, error in executor.map(download_repository, requests.items()):
                repository, revision = identity
                record = {"repository": repository, "revision": revision, "url": url, "error": error, "notices": []}
                if data is not None:
                    target = output / "repository-sources" / f"{repository.replace('/', '__')}-{revision}.tar.gz"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    record["archive"] = target.relative_to(output).as_posix()
                    record["sha256"] = hashlib.sha256(data).hexdigest()
                    for relative, content in notices.items():
                        target = output / "repository-notices" / repository.replace("/", "__") / revision / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(content)
                        record["notices"].append({"path": target.relative_to(output).as_posix(), "sha256": hashlib.sha256(content).hexdigest()})
                repositories.append(record)
    report = {"state": "original-notice-evidence-not-a-license-clearance", "packages": rows, "repositories": repositories, "root_notices_missing_in_vendor": [f"{row['name']}@{row['version']}" for row in rows if not row["root_notice_present"]]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch-missing", action="store_true")
    args = parser.parse_args()
    report = collect(args.vendor.resolve(), args.inventory.resolve(), args.output.resolve(), args.fetch_missing)
    failures = sum(bool(item["error"]) for item in report["repositories"])
    print(f"Collected original notices for {len(report['packages'])} external packages; {len(report['root_notices_missing_in_vendor'])} lack root notices; {len(report['repositories'])} repository snapshots, {failures} download failures. No legal clearance inferred.")
    if failures:
        raise SystemExit(1)
