import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from verify_vendor_sources import verify


class VendorSourceTests(unittest.TestCase):
    def test_original_source_passes_and_modified_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "vendor/example"
            package.mkdir(parents=True)
            source = package / "lib.rs"
            source.write_bytes(b"original source\r\n")
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            (package / ".cargo-checksum.json").write_text(json.dumps({"files": {"lib.rs": checksum}}))
            self.assertEqual(verify(root / "vendor", root / "pass.json")["verified_files"], 1)
            source.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify(root / "vendor", root / "failure.json")
            self.assertFalse((root / "failure.json").exists())

    def test_checksum_path_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "vendor/example"
            package.mkdir(parents=True)
            (package / ".cargo-checksum.json").write_text(json.dumps({"files": {"../../outside": "0" * 64}}))
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                verify(root / "vendor", root / "report.json")

    def test_missing_packages_and_existing_reports_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "No vendored"):
                verify(root / "vendor", root / "report.json")
            output = root / "existing.json"
            output.write_text("existing evidence")
            with self.assertRaisesRegex(ValueError, "must be new"):
                verify(root / "vendor", output)
            self.assertEqual(output.read_text(), "existing evidence")


if __name__ == "__main__":
    unittest.main()
