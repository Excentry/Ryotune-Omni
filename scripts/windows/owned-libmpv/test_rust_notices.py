import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from collect_rust_notices import NOTICE_NAME, archive_notices, collect, repository_identity, safe_relative


class RustNoticeTests(unittest.TestCase):
    def test_supplemental_notice_names_are_included(self):
        for name in ("THIRD-PARTY-LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES", "COPYING.RUNTIME"):
            self.assertIsNotNone(NOTICE_NAME.match(name))

    def test_git_source_overrides_stale_manifest_repository(self):
        revision = "a" * 40
        result = repository_identity(f"git+https://github.com/owner/fork?rev={revision}#{revision}", {"repository": "https://github.com/other/repo"}, {})
        self.assertEqual(result, ("owner/fork", revision))
        self.assertIsNone(repository_identity("registry+index", {"repository": "https://example.com/repo"}, {"git": {"sha1": revision}}))

    def test_archive_preserves_root_and_package_notices_not_unrelated_tests(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name in ("repo/LICENSE", "repo/crates/NOTICE", "repo/crates/core/LICENSE-MIT", "repo/other/LICENSE"):
                data = name.encode() + b"\r\n"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        notices = archive_notices(stream.getvalue(), [PurePosixPath("crates/core")])
        self.assertEqual(set(notices), {"LICENSE", "crates/NOTICE", "crates/core/LICENSE-MIT"})
        self.assertEqual(notices["LICENSE"], b"repo/LICENSE\r\n")

    def test_unsafe_paths_rejected(self):
        for value in ("../LICENSE", "/LICENSE", "C:LICENSE", "a\\LICENSE"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_relative(value)

    def test_notices_preserved_and_modified_vendor_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "vendor/example-1.0.0"
            package.mkdir(parents=True)
            files = {"Cargo.toml": b'[package]\nname="example"\nversion="1.0.0"\nlicense="MIT"\n', "LICENSE": b"original grant\r\n"}
            for name, data in files.items():
                (package / name).write_bytes(data)
            (package / ".cargo-checksum.json").write_text(json.dumps({"files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}))
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"packages": [{"name": "example", "version": "1.0.0", "source": "registry+example"}]}))
            result = collect(root / "vendor", inventory, root / "notices")
            self.assertEqual(result["root_notices_missing_in_vendor"], [])
            self.assertEqual((root / "notices/packages/example-1.0.0/LICENSE").read_bytes(), files["LICENSE"])
            with self.assertRaisesRegex(ValueError, "must be new"):
                collect(root / "vendor", inventory, root / "notices")
            (package / "LICENSE").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                collect(root / "vendor", inventory, root / "failure")


if __name__ == "__main__":
    unittest.main()
