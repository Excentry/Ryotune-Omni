import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

from collect_rust_notices import NOTICE_NAME, safe_relative
from smoke import verify_checksums


GRANT = re.compile(rb"copyright|permission is hereby granted|redistribution and use|SPDX-License-Identifier|public domain|Source Code Form|GNU (?:Lesser )?General Public License", re.IGNORECASE)


def select_notices(data):
    selected = {}
    links = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            path = safe_relative(member.name)
            if len(path.parts) < 2:
                continue
            relative = PurePosixPath(*path.parts[1:])
            named_notice = bool(NOTICE_NAME.match(relative.name)) or any(part.lower() in {"licenses", "licences"} for part in relative.parts[:-1])
            if member.issym() or member.islnk():
                if named_notice:
                    links.append({"path": relative.as_posix(), "target": member.linkname})
                continue
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            prefix = stream.read(65536)
            if named_notice or (b"\0" not in prefix and GRANT.search(prefix)):
                name = relative.as_posix()
                if name in selected:
                    raise ValueError("Duplicate source notice path")
                selected[name] = prefix + stream.read()
    return selected, links


def collect(candidate, output):
    if output.exists():
        raise ValueError("Native notice output must be new")
    verify_checksums(candidate)
    lock = json.loads((candidate / "sources.lock.json").read_text(encoding="utf-8"))
    rows = []
    with tarfile.open(candidate / "source-inputs.tar.gz", mode="r:gz") as bundle:
        for source in lock["sources"]:
            archive_path = f"archives/{source['name']}.tar.gz"
            data = bundle.extractfile(archive_path).read()
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                raise ValueError("Native source archive differs from candidate lock")
            notices, links = select_notices(data)
            files = []
            for relative, content in notices.items():
                target = output / "original-files" / source["name"] / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                files.append({"path": target.relative_to(output).as_posix(), "sha256": hashlib.sha256(content).hexdigest()})
            rows.append({"source": source["name"], "revision": source["revision"], "archive_sha256": source["sha256"], "files": files, "notice_links_not_materialized": links})
    result = {"state": "original-notice-and-source-superset-not-per-object-license-clearance", "selection": "notice filenames/directories or grant/copyright markers in first 65536 bytes; selected files preserved whole and unchanged", "sources": rows}
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.candidate.resolve(), args.output.resolve())
    print(f"Preserved {sum(len(item['files']) for item in report['sources'])} original notice-bearing files from {len(report['sources'])} hash-verified native snapshots; compiled-file mapping and legal review remain separate.")
