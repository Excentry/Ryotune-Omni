# Owned Windows libmpv candidate

## Status and boundaries

The repository now has a separate candidate recipe under `scripts/windows/owned-libmpv/` and a non-release workflow in `.github/workflows/libmpv-candidate.yml`. The workflow supports manual dispatch and a narrowly scoped push trigger for recipe/workflow changes on `test/libmpv-owned-build`, allowing its first run without adding the workflow to `main`. The user explicitly authorized native dependency/CI preparation and this separate test branch. Long-term maintenance and review remain with the native/CI owner, @Excentry.

The selected upstream DLL, its downloader and the application resource mapping are unchanged by this candidate recipe. Do not promote a candidate by overwriting the active DLL or reusing its existing hashes/notices. Native compilation and Windows validation of this recipe remain unverified until its workflow actually runs. Preparing scripts is not a successful DLL build or release approval.

Local checks completed on 2026-10-22: 11 Python unit tests passed; all 15 downloaded source archives matched their locked checksums; full offline extraction and source-package preparation passed; `bash -n` passed; workflow YAML parsing verified the manual trigger, read-only permissions and build-to-Windows dependency; `git diff --check` passed. Existing WSL Bash/PyYAML were used only for syntax checks, not native compilation. Docker's Linux engine was unavailable and was not started.

The preserved local package `.libmpv/owned/prepared-final/source-inputs.tar.gz` contains all 15 original source archives and the recipe: 78,892,342 bytes, SHA-256 `9a1dc7d8e032bff26ccf880e85470bf1d9f24f4b09c01cad5ef726113b3d579d`. This package hash identifies this local preparation, not a bit-for-bit reproducibility guarantee for future tarballs. The active application DLL still has SHA-256 `5816ca7aeab4d07774f3b26c465ee6691c41660ba7288381949413c9844bcdf7`.

## Reduced, pinned source closure

`sources.lock.json` pins full commits and SHA-256 values for 15 source archives: mpv, FFmpeg, Rubber Band, libplacebo, libass, FreeType, FriBidi, HarfBuzz, libxml2 and six libplacebo submodules. They are independently downloadable commit snapshots, not references to an expiring Actions cache. Submodule revisions were recovered from the cached source trees; they are deliberate inputs for this new build, not a claim about previously unresolved clones in the old binary.

The recipe disables LuaJIT, MuJS, libsixel, subrandr, DVD/Blu-ray integrations and optional graphics backends. mpv still requires libass and libplacebo even though the application sets `vid=no`; those required dependencies are rebuilt rather than removed by patching mpv. libplacebo's fixed submodules are preserved even where their backends or demos are disabled.

Required functionality retained by design:

- WASAPI output; OS media controls remain in Tauri/souvlaki.
- FFmpeg built-in codecs, demuxers, protocols and audio filters, rather than an unverified narrow audio-format whitelist.
- Network/Schannel HTTPS and libxml2 for DASH; actual signed-provider streams and headers still need runtime tests.
- Rubber Band using its built-in FFT/resampler; no optional FFTW/libsamplerate dependency.
- `volume`, `aecho`, `bass` and `stereowiden` lavfi filters used by `crates/player`.

Compiler/build tools come from the locked BtbN container digest, but preinstalled target libraries must not be consumed. Target dependencies are rebuilt into an isolated prefix; inherited include/library flags are cleared, pkg-config is restricted, FFmpeg autodetection is disabled, and Meson downloads/fallbacks are disabled. The container compilation step has networking disabled. Build metadata and PE imports require review for any accidental dependency or compiler runtime DLL.

The first branch run preserved the sources successfully but failed before compilation because the image's default user could not write the host-owned output bind mount. The workflow now uses the runner's numeric UID/GID and an output-local `HOME`/cache directory; it does not grant root privileges or widen directory permissions. The build script checks log writability before redirecting output. Output access passed in the second CI run.

The second run passed output ownership and compiled/installed all seven prerequisites, then failed FFmpeg's libxml2 detection. The pinned FFmpeg probe includes `libxml2/libxml/xmlversion.h`, while libxml2's Meson pkg-config file supplies the nested `include/libxml2` path. Its static Windows exports also require `LIBXML_STATIC`, not exported by this pkg-config generation. The recipe now supplies the isolated prefix include path and static define to FFmpeg, and compiles a matching standalone link probe before configuring it. FFmpeg/Meson detection logs and the libxml2 pkg-config file are retained as CI evidence. Native completion and Windows tests remain pending.

The third run passed that link probe and compiled/installed FFmpeg. mpv setup then rejected the duplicate static/shared `default_library` arguments. The helper now selects a single shared-library option for mpv and a single static-library option for every prerequisite. Final libmpv linkage and Windows tests still need a passing run.

## Local source preparation on Windows

From the repository root, with Python 3.12 or later:

```powershell
python -m unittest discover -s scripts/windows/owned-libmpv -p 'test_*.py' -v
python scripts/windows/owned-libmpv/prepare.py --output .libmpv/owned/prepared --cache .libmpv/owned/archives
```

The output directory must be new or empty. Previously acquired archives are reused only when their hashes match; mismatches fail instead of being silently accepted. Use `--offline` when all locked archives are already cached, or `--verify-only` to check archives without unpacking. The script verifies all inputs before extraction, rejects unsafe archive paths/links, preserves original source/license bytes and creates `source-inputs.tar.gz` with original archives, the recipe, lock and provenance metadata before native compilation.

No Linux setup is required locally. The manual workflow performs cross-compilation on a GitHub-hosted Linux runner using the pinned toolchain container. It first uploads the preserved source inputs, then builds with no network and tests the resulting candidate on Windows Server 2025. Uploads are Actions validation artifacts, accessible according to repository permissions and subject to expiry; they are not a durable source-distribution channel or an application release.

The user authorized committing/pushing only the new candidate implementation to the separate test branch, leaving previous local work uncommitted. The workflow has only `contents: read`, no tag trigger and no release publishing step. This does not authorize merging into `main`, replacing the active DLL or publishing a release.

## Evidence produced by the workflow

- Original source archives and recipe, retained independently of native build success.
- Compiler/build-tool versions, configure/build log, Meson options and dependency introspection.
- A separate `libmpv-2.dll`, GNU import archive named `mpv.lib`, public headers and PE imports.
- Original notice/license files, including FreeType's FTL text and acknowledgement; the full originals remain in the source inputs.
- Candidate hashes and metadata explicitly marking it not approved for distribution.
- Windows checksum/ABI smoke using the actual DLL and a generated WAV: load readiness, audio filter acceptance, seek request and play/pause state.
- The existing real-libmpv player regression compiled with MSVC against the candidate import library. Failure or timeout is not ignored.

The Windows smoke uses `ao=null`: it does not demonstrate audible playback, actual WASAPI output or the complete provider/format matrix. Successful API calls are not proof of gapless transitions or precise seek position.

## Promotion gates

Before replacing the selected dependency or distributing binaries:

1. Run the workflow and fix native build or Windows test failures. Confirm actual imports and no unpreserved target dependency.
2. Test Windows 11 installed runtime, WASAPI, local MP3/AAC/Opus/Vorbis/FLAC/ALAC/PCM, HTTPS headers, HLS/DASH, seek, EOF, gapless, speed/pitch/effects, shutdown and restart. Validate supported providers against authorized test inputs.
3. Review original per-file grants and nested dependencies, not only filenames. Preserve required notices and document compiler runtime/System Library exclusions or applicable exceptions. No blanket legal certification is made.
4. Preserve build/install scripts, modifications, source inputs, configuration and required installation information; verify source reconstruction without mutable fetches.
5. Arrange durable, equivalent source access with the candidate binary. Actions retention alone does not satisfy the intended public distribution arrangement.
6. Review/pin the new DLL/import-library hashes and replace application notices deliberately; rerun Tauri MSI/NSIS and clean installation tests. Keep the release guard closed until then.
