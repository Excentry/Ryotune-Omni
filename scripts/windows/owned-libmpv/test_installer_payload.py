import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from verify_installer_payload import verify


class InstallerPayloadTests(unittest.TestCase):
    def fixture(self, root):
        candidate = root / "candidate"
        candidate.mkdir()
        names = ("libmpv-2.dll", "mpv.lib", "source-inputs.tar.gz", "sources.lock.json", "NOTICE.md", "candidate.json", "REVIEW.md", "notice-inputs.lock.json", "licenses/toolchain/COPYING.RUNTIME")
        for name in names:
            path = candidate / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == "candidate.json":
                path.write_text(json.dumps({"source_archive": "source-inputs.tar.gz", "source_archive_sha256": hashlib.sha256((candidate / "source-inputs.tar.gz").read_bytes()).hexdigest()}))
            else:
                path.write_bytes(name.encode())
        sums = [f"{hashlib.sha256((candidate / name).read_bytes()).hexdigest()}  {name}" for name in names]
        (candidate / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
        application = root / "application-source.tar.gz"
        application.write_bytes(b"application source fixture")
        license = root / "LICENSE"
        license.write_bytes(b"project grant")
        extracted = root / "extracted"
        mapping = {"libmpv-2.dll": candidate / "libmpv-2.dll", "sources/libmpv-source-inputs.tar.gz": candidate / "source-inputs.tar.gz", "sources/application-source.tar.gz": application, "licenses/project/LICENSE": license, "licenses/libmpv/candidate-SHA256SUMS.txt": candidate / "SHA256SUMS.txt"}
        for name in ("NOTICE.md", "REVIEW.md", "sources.lock.json", "notice-inputs.lock.json"):
            mapping[f"licenses/libmpv/{name}"] = candidate / name
        mapping["licenses/libmpv/toolchain/COPYING.RUNTIME"] = candidate / "licenses/toolchain/COPYING.RUNTIME"
        for relative, source in mapping.items():
            target = extracted / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return candidate, extracted, application, license

    def test_payload_matches_original_dll_notices_and_source_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = verify(*self.fixture(root), root / "report.json")
            self.assertEqual(len(report["verified_files"]), 10)

    def test_different_dll_or_missing_notice_blocks_verification(self):
        for relative in ("libmpv-2.dll", "licenses/libmpv/toolchain/COPYING.RUNTIME", "sources/application-source.tar.gz"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                arguments = self.fixture(root)
                (arguments[1] / relative).write_bytes(b"wrong payload")
                with self.assertRaisesRegex(ValueError, "missing or mismatched"):
                    verify(*arguments, root / "report.json")
                self.assertFalse((root / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
