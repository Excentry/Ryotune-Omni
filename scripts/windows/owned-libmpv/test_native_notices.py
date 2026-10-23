import io
import tarfile
import unittest

from collect_native_notices import select_notices


class NativeNoticeTests(unittest.TestCase):
    def test_embedded_grants_and_named_texts_preserved_without_rewriting(self):
        stream = io.BytesIO()
        files = {"root/src/header.h": b"Copyright original holder\r\nfull source\r\n", "root/LICENSE": b"original terms\r\n", "root/src/plain.c": b"int value;", "root/data.bin": b"\0Copyright binary"}
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name, data in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            member = tarfile.TarInfo("root/COPYING")
            member.type = tarfile.SYMTYPE
            member.linkname = "LICENSE"
            archive.addfile(member)
        selected, links = select_notices(stream.getvalue())
        self.assertEqual(selected, {"src/header.h": files["root/src/header.h"], "LICENSE": files["root/LICENSE"]})
        self.assertEqual(links, [{"path": "COPYING", "target": "LICENSE"}])


if __name__ == "__main__":
    unittest.main()
