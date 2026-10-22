import re
import sys
from pathlib import Path


WINDOWS_IMPORTS = {
    "advapi32.dll", "avrt.dll", "bcrypt.dll", "crypt32.dll", "dwmapi.dll",
    "gdi32.dll", "imm32.dll", "kernel32.dll", "ncrypt.dll", "ntdll.dll",
    "ole32.dll", "secur32.dll", "shcore.dll", "shell32.dll", "shlwapi.dll",
    "user32.dll", "uxtheme.dll", "ws2_32.dll",
    "api-ms-win-core-path-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-private-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "api-ms-win-crt-utility-l1-1-0.dll",
}


def verify_pe_imports(path):
    imports = sorted({name.lower() for name in re.findall(r"^\s*DLL Name:\s*(\S+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)})
    if not imports:
        raise ValueError("PE import evidence contains no DLL imports")
    unexpected = sorted(set(imports) - WINDOWS_IMPORTS)
    if unexpected:
        raise ValueError(f"Unreviewed non-system or new DLL imports: {', '.join(unexpected)}")
    return imports


if __name__ == "__main__":
    for name in verify_pe_imports(Path(sys.argv[1])):
        print(name)
