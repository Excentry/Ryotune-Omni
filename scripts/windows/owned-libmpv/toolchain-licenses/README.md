# Toolchain notice inputs

Original notice texts in this directory are copied without rewriting from fixed upstream revisions. `../notice-inputs.lock.json` records their URLs and SHA-256 checksums. Source preparation includes this directory in the recipe inside `source-inputs.tar.gz`; packaging verifies the recorded bytes and copies the texts into `licenses/toolchain/`.

Scoped Git attributes preserve these upstream files' bytes and original whitespace, including trailing spaces and the exception text's final blank line. Do not normalize their line endings or apply whitespace cleanup: the locked SHA-256 checks, rather than repository prose formatting, validate these original legal texts.

These files are license evidence, not complete runtime sources. GCC 16.2.0 was observed in candidate run 39792004346. Its release tag resolves to commit `78d4ac73dd391005b895a6148cd9831e28e1208b`. The BtbN image recipe at `937868360a21d711ec94a33f5591d345ad9b7754` selects that version in `images/base-win64/ct-ng-config`, but clones crosstool-NG without pinning its checkout and applies bundled patches. The precise effective GCC patch set remains to be reconstructed.

The same BtbN recipe rebuilds MinGW headers, CRT and static winpthreads from commit `57b595039040eaa15bece85b7cc71d952281b269` in `scripts.d/10-mingw.sh`, overriding the base toolchain's MinGW release. That commit is present as the checked-out HEAD in the recovered `10-mingw` cache. This is stronger evidence than labeling all runtime objects with the base configuration's `v14.0.0` string, but final linked-object provenance still requires a link map.

GCC's runtime exception applies to files bearing the relevant grant and eligible compilation processes; it does not relicense mpv, FFmpeg, Rubber Band or other independent modules. Copying a separate GCC runtime DLL is not automatically covered by the same reasoning as target code combined with independent modules. This recipe intends to avoid that extra DLL dependency rather than silently bundle one.

The MinGW runtime notice contains an unresolved upstream Cephes paragraph and references Wine-derived LGPL headers. Do not treat its root ZPL notice or this notice bundle as a complete per-object clearance. Inspect the selected objects and headers; no upstream contact or license clarification request is authorized by this review.
