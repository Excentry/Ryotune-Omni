# Ryotune-Omni

An independent, community-driven fork of Ryotunes exploring Windows and Android ports of its desktop music-player experience.

Ryotune-Omni aims to preserve the original application's functionality, design language, themes, music ecosystem, and user experience wherever technically and legally possible. It builds on the work of the original authors; it does not claim ownership of their code.

**This is not an official Ryotunes or Ryoku project, and no affiliation or endorsement is implied.**

## Project status

**Experimental / work in progress. Windows and Android are planned targets, not supported releases.**

The inspected repository contains the inherited Linux-first application, its Rust workspace, a primary Quickshell/QML client, and an older Svelte/Tauri client. Some Windows-specific code and a Tauri mobile entry-point annotation already exist, but neither establishes a functioning Ryotune-Omni port.

At this documentation update:

- No Ryotune-Omni releases were published on the fork's GitHub repository.
- The inherited CI validates Linux and web frontend paths; it has no Windows or Android build job.
- No Windows or Android application was compiled, run, or validated as part of this documentation review.
- UI framework selection, target OS versions, Android ABIs, native-library packaging, and feature parity remain open engineering decisions.

Inherited version numbers, application identifiers, package names, and update links still refer to Ryotunes. They are not evidence of a Ryotune-Omni release. This README documents a direction, not an implemented migration.

## Vision and principles

These are project goals, not completed achievements:

- **Feature parity:** Preserve desktop functionality where feasible and document unavoidable platform differences.
- **Code reuse:** Retain compatible Rust logic, provider integrations, data models, and persistence rather than rebuilding them unnecessarily.
- **Platform independence:** Put OS-specific behavior behind explicit interfaces instead of spreading platform assumptions through shared code.
- **Original identity:** Carry forward the application's visual language, themes, artwork-centered presentation, and listening experience, adapting interaction for desktop or mobile rather than creating an unrelated player.
- **Maintainability:** Track upstream improvements while keeping port-specific divergence small and understandable.
- **Transparency:** Publish limitations, incomplete features, technical decisions, and evidence behind compatibility claims.
- **Open-source collaboration:** Welcome community contributions while preserving upstream attribution and complying with applicable licenses.

## Platform support

| Platform | Repository baseline | Ryotune-Omni status |
| --- | --- | --- |
| Linux, especially Ryoku / Arch-based desktops | Primary upstream environment: Quickshell/QML, Rust daemon, libmpv, Linux packaging; Void installation documentation is also inherited | Reference implementation for parity; not newly tested by this fork's documentation review |
| Windows | Inherited Tauri launch path, Windows taskbar code, and media-control integration points | Planned port; no verified build, installer, minimum OS version, or parity guarantee |
| Android | Tauri v2 dependencies and a mobile entry-point annotation, but desktop-oriented hosting and dependencies | Planned port; no verified Android build, APK, background service, or supported device list |

The original application is **audio-only**. This fork does not announce video playback or additional provider capabilities.

## Architecture and portability strategy

### What is implemented in the inherited code

The primary Linux execution path is:

```text
ryotunes launcher -> ryotunesd -> shared Rust core -> player -> libmpv
                         ^
                         | newline-delimited JSON requests and events
                         v
                 Quickshell / QML client
```

The alternate Tauri host embeds the Svelte frontend and calls the shared core through Tauri commands. On Linux, the current launcher uses the daemon/native client only: a failed daemon connection does not fall back to Tauri.

| Area | Source and role | Portability assessment |
| --- | --- | --- |
| Primary UI | `client/shell.qml`, `App.qml`, pages and components; Qt Quick/QML hosted by Quickshell, with `Quickshell.Wayland` and `Ryoku.Ui.Singletons` imports | Not a standalone, platform-neutral Qt app. Quickshell, shell tokens, and window surfaces need adaptation or replacement; ordinary Qt platform support does not establish client portability. |
| Alternate UI/host | `ui/`: Svelte 5, SvelteKit, TypeScript, Tailwind and Vite, statically built into `ui/build`; `src-tauri/`: Tauri v2 host, commands and desktop integrations | A candidate for reuse, not a selected migration. Its feature coverage differs from the QML client, and desktop plugins/window behavior need target-specific review. |
| Shared backend | `crates/core`: `AppState`, orchestration, SQLite persistence, local library, lyrics, provider bridges and integrations; Tokio, Serde, reqwest/rustls, rusqlite and other dependencies | Candidate logic for reuse, not a certified portable crate. It still depends on playback, media controls, Discord integration, and Linux-oriented updater behavior. |
| Host interfaces | `crates/core/src/host.rs`: `EventSink`, `JsBridge`, `LoginFlow`, and host-supplied paths | Useful existing seams. Provider JavaScript execution, interactive authentication, and event delivery still need implementations on each target. |
| Playback | `crates/player`: `libmpv2` wrapper, dedicated event thread, audio-only playback, queue lookahead, disk cache and audio filters | Requires native libmpv and its dependency chain. Linkage, output devices, lifecycle, codecs and effects must be validated per target. Pitch shifting depends on the libmpv build's rubberband support. |
| Providers | `crates/innertube`, `spotify`, `soundcloud`, `tidal`, and core bridge modules | Request/model/parsing logic may be reusable. Authentication, native dependencies, audio transport, service restrictions, and live behavior require separate validation. |
| IPC | `crates/protocol` wire types; daemon `server.rs` / `methods.rs`; `crates/ryotunes-cli`; `client/Daemon.qml` | JSON contracts are reuse candidates. The current daemon and CLI use Unix sockets; daemon locking and runtime paths are OS-specific. Protocol path discovery also reads Linux `/proc`. |
| Downloads | Daemon-owned queue/history, external yt-dlp and FFmpeg, metadata/lyrics/artwork enrichment | Not simply portable backend code: process groups, signals, Unix priority handling, hard-link publication and desktop folder opening need review or replacement. |

### State, storage, and desktop integration

The Linux daemon resolves data under `$XDG_DATA_HOME/dev.ryoku.ryotunes` and audio cache under `$XDG_CACHE_HOME/dev.ryoku.ryotunes/audio`, with home-directory defaults. Its application setup opens `ryotunes.sqlite`; download settings/history use `downloads.json`. The QML client separately stores UI preferences in `$XDG_CONFIG_HOME/ryotunes/client.json`. The Tauri host uses Tauri's application-data/cache resolvers instead.

The normal daemon socket is `$XDG_RUNTIME_DIR/ryotunes/ryotunesd.sock`. Spotify audio currently passes from librespot into libmpv through a Unix FIFO; `crates/spotify/src/stream.rs` explicitly rejects this transport on non-Unix platforms. Authentication data, cookies, settings, local library paths, artwork and provider caches also need a target-specific storage and privacy review. Existing XDG/HOME assumptions, Unix permissions, filesystem URLs and external-process behavior must not be copied unchanged to Windows or Android.

Linux integrations include MPRIS/D-Bus media controls, StatusNotifierItem tray support, systemd user socket activation, Hyprland window rules, Ryoku live palette integration, and GTK/WebKitGTK authentication and JavaScript hosts. These are not portable application requirements. The daemon owns playback and active downloads independently of the visible client; equivalent lifecycle behavior is a porting goal, not a reason to reproduce systemd or a desktop daemon on mobile.

### Windows: planned approach

The existing Tauri path is worth evaluating before choosing a replacement UI. `src-tauri/src/main.rs` invokes the Tauri application on non-Linux targets, and `src-tauri/src/taskbar.rs` contains Windows thumbnail-toolbar integration. These are inherited implementation points, **not tested Windows support**. Core media controls use souvlaki, but the shared-core path currently supplies no Windows window handle, so media integration needs explicit validation.

Windows work must investigate:

- Building selected compatible Rust packages and native dependencies with a validated Windows toolchain rather than assuming the Unix-oriented workspace builds as a whole.
- Reusing/adapting the Svelte/Tauri interface, or another validated UI host, while preserving QML-era features, skins and design. Running the current Quickshell shell unchanged is not the plan.
- Retaining libmpv if a reproducible, license-reviewed Windows build can meet playback requirements; otherwise evaluating an audio abstraction and alternative engine without promising identical codec/effect behavior.
- Replacing Unix socket/locking and Spotify FIFO transport where needed. Windows named pipes or an in-process host are options requiring design and security review, not implemented decisions.
- Adapting system media controls, tray, launch behavior, authentication/browser callbacks and window management instead of carrying over MPRIS, systemd or Hyprland.
- Resolving Windows application-data/cache locations, Unicode paths, file URLs, permissions, local-library access and download publication safely.
- Packaging the app, libmpv/native libraries and any downloader dependencies; validating runtime discovery, updates, signing and redistribution obligations. If Tauri is retained, its Windows C++ build-tool and WebView2 requirements also apply.

### Android: planned approach

Desktop QML, Quickshell, the existing daemon, systemd activation, and Linux desktop APIs are not an Android application architecture. Tauri v2 supports Android at the framework level, but that does not make this application's native libraries or desktop plugins Android-compatible.

Options requiring validation include a mobile-adapted Svelte/Tauri frontend with native plugins, or an Android-native interface connected to compatible Rust components through JNI/FFI. Neither is selected. A libmpv-based Android engine versus an Android-native playback engine must be assessed against stream support, effects, lifecycle, resource use and licensing.

Android work must investigate:

- SDK/NDK, Rust targets, native ABIs, reproducible builds, and which backend components can actually compile and run.
- Touch navigation, responsive layouts and accessibility while preserving the original visual identity, artwork, themes and feature intent.
- A platform-appropriate playback service, media session, foreground-service behavior, notifications and lock-screen controls, including audio focus, headphone/disconnection events and interruption recovery.
- Activity/service lifecycles and background limits; keeping playback independent of the visible activity without assuming desktop process lifetimes or IPC. In-process bindings and Android service interfaces are candidates.
- App-private configuration/cache and protected credentials; shared music and downloads through appropriate MediaStore or Storage Access Framework access. Handle content URIs and request only permissions required by the selected access method and Android version, rather than treating every document as a normal path.
- Replacing desktop authentication assumptions and validating provider flows, playlists, lyrics, downloads and offline local playback individually.
- APK packaging and, if a distribution channel requires it, an Android App Bundle, with signing, native libraries, source availability and license notices reviewed before release.

Reference guidance: [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/), [Tauri v2 mobile support and plugin limitations](https://v2.tauri.app/blog/tauri-20/), [Android background playback](https://developer.android.com/media/media3/session/background-playback), and [Android document/storage access](https://developer.android.com/training/data-storage/shared/documents-files). These describe platform capabilities, not completed Ryotune-Omni work.

## Feature compatibility

**Legend:** "Existing" means implementation is present in the inherited source, not that it was executed in this review. "Planned" means a parity objective; "Investigate" identifies an unresolved implementation or platform constraint. **No Windows or Android feature below is verified working.**

| Feature | Existing upstream functionality in this checkout | Windows goal | Android goal / investigation |
| --- | --- | --- | --- |
| Discovery and search | Home feeds, songs/albums/artists/playlists, incremental results, shortcuts and local history-based recommendations | Planned parity | Planned; adapt navigation and bounded loading |
| Music providers | YouTube/YouTube Music, Spotify, SoundCloud and TIDAL provider paths | Planned; investigate auth and native/audio transport | Planned; investigate auth, native compatibility and service restrictions |
| Playback and audio controls | Native audio-only libmpv, seek/volume, shuffle/repeat, queue continuation and audio effects; behavior varies by provider | Planned; validate libmpv, filters and output | Investigate engine and effects parity |
| Queue, playlists and favorites | Queue editing, provider likes/saves, persistent device playlists, playlist import/export | Planned parity | Planned; adapt file import/export and interactions |
| Local library and metadata | Local-folder indexing, metadata and artwork handling | Planned; paths and access need adaptation | Planned; investigate URI-based media access and permissions |
| Album/playlist artwork | Provider/local artwork, caches, device-playlist collages and custom covers | Planned parity | Planned; validate memory/cache costs |
| Lyrics | Plain and synchronized lyrics, timing/seek UI, local sidecar/embedded lyrics and network providers | Planned parity | Planned; provider availability and mobile presentation need validation |
| Downloads and offline files | Persistent queue/history, format preferences, metadata and companion artwork/lyrics; downloaded/local files can be used offline | Investigate downloader packaging, process control and filesystem behavior | Investigate mobile downloader, background execution, storage and permissions |
| Themes, skins and customization | Light/dark, Ryoku Follow System, skin manifests, matugen integration and mini-player styling | Planned identity/skins; replace Linux shell theme coupling | Planned identity/skins; investigate mobile theme mapping |
| History and personalization | Recent listening, shortcuts, local Home ranking and listening statistics | Planned parity | Planned parity; lifecycle and persistence need validation |
| Desktop/background controls | Daemon-owned playback/downloads, mini-player, tray, media keys and MPRIS; inherited Windows host code also exists | Investigate Windows media controls, tray and mini-player parity | Investigate foreground media service, notifications, audio focus and lock-screen controls |
| External integrations | Last.fm scrobbling, Discord Rich Presence, optional Listen Together relay | Investigate credentials, host integration and lifecycle | Investigate applicability; desktop integration may have no mobile equivalent |
| Internet Radio | Demand-driven station discovery and native live audio playback | Planned; validate engine/network behavior | Planned; validate engine and background playback |
| Installation and updates | Linux package/release scripts and pacman/xbps-oriented update handling | New packaging/update strategy required | New packaging/update strategy required |

### Provider and download limits

- Feature availability depends on account state, region, subscription, provider responses and service terms; integrations are not service guarantees. Spotify sign-in includes a Premium eligibility gate.
- TIDAL integration requires configured client credentials and sign-in. The implementation explicitly refuses protected stream assets; this fork does not promise DRM bypass or playback of every catalogue item.
- Current downloads use yt-dlp and FFmpeg. YouTube and public SoundCloud sources are supported paths; Spotify downloads use a **labelled YouTube search match**, not exported Spotify audio or a guarantee of the same recording.
- Downloads do not establish unrestricted offline access to any provider catalogue. Local files, live radio, protected or unavailable items are not downloadable through that workflow. Save only content you are authorized to download, in accordance with applicable law and service terms.
- Accounts, lyrics, artwork, scrobbling and download metadata lookups can involve third-party services. Preserve clear disclosures and protect credentials when adapting these features.

## Roadmap

All items below are planned work. This initial documentation review is not a completed architecture, security, licensing or compatibility audit.

### Phase 1 - Repository and licensing audit

- [ ] Review the upstream architecture and dependency graph.
- [ ] Identify platform-specific components and native-library blockers.
- [ ] Establish license compliance and attribution requirements, including distributed dependency builds.
- [ ] Define and test a baseline of existing functionality for parity tracking.

### Phase 2 - Portability architecture

- [ ] Separate reusable business logic from OS-specific behavior where needed.
- [ ] Define host interfaces, storage boundaries and platform abstractions.
- [ ] Evaluate UI and audio-engine alternatives with small technical prototypes.
- [ ] Establish automated tests and target-specific build validation.

### Phase 3 - Windows port

- [ ] Validate the Windows toolchain and native dependencies.
- [ ] Adapt backend dependencies, authentication, IPC and Spotify audio transport.
- [ ] Integrate and test the audio engine and Windows media controls.
- [ ] Establish application-data handling, packaging and update behavior.
- [ ] Verify and publish feature compatibility results.

### Phase 4 - Android port

- [ ] Validate the Android SDK/NDK toolchain and supported ABIs.
- [ ] Integrate compatible Rust/native components and the selected mobile UI.
- [ ] Implement and test mobile audio and background playback.
- [ ] Adapt storage, permissions, lifecycle, audio focus and media controls.
- [ ] Verify and publish feature compatibility results.

### Phase 5 - Quality and maintenance

- [ ] Test playback reliability, resource usage, interruptions and long sessions.
- [ ] Verify provider integrations and inherited functionality on each target.
- [ ] Document known limitations and reproducible test results.
- [ ] Establish fork-specific releases, issue reporting and contribution procedures.
- [ ] Track upstream changes and maintain the fork with minimal unnecessary divergence.

## Building, installation, and releases

### Windows and Android

**Platform-specific setup, build and installation instructions are pending successful port validation.** There are no verified Ryotune-Omni Windows executables, installers or Android APKs to recommend. No target build commands are provided here because none were executed successfully during this review.

The existing Tauri configuration, mobile annotation, DLL ignore entries and Windows code are starting points for investigation, not installation instructions. No minimum Windows/Android version or supported CPU/ABI list has been established.

### Inherited Linux development reference

The existing build system is a Cargo workspace plus a separate pnpm project in `ui/`. CI declares stable Rust, Node 22 and pnpm 11; the Spotify crate uses Rust edition 2024, so the older `rust-version` declared by the Tauri package alone is not a sufficient workspace toolchain guide. Linux builds require native dependencies including GTK/WebKitGTK and libmpv; the QML runtime additionally requires Quickshell and Ryoku modules.

Use the following existing documents and executable configurations as **upstream-oriented references**, not verified Windows/Android instructions:

- [Arch/Ryoku setup and source builds](docs/INSTALL-ARCH.md) and [Void installation](docs/INSTALL-VOID.md).
- [Contributing](CONTRIBUTING.md), [CI workflow](.github/workflows/ci.yml), [Cargo workspace](Cargo.toml), [frontend scripts](ui/package.json), and [Arch dependency/build recipe](packaging/arch/PKGBUILD).
- [Release checklist](docs/RELEASE-CHECKLIST.md) and [release checks](scripts/release-check.sh).
- [Architecture](docs/ARCHITECTURE.md), [design language](docs/DESIGN.md), [skins](docs/SKINS.md), and [troubleshooting](docs/TROUBLESHOOTING.md).

These documents contain historical Linux assumptions and some stale lifecycle descriptions. Consult current code when they conflict: the Linux launcher has no Tauri fallback, and the daemon's default idle grace is 60 seconds, subject to activity and subscribers. Do not run separate playback hosts against the same application data.

Existing test sources include Rust unit tests, Node-run `ui/src/lib/*.check.ts` regressions, and separate QtTest files in `client/tests`. Linux CI separates an environment-sensitive real-libmpv test from the main suite; QML tests are not currently a CI job. These are inherited checks, not proof of target-platform compatibility.

**Release safety:** The inherited release workflow is designed to version, tag and publish Linux packages on default-branch pushes. Update/self-install code and several links still target upstream infrastructure. Fork-specific publishing, application identity and update routing require review before distributing binaries; existing Linux packages must not be presented as Windows or Android releases. No build/test success is claimed by this README.

## Licensing and attribution

### Project license and provenance

The root [LICENSE](LICENSE) contains the GNU GPL version 3 text. The workspace manifest explicitly declares **`GPL-3.0-or-later`**, and the verified Ryotunes upstream manifest and [UPSTREAM.md](UPSTREAM.md) confirm that grant. Ryotune-Omni retains this licensing basis for the inherited application and derivative work; this README does not relicense third-party components.

Attribution must include the original Ryotunes/Ryoku contributors and the earlier **[LiMusic project by SimoHypers](https://github.com/SimoHypers/limusic)** described in `UPSTREAM.md`. Additional Spotify implementation provenance is recorded in [crates/spotify/README.md](crates/spotify/README.md) and source headers: code was adapted from **[Sonora](https://github.com/sonorahq/sonora)**, historically `nolight132/sonora`, commit `695242e`, under GPL-3.0-or-later. Preserve those notices and the original authors' credits.

### What distribution requires

In plain English, applicable GPL obligations include:

- Preserve copyright, attribution, licensing and warranty notices, and retain the required license text. Clearly identify modifications rather than presenting the fork as the original work.
- Distribute covered derivative work under the applicable GPL terms, preserving recipients' rights to use, study, modify and redistribute it. Do not add incompatible restrictions.
- When conveying binaries, meet GPL section 6's corresponding-source requirements through an applicable compliant distribution method. Source must correspond to the shipped build and include required build/install scripts and modifications, not merely a link to unrelated upstream HEAD.
- Where GPLv3's User Product provisions apply, provide required Installation Information so recipients can install and run modified versions.
- Preserve required legal notices in interfaces and distributions, and satisfy each bundled dependency's own license requirements.

This is a summary, not legal advice or a compliance certification. Consult the actual licenses before publishing. No license files were changed for this README.

### Third-party components are not all GPL-3.0-or-later

The initial review identified these distinct licensing considerations; this is **not a complete dependency/license inventory**:

| Component | Verified licensing information / distribution review |
| --- | --- |
| `aur/` packaging material | [aur/LICENSE](aur/LICENSE) is BSD Zero Clause, with a 2026 ashmitvoid copyright notice; do not replace it with the application license. |
| Spotify code adapted from Sonora | GPL-3.0-or-later, with provenance above and in the crate's own documentation. |
| Pinned librespot fork | MIT; its license retains Paul Lietar's copyright and notice requirements. The actual source revision is pinned in `Cargo.toml` / `Cargo.lock`. |
| `libmpv2` 4.1.0 and `libmpv2-sys` 4.0.1 | Registry metadata declares LGPL-2.1 for these Rust bindings; do not confuse the wrapper's license with the native engine's. |
| Native mpv/libmpv | The [mpv copyright file](https://github.com/mpv-player/mpv/blob/master/Copyright) describes default GPL-2.0-or-later and an LGPL configuration excluding GPL-only files. Review the exact build and linked libraries. |
| FFmpeg | [Licensing depends on build configuration and enabled components](https://www.ffmpeg.org/legal.html); a bundled binary needs its own source/notice and compatibility review. |
| yt-dlp | Source is under the Unlicense, but [bundled release executables can have additional licensing obligations](https://github.com/yt-dlp/yt-dlp#licensing), including GPLv3+ code. Review the artifact, not just the source repository license. |

Before shipping, inventory the resolved Rust/frontend dependencies, native codecs/libraries, Qt/Quickshell if retained, fonts, icons and skins. Verify license compatibility, required notices and source/relinking obligations for the chosen binaries and distribution channel. No blanket legal guarantee is made for Windows installers or Android packages.

Software licensing does not grant ownership of music, provider accounts, service APIs, artwork or trademarks, and does not imply upstream endorsement. Third-party names and trademarks remain the property of their respective owners. Ryotune-Omni is not affiliated with, authorized by, sponsored by, or endorsed by YouTube or Google; YouTube and YouTube Music are trademarks of Google LLC. Provider terms and applicable law remain separate obligations.

## Relationship with upstream

- **Direct upstream: [Ryotunes](https://github.com/Ryoku-dev/ryotunes)** - the inherited Linux-first application and its implementation baseline.
- **Ryoku: [Ryoku-dev/ryoku](https://github.com/Ryoku-dev/ryoku)** - the original desktop/distribution environment and shell/design integration. Older `ryoku-arch` repository links redirect here.
- **Earlier origins:** LiMusic and Sonora, credited in the licensing section and retained provenance documentation.

Ryotune-Omni is maintained independently. These upstream projects remain authoritative for their own codebases, features, development and contribution guidelines. Their releases, branding and community channels do not represent this fork.

The goal is to follow relevant upstream fixes and improvements while diverging only where Windows/Android support or maintainability requires it. Port-specific decisions and parity gaps should be documented so upstream work can be integrated without misrepresenting compatibility.

## Contributing

Contributions are welcome in:

- Portability and dependency audits, including native-library and license inventories.
- Rust backend compatibility and isolation of platform-specific functionality.
- Windows hosting, IPC, media controls, paths and packaging.
- Android native integration, mobile UI, storage, permissions and service lifecycle.
- Audio engines, authentication, downloads and external integrations.
- Reproducible tests, playback/resource measurements, bug reports, documentation and feature-parity tracking.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), keeping in mind that its desktop-host and setup instructions describe the inherited Linux application. Preserve its audio-only, backend-owned playback, explicit-Quit, event-driven update and restrained-design contracts where applicable; document target-specific differences.

Prefer small, reviewable contributions with explicit scope, alternatives, limitations and verification results. Discuss architectural choices in a focused proposal before attempting a broad framework migration. A successful compile alone does not establish playback or feature parity.

At this documentation update the fork's GitHub Issues and Discussions were disabled; no dedicated fork community channel is advertised. Use the repository's available pull-request mechanism for contributions/proposals, and use a fork issue tracker for reports if one is enabled later. Do not send fork-specific port failures to upstream as confirmed upstream bugs. Reports should identify the commit, OS/device/toolchain, provider/account prerequisites, reproduction steps, expected/actual behavior and checks actually run. Remove credentials and personal data from logs.

## Disclaimer and acknowledgments

Ryotune-Omni is experimental software, provided under the warranty and liability terms of its licenses. Port feasibility, feature parity, provider availability, release dates and distribution approval are not guaranteed.

Thanks to the Ryotunes, Ryoku, LiMusic and Sonora authors and contributors, and to the maintainers of Rust, Tauri, Svelte, Qt/Quickshell, mpv, librespot, FFmpeg, yt-dlp and the other projects on which this work depends. Their work remains credited to its original authors.
