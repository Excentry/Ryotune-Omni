import json
import tempfile
import unittest
from pathlib import Path

from package import package
from smoke import verify_checksums


class CandidatePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        (self.root / "candidate").mkdir()
        (self.root / "prepared/sources/freetype/docs").mkdir(parents=True)
        (self.root / "prepared/recipe").mkdir(parents=True)
        (self.root / "prepared/recipe/sources.lock.json").write_text("{}")
        (self.root / "prepared/sources/freetype/docs/FTL.TXT").write_bytes(b"Example notice\r\n")
        for name in ("libmpv-2.dll", "mpv.lib", "source-inputs.tar.gz", "NOTICE.md"):
            (self.root / "candidate" / name).write_bytes(b"test fixture")

    def test_packaging_preserves_notice_bytes_and_matches_checksums(self):
        package(self.root)
        verify_checksums(self.root / "candidate")
        self.assertEqual((self.root / "candidate/licenses/freetype/docs/FTL.TXT").read_bytes(), b"Example notice\r\n")
        metadata = json.loads((self.root / "candidate/candidate.json").read_text())
        self.assertEqual(metadata["state"], "candidate-not-approved-for-distribution")

    def test_candidate_tampering_is_rejected(self):
        package(self.root)
        (self.root / "candidate/mpv.lib").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_checksums(self.root / "candidate")

    def test_missing_manifest_entry_is_rejected(self):
        package(self.root)
        sums = self.root / "candidate/SHA256SUMS.txt"
        sums.write_text("\n".join(line for line in sums.read_text().splitlines() if not line.endswith("  mpv.lib")) + "\n")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify_checksums(self.root / "candidate")


if __name__ == "__main__":
    unittest.main()
