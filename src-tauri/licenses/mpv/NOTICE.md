# libmpv Windows distribution notice

Ryotunes Omni includes the Windows x64 `libmpv-2.dll` from mpv upstream's GPL build:

- Version: `v0.41.0-1274-ga43ab319f`
- Source commit: `a43ab319fdb7aec31874999e5562c9975328cbda`
- mpv source: <https://github.com/mpv-player/mpv/tree/a43ab319fdb7aec31874999e5562c9975328cbda>
- FFmpeg source commit recorded in the CI build log: `ca85613d10cd523dd05780f48dc6ecac142bd560`
- Source audit and partial source collector: `docs/windows/LIBMPV-SOURCE-AUDIT.md` and `scripts/windows/collect-libmpv-sources.ps1`
- Build recipe: <https://github.com/mpv-player/mpv/blob/a43ab319fdb7aec31874999e5562c9975328cbda/ci/build-mingw64-full.sh>
- Upstream asset: <https://github.com/mpv-player/mpv/releases/download/git-release/libmpv-v0.41.0-dev-ga43ab319f-39541010475-x86_64-w64-mingw32-gpl.zip>
- Asset SHA-256: `7f63ce43997b0c0d3d16465162200a4cdafcc21f73a122ba3a75b55032c64b9f`
- DLL SHA-256: `5816ca7aeab4d07774f3b26c465ee6691c41660ba7288381949413c9844bcdf7`
- Upstream CI run: <https://github.com/mpv-player/mpv/actions/runs/39541010475>
- FFmpeg build-container digest recorded in that run: `ghcr.io/btbn/ffmpeg-builds/win64-gpl@sha256:666d6b74870f232bbc9ea29acc608c91b6b1c74f1effd8129cd39ed2332d1287`

The upstream release metadata identifies this combined build as GPLv3, including FFmpeg built with `--enable-gpl --enable-version3`. The project-level GPL-3.0-or-later license text is installed as `licenses/project/LICENSE`. The upstream archive also supplies `LICENSE.GPL` (GPL version 2 text); it is retained as an upstream notice and does not replace the GPLv3 terms for the combined binary.

The verified mpv source supplies `Copyright`, `LICENSE.GPL` and `LICENSE.LGPL`, installed beside this notice. mpv derives from mplayer2 and MPlayer; their attribution and the source's licensing explanation are preserved in `Copyright`. The verified FFmpeg source supplies `LICENSE.md`, `COPYING.GPLv2`, `COPYING.GPLv3`, `COPYING.LGPLv2.1` and `COPYING.LGPLv3`, installed under `licenses/ffmpeg/`. These files describe multiple upstream licensing options; including them does not change this binary's build configuration or license. Individual source-file notices remain in the partial source archives and still require review for the exact enabled code and dependencies.

FFmpeg's licensing overview identifies code derived from the Independent JPEG Group. This software is based in part on the work of the Independent JPEG Group. The corresponding per-file notices are preserved in the FFmpeg source archive; this acknowledgement does not certify the complete binary notice inventory.

The upstream build recipe enables `rubberband`, used by Ryotunes Omni's pitch control. Its known build inputs also include FFmpeg (`--enable-gpl --enable-version3`), LuaJIT, libsixel, subrandr and the Meson `mujs` subproject. The pinned FFmpeg build-container image supplies additional static FFmpeg dependencies. The upstream script clones several dependencies from moving branches/HEAD and does not publish a complete revision/license manifest with this DLL.

This notice is provenance information, not a complete third-party license inventory or corresponding source. The repository can collect pinned mpv and FFmpeg sources, but does not yet contain exact source for all statically linked components and build inputs corresponding to this DLL. Do not publish a binary release until that source bundle and dependency notice review are complete.
