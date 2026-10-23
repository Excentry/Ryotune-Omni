import base64
import hashlib
import io
import json
import tarfile
import unittest
from unittest.mock import patch

from collect_frontend_supplement import package_hashes, preserve_package


class FrontendSupplementTests(unittest.TestCase):
    def archive(self, names=("package/package.json", "package/index.js")):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name in names:
                data = name.encode() + b"\r\n"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return stream.getvalue()

    def test_original_distribution_hashes_preserve_bytes(self):
        data = self.archive()
        self.assertEqual(package_hashes(data)["index.js"], hashlib.sha256(b"package/index.js\r\n").hexdigest())

    def test_identical_duplicates_recorded_and_conflicting_entries_rejected(self):
        duplicates = []
        package_hashes(self.archive(("package/package.json", "package/package.json")), duplicates)
        self.assertEqual(duplicates, ["package/package.json"])
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            package_hashes(self.archive(("package/package.json", "package/./package.json")))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            package_hashes(self.archive(("package/../outside",)))

    def test_registry_integrity_and_source_pairing_are_both_required(self):
        data = self.archive()
        metadata = {"name": "example", "version": "1.0.0", "dist": {"tarball": "https://registry.npmjs.org/example/-/example.tgz", "integrity": "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()}}
        with patch("collect_frontend_supplement.fetch", side_effect=[json.dumps(metadata).encode(), data]):
            result = preserve_package(("example", "1.0.0", package_hashes(data)))
            self.assertEqual(len(result[5]), 2)
        expected = package_hashes(data)
        del expected["index.js"]
        with patch("collect_frontend_supplement.fetch", side_effect=[json.dumps(metadata).encode(), data]):
            self.assertEqual(preserve_package(("example", "1.0.0", expected))[8], ["index.js"])
        with patch("collect_frontend_supplement.fetch", side_effect=[json.dumps(metadata).encode(), data]), self.assertRaisesRegex(ValueError, "differs from preserved"):
            preserve_package(("example", "1.0.0", {"index.js": "0" * 64}))
        metadata["dist"]["integrity"] = "sha512-invalid"
        with patch("collect_frontend_supplement.fetch", side_effect=[json.dumps(metadata).encode(), data]), self.assertRaisesRegex(ValueError, "integrity differs"):
            preserve_package(("example", "1.0.0", package_hashes(data)))


if __name__ == "__main__":
    unittest.main()
