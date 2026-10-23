import argparse
import ctypes
import hashlib
import json
import locale
import math
import os
import re
import struct
import tempfile
import time
import wave
from pathlib import Path


def verify_checksums(directory):
    entries = (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    required = {"libmpv-2.dll", "mpv.lib", "source-inputs.tar.gz", "sources.lock.json", "NOTICE.md", "candidate.json"}
    listed = set()
    for entry in entries:
        expected, relative = entry.split("  ", 1)
        if not re.fullmatch(r"[a-f0-9]{64}", expected) or relative in listed:
            raise ValueError("Invalid or duplicate candidate checksum entry")
        listed.add(relative)
        path = directory / relative
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Unsafe candidate checksum path")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Candidate checksum mismatch: {relative}")
    actual_files = {path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"}
    if not required.issubset(listed) or listed != actual_files:
        raise ValueError("Candidate checksum manifest is incomplete")
    metadata = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
    if metadata.get("source_archive") != "source-inputs.tar.gz":
        raise ValueError("Candidate source archive path is invalid")
    with (directory / "source-inputs.tar.gz").open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    if metadata.get("source_archive_sha256") != source_hash:
        raise ValueError("Candidate source archive hash does not match candidate metadata")


def smoke(dll):
    verify_checksums(dll.parent)
    locale.setlocale(locale.LC_NUMERIC, "C")
    search_path = os.add_dll_directory(str(dll.parent))
    library = ctypes.CDLL(str(dll))
    library.mpv_create.restype = ctypes.c_void_p
    library.mpv_set_option_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    library.mpv_initialize.argtypes = [ctypes.c_void_p]
    library.mpv_set_property_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    library.mpv_get_property.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]
    library.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    library.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
    library.mpv_error_string.argtypes = [ctypes.c_int]
    library.mpv_error_string.restype = ctypes.c_char_p
    handle = library.mpv_create()
    if not handle:
        raise RuntimeError("mpv_create failed")

    def check(code):
        if code < 0:
            raise RuntimeError(library.mpv_error_string(code).decode("utf-8"))

    def command(*arguments):
        encoded = [argument.encode("utf-8") for argument in arguments]
        values = (ctypes.c_char_p * (len(encoded) + 1))(*encoded, None)
        check(library.mpv_command(handle, values))

    def get_property(name, value, format_value):
        check(library.mpv_get_property(handle, name.encode(), format_value, ctypes.byref(value)))
        return value.value

    try:
        for key, value in (("config", "no"), ("terminal", "no"), ("vo", "null"), ("ao", "null"), ("vid", "no"), ("pause", "yes"), ("idle", "yes")):
            check(library.mpv_set_option_string(handle, key.encode(), value.encode()))
        check(library.mpv_initialize(handle))
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "audio.wav"
            with wave.open(str(fixture), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"".join(struct.pack("<h", int(1000 * math.sin(2 * math.pi * 440 * index / 48000))) for index in range(48000 * 3)))
            command("loadfile", str(fixture), "replace")
            deadline = time.monotonic() + 15
            while True:
                try:
                    duration = get_property("duration", ctypes.c_double(), 5)
                    if duration >= 2.9:
                        break
                except RuntimeError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("WAV never became ready")
                time.sleep(0.05)
            filters = b"lavfi=[volume=-6dB],rubberband=pitch-scale=1.122462,lavfi=[aecho=0.8:0.9:40:0.2],lavfi=[bass=g=3:f=110:w=0.6],lavfi=[stereowiden=delay=20:feedback=0.3:crossfeed=0.3:drymix=0.7]"
            check(library.mpv_set_property_string(handle, b"af", filters))
            command("seek", "1", "absolute+exact")
            for paused in (False, True):
                check(library.mpv_set_property_string(handle, b"pause", b"yes" if paused else b"no"))
                if bool(get_property("pause", ctypes.c_int(), 3)) != paused:
                    raise RuntimeError("Pause state did not change")
            command("stop")
        print("PASS: candidate hashes, Windows ABI loading, WAV, filter acceptance, seek request and play/pause state")
    finally:
        library.mpv_terminate_destroy(handle)
        search_path.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll", type=Path, required=True)
    args = parser.parse_args()
    smoke(args.dll.resolve())
