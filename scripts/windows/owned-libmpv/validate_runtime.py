import argparse
import ctypes
import functools
import hashlib
import http.server
import json
import locale
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from imports import verify_pe_imports
from smoke import verify_checksums


FORMATS = (
    ("pcm", "pcm_s16le", "audio.wav"),
    ("mp3", "libmp3lame", "audio.mp3"),
    ("aac", "aac", "audio.m4a"),
    ("opus", "libopus", "audio.opus"),
    ("vorbis", "libvorbis", "audio.ogg"),
    ("flac", "flac", "audio.flac"),
    ("alac", "alac", "lossless.m4a"),
)


def encode_fixtures(ffmpeg, directory):
    directory.mkdir(parents=True, exist_ok=False)
    base = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4", "-ac", "2"]
    for _, codec, filename in FORMATS:
        subprocess.run([*base, "-c:a", codec, str(directory / filename)], check=True, capture_output=True, timeout=30)
    for name, options, filename in (
        ("hls", ["-f", "hls", "-hls_time", "1", "-hls_playlist_type", "vod"], "audio.m3u8"),
        ("dash", ["-f", "dash", "-seg_duration", "1", "-use_template", "1", "-use_timeline", "1"], "audio.mpd"),
    ):
        target = directory / name
        target.mkdir()
        subprocess.run([*base, "-c:a", "aac", *options, filename], cwd=target, check=True, capture_output=True, timeout=30)


class Player:
    def __init__(self, library, output="null", log=None):
        self.library = library
        self.handle = library.mpv_create()
        if not self.handle:
            raise RuntimeError("mpv_create failed")
        try:
            if log:
                self.check(library.mpv_set_option_string(self.handle, b"log-file", str(log).encode()))
                self.check(library.mpv_set_option_string(self.handle, b"msg-level", b"all=v"))
            for key, value in (("config", "no"), ("terminal", "no"), ("vo", "null"), ("vid", "no"), ("ao", output), ("volume", "10"), ("pause", "yes"), ("idle", "yes"), ("keep-open", "yes"), ("tls-verify", "yes"), ("network-timeout", "10")):
                self.check(library.mpv_set_option_string(self.handle, key.encode(), value.encode()))
            self.check(library.mpv_initialize(self.handle))
        except Exception:
            self.close()
            raise

    def check(self, code):
        if code < 0:
            raise RuntimeError(self.library.mpv_error_string(code).decode("utf-8"))

    def set(self, name, value):
        self.check(self.library.mpv_set_property_string(self.handle, name.encode(), str(value).encode()))

    def command(self, *arguments):
        values = (ctypes.c_char_p * (len(arguments) + 1))(*[str(value).encode() for value in arguments], None)
        self.check(self.library.mpv_command(self.handle, values))

    def number(self, name):
        value = ctypes.c_double()
        self.check(self.library.mpv_get_property(self.handle, name.encode(), 5, ctypes.byref(value)))
        return value.value

    def flag(self, name):
        value = ctypes.c_int()
        self.check(self.library.mpv_get_property(self.handle, name.encode(), 3, ctypes.byref(value)))
        return bool(value.value)

    def string(self, name):
        pointer = self.library.mpv_get_property_string(self.handle, name.encode())
        if not pointer:
            return None
        try:
            return ctypes.string_at(pointer).decode("utf-8")
        finally:
            self.library.mpv_free(pointer)

    def wait(self, predicate, description, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return
            except RuntimeError:
                pass
            time.sleep(0.02)
        raise RuntimeError(f"Timed out: {description}")

    def load(self, source):
        self.command("loadfile", source, "replace")
        self.wait(lambda: self.number("duration") >= 3.5 and self.string("audio-codec-name") is not None, "audio readiness")

    def close(self):
        if self.handle:
            self.library.mpv_terminate_destroy(self.handle)
            self.handle = None


def load_library(dll):
    library = ctypes.CDLL(str(dll))
    signatures = {
        "mpv_create": ([], ctypes.c_void_p),
        "mpv_initialize": ([ctypes.c_void_p], ctypes.c_int),
        "mpv_set_option_string": ([ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
        "mpv_set_property_string": ([ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
        "mpv_get_property": ([ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p], ctypes.c_int),
        "mpv_get_property_string": ([ctypes.c_void_p, ctypes.c_char_p], ctypes.c_void_p),
        "mpv_command": ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)], ctypes.c_int),
        "mpv_error_string": ([ctypes.c_int], ctypes.c_char_p),
        "mpv_free": ([ctypes.c_void_p], None),
        "mpv_terminate_destroy": ([ctypes.c_void_p], None),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(library, name)
        function.argtypes = arguments
        function.restype = result
    return library


def exercise(library, source, output="null", headers=False, log=None):
    player = Player(library, output, log)
    try:
        if headers:
            player.set("http-header-fields", "X-Ryotunes-Fixture: owned-libmpv")
        player.load(source)
        duration = player.number("duration")
        codec = player.string("audio-codec-name")
        player.set("af", "lavfi=[volume=-6dB],rubberband=pitch-scale=1.122462,lavfi=[aecho=0.8:0.9:40:0.2],lavfi=[bass=g=3:f=110:w=0.6],lavfi=[stereowiden=delay=20:feedback=0.3:crossfeed=0.3:drymix=0.7]")
        player.set("speed", "1.25")
        player.command("seek", "1", "absolute+exact")
        player.wait(lambda: abs(player.number("time-pos") - 1) < 0.15, "seek position")
        player.set("pause", "no")
        player.wait(lambda: player.number("time-pos") > 1.25, "playback progress")
        active_output = player.string("current-ao")
        if active_output != output:
            raise RuntimeError(f"Expected output {output}, got {active_output}")
        player.set("pause", "yes")
        if not player.flag("pause"):
            raise RuntimeError("Pause state did not change")
        player.command("seek", str(duration - 0.4), "absolute+exact")
        player.set("pause", "no")
        player.wait(lambda: player.flag("eof-reached"), "EOF")
        player.command("stop")
        player.wait(lambda: player.flag("idle-active"), "stop idle state")
        return {"codec": codec, "duration": duration, "output": active_output, "seek_progress_pause_eof_stop": "pass"}
    finally:
        player.close()


class FixtureHandler(http.server.SimpleHTTPRequestHandler):
    requests = []

    def do_GET(self):
        authorized = self.headers.get("X-Ryotunes-Fixture") == "owned-libmpv"
        self.requests.append({"path": self.path, "header_accepted": authorized})
        if not authorized:
            self.send_error(403)
            return
        super().do_GET()

    def log_message(self, *_):
        pass


def certificate_rejection(log):
    return bool(re.search(r"\b(?:CERT_E_EXPIRED|SEC_E_CERT_EXPIRED|0x80090328|0x800b0101)\b", log, re.IGNORECASE))


def verify_expired_certificate(library, log):
    player = Player(library, log=log)
    try:
        try:
            player.load("https://expired.badssl.com/")
        except RuntimeError:
            pass
    finally:
        player.close()
    if not certificate_rejection(log.read_text(encoding="utf-8", errors="replace")):
        raise RuntimeError("Expired-certificate request did not produce a verified certificate rejection")
    return {"state": "certificate-rejected", "endpoint": "https://expired.badssl.com/", "tls_verify": True}


def run(dll, output, ffmpeg, wasapi, https=False):
    if output.exists():
        raise ValueError("Output directory must be new; existing evidence will not be overwritten")
    verify_checksums(dll.parent)
    imports = verify_pe_imports(dll.parent / "pe-imports.txt")
    output.mkdir(parents=True)
    with dll.open("rb") as stream:
        dll_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"dll_sha256": dll_hash, "reported_imports": imports, "tests": {}, "limits": ["No authenticated provider validation", "No HTTPS/Schannel validation", "No measured gapless continuity", "WASAPI progress is not human confirmation of audible output", "No clean VM installation validation"]}
    locale.setlocale(locale.LC_NUMERIC, "C")
    search_path = os.add_dll_directory(str(dll.parent))
    try:
        fixtures = output / "fixtures"
        encode_fixtures(ffmpeg, fixtures)
        library = load_library(dll)
        for name, _, filename in FORMATS:
            report["tests"][name] = exercise(library, str(fixtures / filename), log=output / f"{name}.log")
            print(f"PASS: {name}", flush=True)
        handler = functools.partial(FixtureHandler, directory=str(fixtures))
        FixtureHandler.requests = []
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for name, path in (("http_headers", "audio.wav"), ("hls", "hls/audio.m3u8"), ("dash", "dash/audio.mpd")):
                report["tests"][name] = exercise(library, f"http://127.0.0.1:{server.server_port}/{path}", headers=True, log=output / f"{name}.log")
                print(f"PASS: {name}", flush=True)
            if not FixtureHandler.requests or not all(item["header_accepted"] for item in FixtureHandler.requests):
                raise RuntimeError("HTTP fixture request headers were missing")
        finally:
            report["http_requests"] = list(FixtureHandler.requests)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        if wasapi:
            report["tests"]["wasapi"] = exercise(library, str(fixtures / "audio.wav"), "wasapi", log=output / "wasapi.log")
            print("PASS: WASAPI progress and lifecycle; audible confirmation remains manual", flush=True)
        if https:
            report["tests"]["https_schannel"] = exercise(library, "https://upload.wikimedia.org/wikipedia/commons/c/c8/Example.ogg", log=output / "https.log")
            report["tests"]["expired_certificate"] = verify_expired_certificate(library, output / "expired-certificate.log")
            report["limits"].remove("No HTTPS/Schannel validation")
            print("PASS: HTTPS playback and expired-certificate rejection without disabling TLS checks", flush=True)
        report["state"] = "passed-listed-checks-only"
    except Exception as error:
        report["state"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        search_path.close()
        (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--wasapi", action="store_true")
    parser.add_argument("--https", action="store_true")
    args = parser.parse_args()
    run(args.dll.resolve(), args.output.resolve(), args.ffmpeg, args.wasapi, args.https)
