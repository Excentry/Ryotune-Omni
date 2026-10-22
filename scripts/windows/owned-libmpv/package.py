import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


def package(output):
    prepared = output / "prepared"
    candidate = output / "candidate"
    records = []
    for source in sorted((prepared / "sources").rglob("*")):
        if not source.is_file():
            continue
        if not re.match(r"(?i)^(?:licen[cs]e|copying|copyright|notice|authors)(?:[._-]|$)", source.name) and source.name not in {"FTL.TXT", "GPLv2.TXT"}:
            continue
        relative = source.relative_to(prepared / "sources")
        destination = candidate / "licenses" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        records.append({"path": destination.relative_to(candidate).as_posix(), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
    for source in output.glob("*-dependencies.json"):
        shutil.copyfile(source, candidate / source.name)
    for source in output.glob("*-options.json"):
        shutil.copyfile(source, candidate / source.name)
    shutil.copyfile(prepared / "recipe/sources.lock.json", candidate / "sources.lock.json")
    metadata = {
        "state": "candidate-not-approved-for-distribution",
        "source_archive": "source-inputs.tar.gz",
        "notice_files": records,
        "pending": ["complete per-file notice review", "Windows playback and provider regression matrix", "installer validation", "source hosting and retention review"],
    }
    (candidate / "candidate.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    lines = []
    for path in sorted(candidate.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            lines.append(f"{digest}  {path.relative_to(candidate).as_posix()}")
    (candidate / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    package(Path(sys.argv[1]).resolve())
