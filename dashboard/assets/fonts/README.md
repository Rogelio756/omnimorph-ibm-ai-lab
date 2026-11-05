# Fuentes locales

Fuentes del sistema de diseño (`DESIGN.md` §3), servidas localmente para que el tablero funcione sin conexión.

| Archivo | Familia | Peso | Tamaño | sha256 (12 primeros) |
|---|---|---|---|---|
| `Jost-Regular.woff2` | Jost | 400 | 9 404 B | `f94cffda1651` |
| `Jost-Medium.woff2` | Jost | 500 | 10 476 B | `98dce4f076fe` |
| `Inter-Regular.woff2` | Inter | 400 | 23 664 B | `8909904ab6c8` |
| `Inter-Medium.woff2` | Inter | 500 | 24 272 B | `f3779f1efccc` |
| `JetBrainsMono-Medium.woff2` | JetBrains Mono | 500 | 21 832 B | `cb182feeed4d` |

- **Origen:** proyecto [Fontsource](https://fontsource.org), vía `https://cdn.jsdelivr.net/fontsource/fonts/<familia>@latest/latin-<peso>-normal.woff2`, con `<familia>` = `jost`, `inter` o `jetbrains-mono`.
- **Descargadas:** 2026-11-04. La URL usa `@latest`, no una versión fija: si vuelves a descargarlas pueden diferir, y los sha256 de arriba identifican estos archivos.
- **Subconjunto:** solo `latin`, que incluye acentos, `¿`, `¡` y `ñ`. No incluye cirílico, griego ni vietnamita.
- **Licencia:** las tres familias se distribuyen bajo la SIL Open Font License 1.1, que permite usarlas y redistribuirlas, también con el proyecto, siempre que se conserve el aviso de licencia de cada una. Este repositorio no incluye los textos de licencia originales: antes de redistribuirlo públicamente, añádelos desde los repositorios de cada fuente.
