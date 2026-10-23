import tempfile
import unittest
from pathlib import Path

from imports import verify_pe_imports


class ImportReviewTests(unittest.TestCase):
    def verify(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pe-imports.txt"
            path.write_text(text, encoding="utf-8")
            return verify_pe_imports(path)

    def test_known_windows_imports_are_case_insensitive(self):
        self.assertEqual(self.verify("\tDLL Name: KERNEL32.dll\n\tDLL Name: api-ms-win-crt-runtime-l1-1-0.dll\n"), ["api-ms-win-crt-runtime-l1-1-0.dll", "kernel32.dll"])

    def test_shared_compiler_runtime_and_unknown_dlls_block_packaging(self):
        for name in ("libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll", "unreviewed.dll"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unreviewed"):
                self.verify(f"\tDLL Name: KERNEL32.dll\n\tDLL Name: {name}\n")

    def test_missing_import_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no DLL imports"):
            self.verify("not an objdump report")


if __name__ == "__main__":
    unittest.main()
