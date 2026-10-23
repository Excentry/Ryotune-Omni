# Windows libmpv component review

This is an evidence-based partial review, not a complete license inventory or permission to publish. The selected binary and source-cache identities are recorded in [LIBMPV-SOURCE-AUDIT.md](LIBMPV-SOURCE-AUDIT.md). The binary has not been replaced.

## Inclusion evidence

The preserved mpv GPL attempt-3 log records FFmpeg's successful configuration summary at lines 336-365 and mpv's enabled features at line 6037. These establish enabled integration/build dependencies, not a per-object final DLL link map. Static-library dead stripping can omit code; system APIs and SDK headers are not automatically redistributable library binaries.

FFmpeg's actual configuration summary lists Rubber Band, libplacebo, libdvdread, libdvdnav, libass, libcurl and libbluray. mpv also reports the corresponding integrations enabled. This is stronger evidence than finding their sources in a cache, but does not exhaust their nested dependencies.

Do not treat all 104 recovered archives as final DLL components. The official mpv recipe explicitly disables `librav1e`, `librsvg` and `openal` when recompiling FFmpeg. The cache also contains tools, headers and inputs for other stages. These exclusions concern the named integrations; they do not prove that every shared lower-level dependency is absent.

## Grants examined in recovered sources

The following declarations were read from the archived source, not inferred from the name of a `COPYING` file. The archive hashes and commits are in `.libmpv/btbn-39601828709/selected-source-inventory.json`.

| Component | Examined declaration | Source evidence | Remaining work |
| --- | --- | --- | --- |
| Rubber Band | GPL-2.0-or-later | `README.md`, `meson.build`, `rubberband/RubberBandStretcher.h`; copyright Particular Programs Ltd. | Preserve grant, copyright and GPL text; audit nested dependencies and actual build options |
| libplacebo | LGPL-2.1-or-later | `README.md` and `meson.build` | Preserve LGPL text and notices; inspect included shader and graphics dependencies |
| libdvdnav | GPL-2.0-or-later | Grant in `src/dvdnav.c`, not just root GPLv2 text | Preserve notices and BtbN patches; review remaining source-file grants |
| libdvdread | GPL-2.0-or-later | Grant in `src/dvd_reader.c`; `README.md` discusses GPLv2/v3 | Preserve notices and examine optional DVD/CSS paths |
| libbluray | LGPL-2.1-or-later | Grant in `src/libbluray/bluray.c` | Review nested inputs; the upstream ZIP's optional JAR is not a resource in our installer |
| libass | ISC | Complete `COPYING` text; copyright libass contributors | Retain copyright/permission notice; review font/rendering dependencies |
| libcurl | curl copyright/permission license | `COPYING`; copyright Daniel Stenberg and contributors | Retain complete notice, including name/endorsement clause; inspect actual TLS/compression dependencies |
| ffnvcodec | MIT permission/warranty terms for the two examined headers only | Inline NVIDIA copyright and grant in `ffnvcodec/include/ffnvcodec/nvEncodeAPI.h` and `dynlink_cuviddec.h` | Preserve header notices; inspect remaining headers/versions actually consumed; these grants do not cover NVIDIA drivers |

The examined `or-later` grants do not present a GPLv2-only conflict with the selected GPLv3 combination. This observation is limited to the declarations inspected above. It does not certify compatibility or compliance for the complete binary.

`scripts/windows/collect-libmpv-notices.ps1` prepares a separate local review corpus. It checks source hashes, reads selected top-level/doc notice entries as bytes without extracting archive links, and records individual hashes under `.libmpv/btbn-39601828709/notice-review-index.json`. It includes two ffnvcodec headers as review inputs. The corpus is intentionally not copied wholesale into the installer: individual-file notices, nested sources and final inclusion remain under review.

The initial collector run preserved 180 inputs across 102 components. Review found two archive symlinks (`glib/COPYING` and `libpsl/COPYING`) and a genuinely empty `pixman/AUTHORS`, not three missing license grants. The collector now reads the verified in-archive targets of those two links without creating filesystem links. It also explicitly includes OpenCL's separate loader/header licenses and AviSynth's nested licensing document. These corrections do not turn the corpus into a complete notice inventory.

## Separate mpv downloads: candidates, not confirmed build inputs

Historical API queries selected the most recent visible commits before each clone time. These snapshots are preserved for investigation under `.libmpv/source-partial/candidates/`. Branch rewrites, timing, submodules and unrecorded modifications prevent treating this inference as proof of the actual checkout.

| Candidate | Revision | Download SHA-256 | Examined license evidence |
| --- | --- | --- | --- |
| LuaJIT | `a4c064539ea931274d407e1249b4bb575424a0f4` | `15625df3ebfbd1f76371005bffae39b84c65e718e57acc9a9c57863c7c101541` | `COPYRIGHT` contains MIT grants for LuaJIT and included Lua; preserve both |
| libsixel | `f0b705a365563c56f977afaca73997ca68669c62` | `f53d0f3b06c221e88d25724d63c8cf9915f3f7a7308b7133b1b26fb5d5df2707` | Root `LICENSE` is MIT, copyright Hayaki Saito; bundled code requires separate review |
| subrandr | `8e150b0b49be13e3fd18e1914c2f38efe859455f` | `bcdab6852e55da53fa9f8c545e504359b2580e1c2d73b28a1afc79ac4b29b44e` | `README.md` declares MPL-2.0 unless stated otherwise; root `LICENSE` supplies MPL-2.0; example is CC0 |

The LuaJIT candidate's commit date matches the timestamp in logged version `2.1.1792588164`, and the subrandr candidate manifest reports `1.4.0`, matching the log. These are corroborating clues, not resolved checkout identities. The log reports libsixel `1.8.7-r2`; that version likewise does not identify a Git tree.

For subrandr, inspect file-specific exceptions, any actual designation as incompatible with secondary licenses, the GPL/MPL combined-work conditions and every linked Rust dependency. Having a root MPL license and a `Cargo.lock` is not that review. The recovered candidate lockfile has no `source = "git..."` entries, but registry crates and workspace sources still need preservation and verification against the real build.

## Exact upstream evidence still needed

No request has been sent upstream. A narrowly scoped request for the existing artifact would ask:

> For mpv commit `a43ab319fdb7aec31874999e5562c9975328cbda`, Actions run `39541010475`, attempt 3, Windows x64 GPL libmpv, please provide the resolved LuaJIT, libsixel and subrandr commits/trees, recursive submodule or LFS inputs, local modifications, subrandr Cargo.lock and dependency sources used by the build. Please also confirm the C++/WinRT/windows-rs inputs and generated-header recipe. We recovered the matching BtbN container source cache and MuJS 1.3.8-1 wrap/source/patch; those do not cover these separate clones. No rebuild is requested if the original inputs are still available.

If that evidence cannot be recovered, preserving more approximate snapshots will not close correspondence. The fallback is a new, separately identified build from fixed, preserved inputs, with source collection before compiling and a complete notice/source package. Do not silently substitute that build for the current DLL or remove the distribution gate.
