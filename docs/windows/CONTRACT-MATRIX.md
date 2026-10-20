# W14 — Matriz estática de contratos Tauri / daemon

Estado: inventario estático terminado con diferencias registradas. No implica runtime verificado. Fuentes principales: `ui/src/lib/api.ts`, `src-tauri/src/commands.rs`, `src-tauri/build.rs`, `crates/ryotunesd/src/methods.rs`, `client/Daemon.qml`, `client/lib/playback.js`.

## Convenciones

- `T` es el tipo indicado por `invoke<T>` en `api.ts`; `void` resuelve `null` en el protocolo socket. Campos opcionales aceptan omisión/null según wrapper Rust y `arg<Option<T>>`.
- Tauri rechaza con string cuando handler devuelve `Err(String)`; daemon serializa `ErrorBody { code, message }`. `arg<T>` falla como `bad_params`; error de dominio usa `failed`. Para comandos sin error Rust explícito, error de transporte/serialización sigue siendo posible. No se afirma equivalencia exacta de texto ni semántica de error.
- Las firmas siguientes transcriben el contrato frontend tipado (`api.ts`) con llaves camelCase wire. La semántica / errores de dominio se conservan en implementaciones fuente; se anotan abajo las diferencias comprobadas.

## Comandos: nombre, parámetros, resultado

| Área | Contratos por método (`nombre(params) -> resultado`) |
| --- | --- |
| Búsqueda | `search(query:string)->SongItem[]`; `search_page(query:string)->SongSearchPage`; `search_page_more(token:string)->SongSearchPage`; `search_all(query:string)->SearchResults`; `search_all_more(token:string)->SearchResults`; `search_cards(query:string,category:'albums'|'artists'|'playlists')->BrowseItem[]`; `search_cards_page(query:string,category:'albums'|'artists'|'playlists')->SearchCardPage`; `search_cards_more(token:string)->SearchCardPage`. |
| Playback / cola | `play(item:SongItem)->void`; `prefetch_stream(videoId:string,isUpload?:boolean=false)->void`; `play_index(index:number)->void`; `remove_from_queue(index:number)->void`; `move_in_queue(from:number,to:number)->void`; `play_next(items:SongItem[],from?:string)->void`; `add_to_queue(items:SongItem[],from?:string,continuation?:string)->void`; `clear_queued()->void`; `next_track()->void`; `prev_track()->void`; `toggle_shuffle()->void`; `set_repeat(mode:RepeatMode)->void`; `set_stop_after_current(enabled:boolean)->void`; `toggle_pause()->void`; `seek(position:number)->void`; `set_volume(volume:number)->void`; `set_playback_params(speed:number,semitones:number)->void`; `get_queue()->QueueState`; `get_playback()->PlaybackSnapshot`. |
| Ajustes / cuenta | `get_settings()->Record<string,string>`; `set_setting(key:string,value:string)->void`; `discord_status()->DiscordStatus`; `get_stream_clients()->string[]`; `clear_caches(rotate?:boolean=true)->{visitorDataRefreshed:boolean}`; `get_personal()->{personal:unknown}`; `set_personal(personal:unknown)->void`; `get_account()->Account`; `get_account_identities()->AccountIdentity[]`; `switch_account(selectionKey:string)->Account`; `sign_out()->void`; `login_webview()->void`; `frontend_ready(label:'main'|'mini')->void`; `open_mini()->void`; `close_mini()->void`. |
| Actualización / host | `check_for_updates()->UpdateInfo`; `install_update(version:string)->UpdateInstallResult`; `ryoku_theme_tokens()->RyokuThemeTokens`; `open_external(url:string)->void`. |
| Browse / biblioteca | `get_home(params?:string)->HomePage`; `get_home_more(token:string)->HomePage`; `get_library()->BrowseItem[]`; `get_library_albums()->BrowseItem[]`; `get_library_artists()->BrowseItem[]`; `get_playlist(id:string,sort?:ServerSort,desc?:boolean)->PlaylistPage`; `set_playlist_sort(playlistId:string,sort:ServerSort)->void`; `get_playlist_more(token:string)->PlaylistContinuation`; `playlist_index()->Record<string,string[]>`; `sync_playlist_index()->Record<string,string[]>`; `play_counts()->Record<string,number>`; `listening_stats(period:'day'|'week'|'month')->ListeningStats`; `get_album(id:string)->AlbumPage`; `get_artist(id:string)->ArtistPage`; `get_browse_grid(id:string,params?:string)->BrowseItem[]`. |
| Reproducción de colecciones / radio | `play_playlist(items:SongItem[],start:number|null,sourceId?:string,sourceName?:string,shuffle?:boolean,continuation?:string)->void`; `start_radio(kind:'song'|'artist'|'album'|'playlist',id:string,name?:string)->void`; `radio_stations(query?:string='',offset?:number=0,limit?:number=36)->RadioStation[]`; `play_radio_station(stationUuid:string)->void`. |
| Importar/exportar | `export_playlist_file(title:string,items:SongItem[])->boolean`; `import_playlist_file()->PlaylistTransfer|null`. |
| Música local | `get_local_library()->LocalLibrary`; `add_local_folder()->LocalLibrary|null`; `remove_local_folder(path:string)->LocalLibrary`. |
| Escrituras | `rate(videoId:string,rating:Rating)->void`; `add_to_playlist(playlistId:string,videoId:string)->boolean`; `add_to_local_playlist(playlistId:string,item:SongItem)->boolean`; `remove_from_playlist(playlistId:string,videoId:string,setVideoId:string)->void`; `create_playlist(title:string)->string`; `edit_playlist_details(playlistId:string,name?:string,description?:string,public?:boolean)->void` (wrapper acepta `changes`, aplana campos); `set_playlist_cover(playlistId:string,pick:boolean)->{cover?:string,thumbnail?:string}|null`; `delete_playlist(playlistId:string)->void`; `subscribe(channelId:string,subscribed:boolean)->void`; `set_album_saved(playlistId:string,saved:boolean)->void`. |
| Letras / Last.fm | `get_lyrics(videoId:string,title:string,artists:string,album?:string,duration?:number)->Lyrics|null`; `lastfm_status()->LastfmState`; `lastfm_connect()->void`; `lastfm_disconnect()->void`. |
| Listen Together | `lt_get_state()->LtState`; `lt_set_server_url(url:string)->void`; `lt_create_room(username:string)->void`; `lt_join_room(code:string,username:string)->void`; `lt_leave()->void`; `lt_approve_join(userId:string)->void`; `lt_reject_join(userId:string)->void`; `lt_kick(userId:string)->void`; `lt_transfer_host(userId:string)->void`; `lt_suggest(item:SongItem)->void` (Tauri command, no Svelte wrapper); `lt_approve_suggestion(id:string)->void`; `lt_reject_suggestion(id:string)->void`; `lt_request_sync()->void`. |

Conteo mecánico: 96 nombres invocados por `api.ts`, todos con función Tauri registrada; `lt_suggest` es comando Tauri registrado adicional sin wrapper en `api.ts`. De los 96 nombres de UI, 92 tienen arm daemon exacto. Los otros cuatro (`frontend_ready`, `login_webview`, `open_mini`, `close_mini`) están agrupados en un arm que devuelve `client_side`; `ryoku_theme_tokens` también tiene arm pero devuelve `client_side`. `subscribe` acepta dos esquemas/semánticas incompatibles. Por tanto, coincidencia de nombre no equivale a paridad: 90 métodos son coincidencias funcionales candidatas, 5 son client-side/no soportados por ese host y uno (`subscribe`) colisiona semánticamente.

## Diferencias verificadas de contrato / errores

| Método | Tauri | Daemon | Consecuencia / prueba pendiente |
| --- | --- | --- | --- |
| `add_local_folder` | No args; native folder picker; cancel -> `null`; returns `LocalLibrary` | Requiere `{path}`; devuelve `Some(LocalLibrary)`; path inválido -> `failed` | Adaptar picker nativo, validar directorio y probar cancelación/raíz/permisos. |
| `import_playlist_file` | No args; native file picker; cancel -> `null`; `PlaylistTransfer|null` | Requiere `{path}`; validación de extensión/tamaño/schema; `null` no representa cancelación | Host debe mantener picker y mismos límites. |
| `export_playlist_file` | `{title,items}`; native save picker; devuelve bool (`false` cancel) | `{title,items,path}`; devuelve resultado/error | Mantener confirmación de destino y atomicidad; probar cancelación, sobrescritura/error IO. |
| `set_playlist_cover` | `{playlistId,pick}`; native image picker; devuelve objeto nullable | Con `pick=true` espera también `path`; devuelve objeto nullable | Windows debe usar picker y validar JPEG/PNG, máximo 8 MiB. |
| `subscribe` | `{channelId,subscribed}`; escribe suscripción a canal YouTube | `subscribe({events:["*"]})` agrega conexión al stream y responde snapshot | Colisión incompatible. QML `ArtistPage.qml` también llama nombre daemon con `channelId/subscribed`, pero dispatch solo subscribe conn; write parece perdido. Runtime Linux por confirmar. Separar nombres en cualquier bridge. |
| `ryoku_theme_tokens` | Devuelve `RyokuThemeTokens` desde host Tauri/Ryoku | Dispatch responde `{code:"client_side",message:...}`; QML lee singleton directamente | Sin API de tokens en socket. Windows requiere paleta propia o adaptación equivalente; no tratar nombre como API daemon. |
| `add_to_playlist` | Devuelve bool | YouTube devuelve bool; rama Spotify termina `null` | Incumple `boolean` tipado; corregir y testear duplicate/success Spotify. |
| `edit_playlist_details` | Params planos `playlistId,name?,description?,public?`; wrapper aplana `changes` | Mismos campos planos leídos por `arg<Option<T>>` | Esquema coincide; behavior device playlists limita campos. |
| Errores generales | `Result<T,String>` se presenta como rechazo string a JS | `{code,message}`, códigos `bad_params` y `failed` | Adaptador Windows debe normalizar sin borrar código/mensaje; pruebas de bad params y errores de dominio. |
| `frontend_ready`,`login_webview`,`open_mini`,`close_mini` | Responsabilidad nativa Tauri (handshake/login/window) | Arm agrupado responde `{code:"client_side"}`; `sign_in`, `show` y lifecycle daemon cubren partes, no alias uno-a-uno | Preservar comportamiento en host propio; no invocar nombres Tauri al daemon. |
| Providers/descargas/FX/diagnóstico | Faltan wrappers/comandos Tauri equivalentes para `set/get_provider`, auth Spotify/SC/TIDAL, FX/waveform, descargas y logs de daemon | Métodos disponibles en daemon, incluidos en snapshot/eventos | Gaps de paridad de superficies; no presentar como API Windows ya implementada. |

Los demás métodos comparten los nombres de campos y tipos de entrada declarados en el inventario y decodificados por `arg<T>`/firmas Tauri. No se codifica aquí una garantía de equivalencia semántica de providers: daemon enruta varios métodos según provider activo y Tauri mantiene backend/host separado. Para cada `Result` de dominio: Tauri string reject; daemon `failed` con texto. Errores de lectura de params son `bad_params`; diálogo cancelado sigue los resultados explícitos de tabla.

## Eventos: payload, productor, consumidor y prueba

| Evento | Payload / origen estático | Consumidor | Prueba existente / gap |
| --- | --- | --- | --- |
| `now-playing` | `NowPlaying`; `AppState` emite item más stream client (`core/state.rs`) | QML Playback reducer; Svelte `onNowPlaying` | `client/tests/tst_playback.qml` cubre reducer parcial; falta contrato payload productor-consumidor. |
| `rating` | `{videoId,rating}`; core | Playback reducer / Svelte listener | tst_playback parcial; falta prueba wire. |
| `queue-changed` | `QueueState`; core | Playback reducer / listener Svelte | tst_playback parcial; falta schema contract. |
| `queue-index` | `currentIndex,playedFrom?,shuffle?,repeat?,sourceName?,current` | Playback reducer / listener Svelte | tst_playback cubre parche de fila; falta prueba campos opcionales. |
| `position`,`duration` | `{position:number}`, `{duration:number}`; daemon app loop / Tauri player loop | Playback reducer/listeners | `crates/ryotunesd/src/server.rs` prueba ejemplo de framing position; sin integración. |
| `volume` | number escalar; core | Playback reducer / listener | tst_playback cubre drag/echo; falta host integration. |
| `playback-state` | string `playing|paused`; core y host poller | Playback reducer/listener | tst_playback cubre estado básico; falta fuente dual test. |
| `stop-after-current` | boolean; core | Playback reducer/listener | tst_playback; cubrimiento parcial. |
| `playback-error` | `{message}` desde host app; core puede añadir `videoId` | Playback reducer lee `message`; Svelte listener | Sin prueba de forma extra; aditivo compatible. |
| `playback-notice` | `{message}`; core | Playback toast/listener | No se encontró test de contrato. |
| `cover-error` | `{message}`; Tauri command background sync y daemon methods | Playlist UI / Svelte listener | No se encontró test de payload. |
| `auth-changed` | Account snapshot; core | QML shell/account views / Svelte listener | No se encontró prueba wire. |
| `account-selection-required` | null/unit; core | QML auth flow / Svelte callback | No se encontró test. |
| `local-changed` | `{removed:string[]}`; core local rescan | QML library/playback / Svelte listener | Sin test de emisión/consumo. |
| `login-error`,`login-done` | string / unit; core session | QML login flow / Svelte listeners | Sin test de contrato. |
| `audio-fx` | AudioFx serializado; core | QML Playback/UI | Sin listener Svelte equivalente ni test. |
| `provider-changed` | `{provider}`; daemon methods | QML shell/provider surfaces | Sin Tauri listener ni test. |
| `spotify-auth` | tagged state: `restored`, `restore_failed/message`, `url/url`, `signed_in/name`, `signed_out`, `error/message` | QML provider/auth surfaces | Sin test de secuencia. |
| `soundcloud-auth` | tagged state: `signed_in/name`, `error/message`, `waiting`, `expired/message`, `signed_out` | QML provider/auth surfaces | Sin test de secuencia. |
| `tidal-auth` | tagged state: `signed_out`, `waiting/url/code`, `signed_in/name/quality`, `expired/message`, `error/message` | QML provider/auth surfaces | Sin test de secuencia. |
| `personal-changed` | blob personal; core | `Personal.qml` | Sin test de emisión. |
| `library-changed` | `{id}`; daemon writes | Library/Playlist pages, sidebar, library components | Sin test de propagación global. |
| `downloads-changed` | downloads snapshot; `Downloads` manager | `Downloads.qml`, download button/page | `tst_collections.qml` prueba grouping, no payload event. |
| `show` | null; daemon tray | `shell.qml` muestra ventana | Sin test de host activation. |
| `ryoku-theme-changed` | `RyokuThemeTokens`; Tauri Ryoku host | Svelte theme listener; QML obtiene tokens por su runtime | No equivale a evento portable; fuente de tema Windows pendiente. |
| `lastfm-state` | `LastfmState` (configured/connected/username/error); core Last.fm | Svelte listener; QML settings/status | Sin test de emisión. |
| `lt-state` | `LtState` snapshot; core Listen Together | QML Listen Together / Svelte listener | No test de contrato payload. |
| `lt-notice` | string; core Listen Together | QML/Svelte notice listener | No test de payload. |

Eventos sin listener Svelte equivalentes (provider, FX, personal/library/downloads/show) son gap visible para Windows hasta que UI los consuma mediante evento o refresco explícito. Productores/casos sin tipo completo en código están marcados por la forma observada; añadir schema formal y tests al crear bridge Windows. Prueba QML focal existente: `qmltestrunner -input client/tests/tst_playback.qml`; no ejecutada en este W14.

## Cierre y trabajo restante

- W14 está completo como inventario estático fuente-a-fuente, no como verificación runtime.
- Confirmar en Linux el bug aparente `subscribe` de ArtistPage; corregir con owners y test (fuera de este inventario, no se modificó código).
- Corregir el resultado Spotify `add_to_playlist` para satisfacer boolean contract y cubrirlo con test.
- W21/W34: pruebas IPC, payloads y WebView2 en Windows. Baseline de W13 no verifica esto.
