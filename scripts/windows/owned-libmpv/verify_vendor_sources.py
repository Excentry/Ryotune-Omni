import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify_file(item):
    path, expected = item
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"Vendored source checksum mismatch: {path}")


def verify(vendor, output):
    if output.exists():
        raise ValueError("Verification report must be new")
    manifests = sorted(vendor.glob("*/.cargo-checksum.json"))
    if not manifests:
        raise ValueError("No vendored Cargo checksum manifests found")
    files = []
    for manifest in manifests:
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        for relative, expected in metadata["files"].items():
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
                raise ValueError("Unsafe vendored checksum path")
            target = manifest.parent / relative
            if not target.resolve().is_relative_to(manifest.parent.resolve()):
                raise ValueError("Vendored source escapes its package directory")
            files.append((target, expected))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for _ in executor.map(verify_file, files):
            pass
    report = {"state": "listed-vendored-file-checksums-verified-not-a-license-clearance", "packages": len(manifests), "verified_files": len(files)}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.vendor.resolve(), args.output.resolve())
    print(f"Verified {result['verified_files']} source-file checksums in {result['packages']} vendored packages")
