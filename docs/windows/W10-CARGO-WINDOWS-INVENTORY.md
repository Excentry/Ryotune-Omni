# W10 — Inventario estático del grafo Cargo para Windows

**Estado: inventario estático; W10 no está cerrado.** Este documento describe el grafo Cargo que selecciona `ryotunes` para `x86_64-pc-windows-msvc` y los límites observables en el código. El intento de `cargo check` se bloqueó en el build script de Tauri porque falta el recurso nativo configurado; no demuestra que el target compile.

## Evidencia y alcance

Inspección realizada en checkout Windows con Rust/Cargo 1.94.0 y el `Cargo.lock` actual:

- `cargo metadata --locked --no-deps --format-version 1` — 12 miembros del workspace.
- `cargo tree --locked --target x86_64-pc-windows-msvc -p ryotunes --edges normal,build --prefix none` — grafo de dependencias activas para la app Tauri.
- `cargo tree --locked --target x86_64-pc-windows-msvc -p player -e normal,build --prefix none` — confirma `libmpv2 -> libmpv2-sys` en el target Windows.
- `cargo tree --locked --target x86_64-pc-windows-msvc -p ryotunesd -e normal,build -i gtk --prefix none` — el daemon arrastra GTK/WebKitGTK sin selección por plataforma en su manifest.
- `cargo check --locked -p ryotunes --target x86_64-pc-windows-msvc`, desde `VsDevCmd.bat -arch=x64` — **BLOCKED** en `src-tauri/build.rs:124`: `resource path 'libmpv-2.dll' doesn't exist`.
- Búsqueda estática de `std::os::unix`, sockets Unix y `cfg` de plataforma en `crates/` y `src-tauri/`.

Los árboles se resolvieron con el lockfile existente; no se editaron manifests ni lockfiles. `cargo check` alcanzó el build script de Tauri y paró al validar el recurso inexistente, antes de verificar el host completo. El target Rust x64 MSVC y Visual Studio 2022 Build Tools están instalados.

## Paquetes del producto Windows

El punto de entrada esperado es el paquete `ryotunes` (`src-tauri/`), no `cargo build --workspace`. Su grafo local incluye:

| Paquete | Función en el grafo | Observación Windows |
| --- | --- | --- |
| `ryotunes` | Host Tauri | Selecciona `windows` 0.61 para `target_os = "windows"`; incluye Tauri, WebView2 y plugins. |
| `ryotunes-core` | Estado y lógica compartida | Depende de providers, SQLite bundled, Tokio y el player; incluye `libc` solo en Linux. |
| `player` | Playback | `libmpv2` 4.1.0 y `libmpv2-sys` 4.0.1 están en el grafo Windows. La DLL/import library y su distribución no quedan resueltas por `cargo tree`. |
| `innertube` | YouTube/API | Dependencias Rust con TLS Rustls; no aparece una dependencia nativa Linux en su manifest. |
| `ryotunes-spotify` | Provider Spotify | Librespot 0.8 y resolver Git fijado en `Cargo.toml`; la compilación no Unix usa un stub FIFO que devuelve unsupported. |
| `ryotunes-soundcloud` | Provider SoundCloud | HTTP/Rustls y Tokio; sin dependencia nativa declarada en el manifest. |
| `ryotunes-tidal` | Provider TIDAL | HTTP/Rustls y Tokio; sin dependencia nativa declarada en el manifest. |
| `ryotunes-protocol` | Tipos de contrato | Serde/JSON; compartible. |
| `listen-protocol` | Tipos de Listen Together | Serde/JSON, incluido transitivamente por core. |

`ryotunesd`, `ryotunes-cli` y `sync-server` son miembros del workspace, pero no dependencias de `ryotunes`; quedan fuera del build normal del host Tauri. No usar `--workspace` como prueba del producto Windows sin decidir antes qué binarios deben ser multiplataforma.

## Dependencias de plataforma y build

- En `src-tauri/Cargo.toml`, `windows` es target-specific. `ksni`, `libc` y `webkit2gtk` se declaran para Linux. El árbol MSVC incluye `tauri-build` como build-dependency y crates de Windows/WebView2, no GTK/WebKitGTK a través del paquete `ryotunes`.
- Tauri trae dependencias de build Windows como `tauri-winres`, `embed-resource` y `vswhom-sys`; `cargo tree` confirma selección, no requisitos instalados de MSVC/SDK ni éxito del resource compiler.
- `crates/player/Cargo.toml` declara `libmpv2` sin separar por target. El wrapper compila contra `libmpv2-sys`. `src-tauri/tauri.windows.conf.json` enumera `libmpv-2.dll` como recurso, pero ese archivo no está en `src-tauri/` en este checkout. El grafo tampoco confirma ABI, linkage ni dependencias runtime; resolver y validar con build Windows real (W12/W20), sin agregar ni regenerar el binario desde esta tarea.
- `crates/spotify/Cargo.toml` limita `libc` a Unix, pero `crates/spotify/src/stream.rs` usa FIFO únicamente bajo `cfg(unix)` y devuelve error en `cfg(not(unix))`. Por tanto, presencia de Spotify en el grafo MSVC no equivale a streaming Spotify funcional; transporte alternativo pertenece a W23.
- `souvlaki` aparece con feature `use_zbus` en manifests compartidos; el árbol MSVC no incluye zbus como backend activo. Confirmar controles Windows/SMTC en runtime; no inferirlos de la resolución del grafo.

## Paquetes fuera del host que no son Windows-ready

- `crates/ryotunesd/Cargo.toml` declara incondicionalmente `gtk`, `glib`, `webkit2gtk`, `javascriptcore`, `ksni` y `libc`. `crates/ryotunesd/src/main.rs` importa `std::os::unix` y `tokio::signal::unix`; `server.rs` usa `UnixListener`/`UnixStream` y activación systemd. No es un daemon Windows: coincide con la arquitectura aprobada de Tauri integrado y no debe agregarse accidentalmente al build Windows.
- `crates/ryotunes-cli/src/main.rs` importa `std::os::unix::net::UnixStream`. Su cliente RPC es Unix-only; el validador local de skins es aparte. Mantenerlo fuera de targets MSVC o plantear port explícito si se necesita un CLI Windows.
- `crates/core/src/update.rs` implementa actualización mediante pacman/Void y rutas Linux. `installation()` rechaza otros targets, pero el módulo sigue presente; el mecanismo Windows no existe y debe quedar deshabilitado/no disponible, no confundirse con un updater portable.

## Conclusión y verificación que falta

El grafo de dependencias de la app Windows está delimitado y varias dependencias específicas Linux ya están condicionadas por target en `src-tauri`. La selección del paquete Tauri evita incluir el daemon Unix. `cargo check` queda bloqueado porque `src-tauri/tauri.windows.conf.json` refiere `src-tauri/libmpv-2.dll` y ese archivo no está presente. No se verificaron incompatibilidades de compilación de los crates compartidos, linkage de libmpv, DLL/runtime de WebView2 ni ejecución del host.

Siguiente verificación del owner en Windows/MSVC, después de confirmar Visual Studio C++ Build Tools, Windows SDK, WebView2 y el recurso libmpv:

```powershell
cargo check --locked -p ryotunes --target x86_64-pc-windows-msvc
```

Registrar primero el grafo por feature/target y resolver errores de compilación en sus crates dueños; no hacer que el CLI o daemon Unix entren en el producto solo para que `--workspace` pase. W10 solo se cierra cuando paquetes activos, build-dependencies, límites de APIs Unix y requisitos DLL estén confirmados por el owner con build reproducible.
