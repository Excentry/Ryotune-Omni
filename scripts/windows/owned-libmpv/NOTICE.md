# Ryotunes Omni libmpv build candidate

This is a separately built Windows x64 libmpv candidate, not the previously selected upstream DLL. It is not approved for public distribution or automatic promotion into the application.

The recipe builds GPL-enabled mpv and FFmpeg with GPL version 3 enabled, plus Rubber Band. The complete pinned input archives, this recipe and its source lock are supplied in `source-inputs.tar.gz`. Extract it and run `python recipe/prepare.py --offline --cache archives --output prepared`, then use the toolchain image recorded in `sources.lock.json` with networking disabled to run `bash prepared/recipe/build.sh prepared output`.

Other compiled components include libplacebo, libass, FreeType, FriBidi, HarfBuzz and libxml2. Source snapshots of libplacebo's fixed submodules are also preserved, including code-generation inputs. Original upstream notices are copied under `licenses/`; original per-file grants remain in the source archives. Automated filename-based notice collection is not a complete per-file legal review. Preserve all applicable copyright, permission and warranty notices.

See `REVIEW.md` for the 15-input license inventory, source-delivery requirements and unresolved compiler/runtime provenance. Known embedded grants and full texts under upstream `LICENSES/` directories are also copied under `licenses/`. The 15-input archive does not yet contain verified corresponding sources for compiler-supplied runtime objects. Distribution of the application with this GPL-enabled candidate requires a separate combined-work review and corresponding application sources; the DLL source archive alone is not sufficient.

Original GCC GPLv3/Runtime Library Exception 3.1 and MinGW-w64/winpthreads notices are supplied under `licenses/toolchain/`, with revision URLs and hashes in `notice-inputs.lock.json`. These texts are also preserved in the source archive's recipe. They do not constitute complete runtime source code or a blanket exception for unrelated GPL components. Effective runtime provenance and exception applicability remain subject to the review gates.

For this candidate, FreeType is used under the FreeType Project License, with its original `docs/FTL.TXT` preserved. Portions of this software are copyright © 2026 The FreeType Project (www.freetype.org). All rights reserved.

FFmpeg includes code derived from the Independent JPEG Group. This software is based in part on the work of the Independent JPEG Group. No modifications to those source files are made by this recipe.

LuaJIT, MuJS, libsixel, subrandr, DVD/Blu-ray integrations and optional mpv graphics backends are not enabled by this audio-focused recipe. Tauri/souvlaki, not this libmpv instance, owns application SMTC. Disabled functionality must still be checked against the application's runtime requirements before promotion.

The toolchain container is pinned for build tools only. Target dependencies are rebuilt into an isolated prefix; preinstalled BtbN target libraries must not be linked accidentally. Windows system libraries and compiler runtime exceptions require separate verification, as does the final PE dependency list.

Before distribution, complete the candidate validation and license review, preserve the build logs and source inputs durably, and provide an applicable corresponding-source distribution method alongside the binary. GitHub Actions artifacts expire and are not the final source-hosting arrangement. No legal certification is claimed.
