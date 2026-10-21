# W26 — Baseline visual Ryotunes para Windows

Estado: inventario estático inicial. La paridad visual con Linux es el objetivo; no se propone rediseño. No hay capturas comparables de ambos runtimes, por lo que la inspección no acredita paridad visual en ejecución.

## Autoridad visual

- El cliente Linux Quickshell/QML (`client/shell.qml`, `client/App.qml`, `client/Style.qml` y `client/chrome/`) es la referencia visual.
- `docs/DESIGN.md` define el lenguaje compartido: Ryoku-native, cálido, arquitectónico, denso sin agobio, artwork como foco, hairlines, radios compactos y movimiento con propósito.
- La UI Windows existente en `ui/` es el destino a comparar, no una autoridad que cambie la referencia.
- Windows puede adaptar integración de ventana e interacción que dependa del sistema; no debe cambiar composición, jerarquía ni carácter por conveniencia del framework.

## Rasgos que deben conservarse

1. **Marco de aplicación:** barra superior, rail de navegación, contenido, panel Queue/Lyrics y transporte persistente; separaciones y orden visual coherentes con `client/App.qml`.
2. **Artwork como centro:** portada dirige el foco; fondos/backdrop y acento acompañan, sin competir con el contenido.
3. **Sistema visual:** colores semánticos Ryoku cuando estén disponibles; oscuro casi tinta, claro cálido y contenido; acento derivado de artwork/proveedor según política.
4. **Tipografía:** los roles UI, display y mono de `client/Style.qml`; conservar sus jerarquías, escalas y etiquetas mono, sin sustituciones que cambien personalidad o densidad.
5. **Geometría:** cuadrícula de 4 px escalada, bordes finos, radios compactos y densidades de navegación/listas; evitar estética de tarjetas redondeadas genéricas.
6. **Reproductor:** barra inferior y Now Playing pertenecen al mismo sistema; transporte legible, controles centrados, artwork y estados consistentes.
7. **Movimiento:** transiciones como respuesta a navegación/acción; respetar reducción de movimiento y evitar animación ambiental añadida.

## Diferencias estáticas por validar visualmente

| Zona | Evidencia QML/Linux | Evidencia Svelte actual | Validación necesaria |
| --- | --- | --- | --- |
| Marco y medidas | `Style.qml`: titlebar 44 px, rail 248 px, panel 340 px, player 88 px y padding de página 32 px a escala 1. `App.qml` organiza rail, contenido, panel y transporte. | `layout.css` fija titlebar a 32 px; `+layout.svelte` calcula overlay para rail de 64/268 px y reserva 60 px para player. | Confirmar tamaño de ventana/DPI comparables y decidir si diferencias son intencionales o rompen silueta, alineación y espacio útil. |
| Colores y temas | `Style.qml` consume `Skin`/`Tokens` de Ryoku; acento puede seguir artwork, proveedor o skin. | `ryotunes.css` define paletas dark/light locales; `ryoku-live.ts` conecta tokens del host. | Verificar en runtime tema del sistema, paleta Ryoku, fallback y acento dinámico; no basta con que existan variables CSS. |
| Tipografía | QML selecciona `Skin.type.ui`, `display` y `mono`, además de fuente CJK. | `ryotunes.css` declara Space Grotesk, Fraunces y SpaceMono Nerd Font; las fuentes instaladas/cargadas se deben confirmar en Windows. | Comparar familia realmente renderizada, métricas, saltos/elipsis y títulos CJK con la misma escala. |
| Navegación | `Sidebar.qml`: grupos con micro-etiquetas mono, hairlines y filas de 40 px; rail nominal de 248 px. | `Sidebar.svelte`: grupos equivalentes y marca Ryotunes; anchura expandida 16.75 rem y rail compacto de 4 rem. | Comparar densidad, grupos, estados activos, marca y alineación; confirmar que colapsar no cambia identidad. |
| Home y páginas | `HomePage.qml` documenta saludo/hero, mood chips, pinned grid y shelves con paginación incremental. | `+page.svelte` usa `HomeHero`, `Shortcuts`, `RecentRail`, `Shelf`, favoritos y layout propio. | Comparar contenido equivalente, proporciones de hero/artwork, orden, márgenes y scroll con estados/datos iguales. |
| Transporte y Now Playing | `PlayerBar.qml`: tres zonas, transporte centrado en ventana, seek hairline; `NowPlaying.qml` es artwork-first con lyrics y wash. | `PlayerBar.svelte` y `NowPlaying.svelte` implementan equivalentes, pero conservan estilos y dimensiones propios. | Comparar altura, centrado real, portada, jerarquía, paneles, seek y estados playing/paused/vacío. |
| SvelteKit / WebView | No aplica a QML. | `ui/` es SvelteKit + adapter-static y Tauri API. El layout inicia estado, temas y bridge en cliente. | El framework puede servir la SPA local; validar CSS/fonts, rutas/fallback, almacenamiento, diálogos, APIs y Tauri IPC en WebView2. Build no equivale a compatibilidad runtime. |

Las diferencias de dimensiones son hallazgos de código, no defectos visuales confirmados. Resolverlas comparando capturas, no suponiendo que números idénticos siempre sean necesarios.

## Protocolo de comparación y cierre

Capturar Linux y Windows en resolución y escala equivalentes, con el mismo tema, proveedor, artwork, cuenta/datos y estado de reproducción. Cubrir como mínimo:

- Home con contenido cargado y ventana vacía/loading;
- Search con resultados;
- Library o playlist con filas/artwork;
- detalle de álbum/artista;
- Queue y Lyrics abiertos;
- Now Playing abierto;
- reproductor paused/playing y ausencia de pista;
- rail expandido/colapsado y tema dark/light.

Para cada par, registrar ventana y DPI, diferencias de composición/medidas, color, tipografía, recorte de artwork, scroll y estados; adjuntar capturas. Clasificar cada diferencia como `corregir para paridad`, `adaptación necesaria de Windows` (con motivo) o `pendiente de evidencia`. Cerrar W26 solo cuando las diferencias visuales no justificadas estén resueltas o aceptadas explícitamente y WebView2 haya sido comprobado aparte.

## Alcance y límites

- W26 no autoriza mejoras de navegación, accesibilidad, nuevas funciones, cambio de marca ni rediseño; esas propuestas requieren trabajo separado.
- No se inspeccionaron capturas ni se ejecutó Quickshell en este entorno Windows. El inventario está basado en fuentes estáticas.
- `pnpm check`/`pnpm build` comprueban frontend, no fidelidad visual ni WebView2. La ejecución comparativa queda pendiente de runtimes Linux y Windows disponibles.
