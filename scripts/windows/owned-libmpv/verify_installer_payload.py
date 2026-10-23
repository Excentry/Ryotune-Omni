import argparse
import json
from pathlib import Path

from prepare import digest
from smoke import verify_checksums


def verify(candidate, extracted, application_source, project_license, report_path):
    if report_path.exists():
        raise ValueError("Installer verification report must be new")
    verify_checksums(candidate)
    required = {
        "libmpv-2.dll": candidate / "libmpv-2.dll",
        "sources/libmpv-source-inputs.tar.gz": candidate / "source-inputs.tar.gz",
        "sources/application-source.tar.gz": application_source,
        "licenses/project/LICENSE": project_license,
        "licenses/libmpv/candidate-SHA256SUMS.txt": candidate / "SHA256SUMS.txt",
    }
    for name in ("NOTICE.md", "REVIEW.md", "sources.lock.json", "notice-inputs.lock.json"):
        required[f"licenses/libmpv/{name}"] = candidate / name
    for source in sorted((candidate / "licenses").rglob("*")):
        if source.is_file():
            required[f"licenses/libmpv/{source.relative_to(candidate / 'licenses').as_posix()}"] = source
    checked = []
    for relative, source in required.items():
        target = extracted / relative
        expected = digest(source)
        if not target.is_file() or digest(target) != expected:
            raise ValueError(f"Installer payload missing or mismatched: {relative}")
        checked.append({"path": relative, "sha256": expected})
    report = {"state": "extracted-payload-matches-frozen-inputs-not-a-clean-install-test", "verified_files": checked}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument("--application-source", type=Path, required=True)
    parser.add_argument("--project-license", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.candidate.resolve(), args.extracted.resolve(), args.application_source.resolve(), args.project_license.resolve(), args.report.resolve())
    print(f"Verified {len(result['verified_files'])} exact DLL, license and source payload files; clean installation remains separate")
