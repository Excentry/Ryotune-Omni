import argparse
import base64
import concurrent.futures
import hashlib
import io
import json
import re
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

from collect_rust_notices import download_repository, safe_relative


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Ryotunes-Omni-license-evidence"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError("Frontend evidence exceeds collection limit")
    return data


def package_hashes(data, identical_duplicates=None):
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            safe_relative(member.name)
            path = PurePosixPath(member.name)
            if path.parts[0] != "package":
                raise ValueError("Unexpected npm archive root")
            if member.isdir():
                continue
            if not member.isfile() or len(path.parts) < 2:
                raise ValueError("Unsupported npm archive entry")
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            checksum = hashlib.file_digest(archive.extractfile(member), "sha256").hexdigest()
            if relative in files:
                if files[relative] != checksum:
                    raise ValueError("Conflicting duplicate npm archive file")
                if identical_duplicates is not None:
                    identical_duplicates.append(member.name)
            files[relative] = checksum
    if "package.json" not in files:
        raise ValueError("npm archive lacks package metadata")
    return files


def preserve_package(item):
    name, version, expected = item
    url = f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='')}/{version}"
    raw_metadata = fetch(url)
    metadata = json.loads(raw_metadata)
    if metadata.get("name") != name or metadata.get("version") != version:
        raise ValueError("Registry package identity differs")
    dist = metadata["dist"]
    if not dist["tarball"].startswith("https://registry.npmjs.org/"):
        raise ValueError("Unexpected npm download host")
    data = fetch(dist["tarball"])
    algorithm, expected_integrity = dist["integrity"].split("-", 1)
    if algorithm != "sha512" or base64.b64encode(hashlib.sha512(data).digest()).decode() != expected_integrity:
        raise ValueError("npm package integrity differs from registry metadata")
    duplicates = []
    actual = package_hashes(data, duplicates)
    if "package.json" not in expected or any(actual.get(path) != checksum for path, checksum in expected.items()):
        raise ValueError(f"Published package differs from preserved build input: {name}@{version}")
    published_only = sorted(set(actual) - set(expected))
    repository = metadata.get("repository", {})
    repository = repository.get("url", "") if isinstance(repository, dict) else repository
    repository = repository.removeprefix("git+").removesuffix(".git")
    parsed = urllib.parse.urlsplit(repository)
    revision = metadata.get("gitHead", "")
    identity = None
    if parsed.hostname == "github.com" and re.fullmatch(r"[a-f0-9]{40}", revision):
        identity = parsed.path.strip("/"), revision
    if name == "locate-character" and re.fullmatch(r"[a-f0-9]{40}", revision):
        identity = "Rich-Harris/locate-character", revision
    evidence = download_repository((identity, [PurePosixPath(".")])) if identity else None
    return name, version, url, raw_metadata, data, expected, evidence, duplicates, published_only


def collect(inventory, source_archive, output):
    if output.exists():
        raise ValueError("Frontend supplement output must be new")
    report = json.loads(inventory.read_text(encoding="utf-8"))
    missing = {f"{item['name'].replace('/', '__')}@{item['version']}": item for item in report["packages"] if not item["root_notice_files_present"]}
    expected = {key: {} for key in missing}
    with tarfile.open(source_archive, "r|gz") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if member.isfile() and len(parts) > 2 and parts[0] == "packages" and parts[1] in expected:
                relative = PurePosixPath(*parts[2:]).as_posix()
                safe_relative(relative)
                if relative in expected[parts[1]]:
                    raise ValueError("Duplicate preserved frontend file")
                expected[parts[1]][relative] = hashlib.file_digest(archive.extractfile(member), "sha256").hexdigest()
    requests = [(item["name"], item["version"], expected[key]) for key, item in missing.items()]
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for name, version, url, raw_metadata, data, hashes, evidence, duplicates, published_only in executor.map(preserve_package, requests):
            prefix = f"{name.replace('/', '__')}@{version}"
            directory = output / "packages" / prefix
            directory.mkdir(parents=True)
            (directory / "registry-metadata.json").write_bytes(raw_metadata)
            (directory / "original-package.tgz").write_bytes(data)
            row = {"name": name, "version": version, "metadata_url": url, "metadata_sha256": hashlib.sha256(raw_metadata).hexdigest(), "archive_sha256": hashlib.sha256(data).hexdigest(), "verified_build_input_files": len(hashes), "published_files_absent_from_snapshot": published_only, "identical_duplicate_entries": duplicates, "repository_notices": []}
            if evidence:
                identity, repository_url, archive, notices, error = evidence
                row.update({"repository": identity[0], "revision": identity[1], "repository_url": repository_url, "repository_error": error})
                if archive is not None:
                    (directory / "repository-source.tar.gz").write_bytes(archive)
                    row["repository_archive_sha256"] = hashlib.sha256(archive).hexdigest()
                    for relative, content in notices.items():
                        target = directory / "repository-notices" / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(content)
                        row["repository_notices"].append({"path": target.relative_to(output).as_posix(), "sha256": hashlib.sha256(content).hexdigest()})
            rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    result = {"state": "preserved-files-match-original-npm-distributions-additional-files-listed-not-a-license-clearance", "packages": rows}
    (output / "inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.inventory.resolve(), args.source_archive.resolve(), args.output.resolve())
    print(f"Preserved {len(report['packages'])} original npm distributions; every preserved build-input file matches. Additional published files and identical duplicate entries are listed explicitly. No legal clearance inferred.")
    if any(item.get("repository_error") for item in report["packages"]):
        raise SystemExit(1)
