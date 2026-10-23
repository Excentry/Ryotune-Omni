import json
import tempfile
import unittest
from pathlib import Path

from collect_frontend_notices import collect


class FrontendNoticeTests(unittest.TestCase):
    def test_scoped_and_unscoped_packages_preserve_notices_and_flag_missing_texts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = (
                ("example@1.0.0/node_modules/example", "example", True),
                ("@scope+icons@1.0.0/node_modules/@scope/icons", "@scope/icons", False),
            )
            for location, name, notice in packages:
                package = root / "node_modules/.pnpm" / location
                package.mkdir(parents=True)
                (package / "package.json").write_text(json.dumps({"name": name, "version": "1.0.0", "license": "MIT"}))
                (package / ("LICENSE" if notice else "README.md")).write_bytes(b"Original notice\r\n")
                if notice:
                    (package / "LICENSES").mkdir()
                    (package / "LICENSES/extra.txt").write_bytes(b"Nested grant\r\n")
            inventory = collect(root / "node_modules", root / "output")
            self.assertEqual(len(inventory["packages"]), 2)
            self.assertEqual(inventory["missing_root_notice_files"], ["@scope/icons@1.0.0"])
            self.assertEqual((root / "output/packages/example@1.0.0/LICENSE").read_bytes(), b"Original notice\r\n")
            self.assertEqual((root / "output/packages/example@1.0.0/LICENSES/extra.txt").read_bytes(), b"Nested grant\r\n")
            self.assertEqual((root / "output/packages/@scope__icons@1.0.0/README.md").read_bytes(), b"Original notice\r\n")

    def test_existing_notice_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "must be new"):
                collect(root / "unused", root)


if __name__ == "__main__":
    unittest.main()
