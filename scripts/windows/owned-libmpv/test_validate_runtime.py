import functools
import http.server
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from validate_runtime import FixtureHandler, certificate_rejection, encode_fixtures, run


class RuntimeValidationTests(unittest.TestCase):
    def test_streaming_encoders_write_segments_inside_fixture_directories(self):
        with tempfile.TemporaryDirectory() as temporary, patch("validate_runtime.subprocess.run") as command:
            root = Path(temporary) / "fixtures"
            encode_fixtures("fixture-ffmpeg", root)
            streaming = [call for call in command.call_args_list if "-hls_time" in call.args[0] or "-seg_duration" in call.args[0]]
            self.assertEqual(len(streaming), 2)
            self.assertEqual({call.kwargs["cwd"] for call in streaming}, {root / "hls", root / "dash"})
            self.assertTrue(all(not Path(call.args[0][-1]).is_absolute() for call in streaming))
            self.assertTrue(all(call.kwargs["check"] for call in command.call_args_list))

    def test_existing_evidence_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "must be new"):
                run(root / "unused.dll", root, "unused-ffmpeg", False)

    def test_fixture_server_requires_header_and_serves_nested_segments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dash").mkdir()
            (root / "dash/init-stream0.m4s").write_bytes(b"fixture segment")
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(FixtureHandler, directory=str(root)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/dash/init-stream0.m4s"
                with self.assertRaises(urllib.error.HTTPError) as rejected:
                    urllib.request.urlopen(url, timeout=5)
                self.assertEqual(rejected.exception.code, 403)
                rejected.exception.close()
                request = urllib.request.Request(url, headers={"X-Ryotunes-Fixture": "owned-libmpv"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.read(), b"fixture segment")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_certificate_check_does_not_confuse_url_or_network_failure_with_rejection(self):
        self.assertTrue(certificate_rejection("InitializeSecurityContext failed: SEC_E_CERT_EXPIRED (0x80090328)"))
        self.assertFalse(certificate_rejection("Opening https://expired.badssl.com/\nConnection timed out"))
        self.assertFalse(certificate_rejection("Opening failed: unrecognized file format"))
        self.assertFalse(certificate_rejection("The certificate is not expired"))


if __name__ == "__main__":
    unittest.main()
