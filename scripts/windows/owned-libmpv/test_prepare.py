import copy
import io
import json
import tempfile
import tarfile
import unittest
from pathlib import Path

import prepare


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def archive(self, entries):
        path = self.root / "input.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, data in entries:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return path

    def test_checked_in_lock_has_full_revisions_and_hashes(self):
        lock = prepare.load_lock(prepare.RECIPE / "sources.lock.json")
        self.assertEqual(len(lock["sources"]), 15)
        self.assertNotIn("subrandr", {source["name"] for source in lock["sources"]})

    def test_cached_tampering_is_rejected_even_offline(self):
        path = self.root / "example.tar.gz"
        path.write_bytes(b"tampered")
        source = {"name": "example", "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            prepare.acquire(source, self.root, True)

    def test_missing_offline_input_fails(self):
        with self.assertRaisesRegex(ValueError, "unavailable offline"):
            prepare.acquire({"name": "missing", "sha256": "0" * 64}, self.root, True)

    def test_extracts_root_and_preserves_notice_bytes(self):
        revision = "a" * 40
        data = b"Copyright example\r\nPermission grant\n"
        archive = self.archive([(f"example-{revision}/LICENSE", data)])
        prepare.extract_source(archive, self.root / "output", revision)
        self.assertEqual((self.root / "output/LICENSE").read_bytes(), data)

    def test_archive_parent_traversal_is_rejected(self):
        revision = "a" * 40
        archive = self.archive([(f"example-{revision}/../../outside", b"unsafe")])
        with self.assertRaises(ValueError):
            prepare.extract_source(archive, self.root / "output", revision)
        self.assertFalse((self.root / "outside").exists())

    def test_absolute_archive_path_is_rejected(self):
        archive = self.archive([("/absolute/file", b"unsafe")])
        with self.assertRaises(ValueError):
            prepare.extract_source(archive, self.root / "output", "a" * 40)

    def test_escaping_symlink_is_rejected(self):
        revision = "a" * 40
        path = self.root / "symlink.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            member = tarfile.TarInfo(f"example-{revision}/link")
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside"
            archive.addfile(member)
        with self.assertRaises(tarfile.FilterError):
            prepare.extract_source(path, self.root / "output", revision)

    def test_unpinned_revision_and_hash_are_rejected(self):
        original = json.loads((prepare.RECIPE / "sources.lock.json").read_text())
        for field, value in (("revision", "main"), ("sha256", None), ("destination", "../outside")):
            with self.subTest(field=field):
                lock = copy.deepcopy(original)
                lock["sources"][0][field] = value
                path = self.root / "lock.json"
                path.write_text(json.dumps(lock))
                with self.assertRaises(ValueError):
                    prepare.load_lock(path)


if __name__ == "__main__":
    unittest.main()
