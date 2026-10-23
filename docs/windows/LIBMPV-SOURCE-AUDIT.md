# Windows libmpv source and license audit

## Selected binary

- Upstream artifact: `libmpv-v0.41.0-dev-ga43ab319f-39541010475-x86_64-w64-mingw32-gpl.zip`
- Artifact SHA-256: `7f63ce43997b0c0d3d16465162200a4cdafcc21f73a122ba3a75b55032c64b9f`
- DLL SHA-256: `5816ca7aeab4d07774f3b26c465ee6691c41660ba7288381949413c9844bcdf7`
- mpv source commit: `a43ab319fdb7aec31874999e5562c9975328cbda`
- Upstream CI run: <https://github.com/mpv-player/mpv/actions/runs/39541010475>
- CI build container: `ghcr.io/btbn/ffmpeg-builds/win64-gpl@sha256:666d6b74870f232bbc9ea29acc608c91b6b1c74f1effd8129cd39ed2332d1287`

The run logs identify FFmpeg commit `ca85613d10cd523dd05780f48dc6ecac142bd560`, MuJS `1.3.8` revision 1, libplacebo `v7.374.0`, Rubber Band `4.0.0`, and C++/WinRT `2.0.250303.1`. They show the build enabled FFmpeg GPL/version3, mpv GPL, Rubber Band, DVD navigation and several more components. The container image provides additional static FFmpeg dependencies.

## Corresponding source recovered

`scripts/windows/collect-libmpv-sources.ps1` fetches and verifies these immutable source archives into the ignored `.libmpv/source-partial/` directory:

| Component | Source revision | SHA-256 |
| --- | --- | --- |
| mpv | `a43ab319fdb7aec31874999e5562c9975328cbda` | `c7198e76676aaa730164f5535dd4d7c562e616216c793785ca5a63738d611948` |
| FFmpeg | `ca85613d10cd523dd05780f48dc6ecac142bd560` | `589ea7ec9a2d42673b1e18685f5cf936e0cf29bf38e002b54867a0b91399ff2c` |

## Available notices prepared for the Windows bundle

Run `scripts/windows/prepare-libmpv.ps1` and `scripts/windows/collect-libmpv-sources.ps1` before bundling. The collector verifies each complete source archive before extracting only its named upstream notice files, preserving their contents. The Windows resource mapping installs:

| Installed path | Evidence |
| --- | --- |
| `licenses/project/LICENSE` | Repository GPLv3 text; explicitly bundled as a file, not only displayed by the installer |
| `licenses/mpv/NOTICE.md` | Project-maintained provenance, acknowledgements and incomplete-source warning |
| `licenses/mpv/Copyright`, `LICENSE.GPL`, `LICENSE.LGPL` | Pinned mpv source archive |
| `licenses/ffmpeg/LICENSE.md`, `COPYING.GPLv2`, `COPYING.GPLv3`, `COPYING.LGPLv2.1`, `COPYING.LGPLv3` | Pinned FFmpeg source archive |

The FFmpeg overview describes IJG-derived source files, so the bundle notice also carries the IJG acknowledgement. These top-level notices do not exhaust individual-file copyright requirements or the static dependency inventory. The source archives remain partial and local under `.libmpv/source-partial/`; installer generation does not publish or supply them to recipients.

## Still missing for redistribution

A separate [owned-build candidate pipeline](LIBMPV-OWNED-BUILD.md) now prepares reduced, fixed inputs and preserves source archives before compilation. It intentionally avoids the unresolved LuaJIT/libsixel/subrandr clones. This is a new candidate, not recovered evidence for the current DLL; native build, Windows tests and promotion remain pending. The current binary's distribution gate is unchanged.

See [component review](LIBMPV-COMPONENT-REVIEW.md) for actual configured-library evidence, grants read from recovered sources, excluded integrations, separately preserved candidate snapshots and the exact upstream evidence still needed. Root notice discovery is not a completed per-component license review.

### Recovery evidence from 2026-10-21

The container is now linked to a concrete BtbN build, not merely a same-day candidate. [Job `119234548334`](https://github.com/BtbN/FFmpeg-Builds/actions/runs/39601828709/job/119234548334) logs at `2026-10-21T13:00:45.5576544Z` record `exporting manifest sha256:666d6b74870f232bbc9ea29acc608c91b6b1c74f1effd8129cd39ed2332d1287`. The same job logs show the pushed manifest and output digest. Local extracted evidence is preserved under `.libmpv/btbn-39601828709/container-digest-evidence.log`.

That run uses BtbN revision `937868360a21d711ec94a33f5591d345ad9b7754` and publishes `download-cache` artifact `12346534162`: 2,210,375,083 bytes, SHA-256 `ea73dfe500a66c3b9f545954f0c9935d3eb8e241c60449dd1ae574e5d43e464d`, expiry `2026-11-04T12:43:03Z`. `scripts/windows/recover-libmpv-cache.ps1` downloads it through the authenticated GitHub API, without forwarding credentials to artifact storage, and verifies its published size and hash before accepting it. The cache still requires inspection: same-run association does not prove that every cached build layer used sources downloaded in that run or that the cache includes all nested downloads.

Recovery has completed locally: the ZIP passed the expected SHA-256 and size checks. Its sole entry, `cache.tar.gz` (2,209,702,759 bytes), was extracted successfully; the nested archive lists 258 entries, including aliases and recipe-hash-named source packages for multiple platforms. Neither count is a count of libraries incorporated into the DLL. The complete Windows GPL container build log is preserved as `.libmpv/btbn-39601828709/btbn-win64-gpl.log`; it includes 186 cached BuildKit steps, so sources must be matched to actual logged input filenames rather than guessed from build dates. `scripts/windows/inventory-libmpv-cache.ps1` selects only hash-named inputs referenced by that log, hashes their bytes, and reads available archived Git HEAD/ref evidence and notice paths without executing downloaded code. Its output is a recovery inventory, not a complete license manifest.

The inventory run completed: 104 selected archives, 101 with archived Git HEAD evidence, 113 Git HEAD/ref pairs resolved to commits (including nested repositories), and 103 archives with matching notice paths. Output: `.libmpv/btbn-39601828709/selected-source-inventory.json`. A matching notice filename is not a license review, and a recorded Git commit does not audit uncommitted files or prove final DLL inclusion. Examples recovered from archived refs:

| Cache component | Archived commit | Source archive SHA-256 |
| --- | --- | --- |
| Rubber Band | `e4296ac80b1170018a110bc326fd0d45a0eb27d6` | `77495a8a3119e26efb21d29ad5c38bd8a985756de0966527f59474d7952b10bd` |
| libplacebo | `1937beef3a2f508266c68efea1491e3fc4600e04` | `35297244890d53ead9f965410ff9a8e28702f43125ce094a8b5847ed505643fb` |
| libdvdnav | `8147ccd35e5aae4afdd21171cf7b6b4d8f179d28` | `f122b0bccbd3b4d9cdf7e174b461070e0a449e4eb7dc619d235c58efaef3c383` |

The BtbN source snapshot for this revision is preserved locally with SHA-256 `9ee4b55c6bf1ea2f9ee50a63bac8887532117ce9f7e7b0e2842a533b2d5f046a`. This preserves the recipes and patches; it is not the dependency source inventory.

The mpv GPL job from attempt 3 explicitly records `Installed mujs version 1.3.8 revision 1`, its source URL and its WrapDB patch URL. The matching published wrap, source and patch have been downloaded into `.libmpv/source-partial/mujs-1.3.8-1/` and checked against the release digests and the wrap's source/patch hashes:

| Input | SHA-256 |
| --- | --- |
| `mujs.wrap` | `44b282e74b95ddc52b62a1087c7af86e8bc6c007cd32b903bbc7bc34c4bf91ac` |
| `mujs-1.3.8.tar.gz` | `506d34882f2620a2fdeb6db63dbb7a8ffd98f417689d8f3c84f2feac275e39a9` |
| `mujs_1.3.8-1_patch.zip` | `20bf51cb657b22f02df05815677003f971da5896a7250940fd02bdabab5fe870` |

Assets: <https://github.com/mesonbuild/wrapdb/releases/tag/mujs_1.3.8-1>. The preserved GPL job log also exposes LuaJIT version `2.1.1792588164` and subrandr `1.4.0`; those version strings are leads, not yet proof of their resolved commits. LuaJIT, libsixel, subrandr and their nested inputs still need exact source correspondence review.

The upstream recipe at the mpv commit clones LuaJIT branch `v2.1`, libsixel default HEAD and subrandr default HEAD. It installs MuJS from the then-current Meson WrapDB and downloads Meson subprojects. The FFmpeg container is pinned by digest in the CI log, but the DLL package does not include the container's corresponding source archive or a complete manifest of its static dependency revisions and licenses. Some versions appear in logs, but versions alone do not prove exact source correspondence.

Therefore the collected archives are useful partial sources, **not complete Corresponding Source** for this DLL. The verified container-to-run link opens a concrete cache-recovery path, but cache contents, reused build layers, nested dependencies and mpv's separate moving-reference clones remain unaudited. Closing this gap requires completing that recovery, obtaining an upstream source bundle for this exact run, or replacing the binary with a build from fully pinned inputs that emits its own source bundle and notices. The installer remains blocked from public distribution until then.
