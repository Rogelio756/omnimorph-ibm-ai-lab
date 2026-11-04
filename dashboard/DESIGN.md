# DESIGN.md — Sistema de Estilo OMNIMORPH / MATEO
> Única fuente de verdad visual. Todo valor concreto se define aquí primero
> y luego se traslada a `styles/tokens.css`. Nunca escribir valores a mano
> en componentes.

---

## 1. Principios

- **Galería oscura:** la interfaz es casi invisible; el protagonismo lo tienen
  el video del estadio, el logo y los datos.
- **Sin color de marca en la interfaz.** El color proviene del logo, del video
  y de los datos de equipos.
- **Números en monoespaciada** (JetBrains Mono 500).
- **Una sola familia de formas:** píldora (30 px) para botones, chips y
  etiquetas; radio 0 para tarjetas, celdas, video y logos.
- **Rejilla con líneas finas** (1 px, `#2A2A2A`) en lugar de tarjetas con
  relleno.
- **Sin sombras ni degradados decorativos** (única excepción: capa oscura
  sobre el hero).

---

## 2. Paleta de colores

### Fondo y superficie
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-bg`           | `#111111` | Fondo principal de todas las páginas oscuras |
| `--color-bg-deep`      | `#0A0A0A` | Fondo más profundo (hero, video)             |
| `--color-surface`      | `#1A1A1A` | Superficie de celdas y paneles               |
| `--color-border`       | `#2A2A2A` | Bordes de rejilla, líneas de 1 px            |
| `--color-border-soft`  | `#3A3A3A` | Bordes suaves, divisores secundarios         |

### Texto
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-text`         | `#FFFFFF` | Texto principal                              |
| `--color-text-soft`    | `#A1A1AE` | Etiquetas, subtítulos, pies (nunca más oscuro sobre negro) |

### Equipos y balón
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-team-a`       | `#F5A623` | BRA (naranja) — siempre legible sobre negro  |
| `--color-team-b`       | `#F5F3EE` | GER (crema) — diferenciado por luminosidad   |
| `--color-ball`         | `#A3E635` | Balón (lima)                                 |

### Cancha
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-pitch`        | `#0E1A16` | Fondo de cancha en radar                     |
| `--color-pitch-lines`  | `#2A4A3E` | Líneas de cancha                             |

### Estado / semáforo
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-ok`           | `#1FC8B0` | Solo el punto del chip "OK" / "PASS"         |
| `--color-alert`        | `#F24E6B` | Alerta / FAIL                                |
| `--color-warn`         | `#F5A623` | Advertencia / WARN (reutiliza team-a)        |

### Especiales
| Token                  | Valor     | Uso                                          |
|------------------------|-----------|----------------------------------------------|
| `--color-logo-card`    | `#F5F3EE` | Tarjeta de logo (crema, bordes rectos)       |

### Tema claro (solo pantalla de carga/error)
| Token                        | Valor     |
|------------------------------|-----------|
| `--color-bg-light`           | `#FFFFFF` |
| `--color-text-light`         | `#111111` |
| `--color-text-soft-light`    | `#4B5563` |
| `--color-border-light`       | `#E5E7EB` |

---

## 3. Tipografía

| Rol         | Familia        | Peso | Tamaño / uso                                      |
|-------------|----------------|------|---------------------------------------------------|
| Titulares   | Jost           | 500  | Hero: 76 px, mayúsculas, interlineado 1.0         |
|             |                |      | Títulos de tarjeta: 24 px                         |
|             |                |      | Cifras KPI: 44 px                                 |
| Interfaz    | Inter          | 400  | Cuerpo: 14–16 px                                  |
|             |                | 500  | Etiquetas: 12 px, botones                         |
| Monoespaciada | JetBrains Mono | 500 | Números, tiempos, frames, código                 |

**Regla:** solo pesos 400 y 500. Nunca `font-weight: 700` (bold).

Fuentes instaladas localmente en `assets/fonts/`. El proyecto debe funcionar
sin conexión a internet.

---

## 4. Escala de espaciado (base 4 px)

| Token           | Valor |
|-----------------|-------|
| `--space-1`     | 4 px  |
| `--space-2`     | 8 px  |
| `--space-3`     | 12 px |
| `--space-4`     | 16 px |
| `--space-5`     | 20 px |
| `--space-6`     | 24 px |
| `--space-9`     | 36 px |
| `--space-12`    | 48 px |

Padding de celda: `20 px × 24 px`. Separación entre secciones: `48 px`.

---

## 5. Radios

| Token              | Valor  | Aplicación                             |
|--------------------|--------|----------------------------------------|
| `--radius-pill`    | 30 px  | Botones, chips, etiquetas              |
| `--radius-card`    | 0 px   | Tarjetas, celdas, video, logos         |

---

## 6. Botones

**Un solo estilo principal:**
- Píldora blanca (`#FFFFFF`) con texto `#111111`
- Altura mínima 44 px, padding `12 px 24 px`
- El texto nunca usa color de marca

**Secundario (contorno):**
- Fondo transparente, borde 1 px `#FFFFFF`, texto `#FFFFFF`
- Mismas proporciones que el principal

**Prohibido:** botones con color de marca (naranja, turquesa, morado, etc.)

---

## 7. Movimiento

- Duración: **150 ms**, `ease-out`
- Solo se animan: fondo de portada, indicador de carga, chip "en vivo"
- **`prefers-reduced-motion`:** todo se detiene; el video se sustituye por
  el poster; el indicador de carga pierde la animación

---

## 8. Accesibilidad

- Contraste mínimo **4.5:1** en todo texto sobre fondo
- Objetivos táctiles **≥ 44 px**
- Botones icon-only llevan `aria-label`
- Cada logo lleva `alt` descriptivo
- Equipos distinguibles también por **luminosidad**, no solo por tono:
  BRA naranja (`#F5A623`, L≈69%) vs GER crema (`#F5F3EE`, L≈96%)

---

## 9. Prohibiciones explícitas

- ❌ Emojis como iconos de interfaz (usar SVG de línea)
- ❌ Color de marca en la interfaz
- ❌ Sombras de más de 8 px
- ❌ Azul vs rojo para equipos
- ❌ `font-weight: 700` o superior
- ❌ `border-radius` en tarjetas/celdas/video/logos
- ❌ Verde brillante en la cancha (usar `#0E1A16`)
- ❌ Parpadeos (`blink`) o rebotes (`bounce`) en animaciones
- ❌ `!important` salvo comentario que justifique por qué

---

## 10. Valores derivados (no estaban en el brief, se deducen de los principios)

| Valor                      | Derivación                                                 |
|----------------------------|------------------------------------------------------------|
| `font-size` cuerpo: 15 px  | Punto medio entre 14–16 px del brief                      |
| `line-height` cuerpo: 1.6  | Legibilidad estándar para texto de 15 px                  |
| `letter-spacing` wordmark: 0.2em | Especificado en el brief para "OMNIMORPH"            |
| `letter-spacing` títulos KPI: -0.02em | Jost a 44 px se comprime ligeramente             |
| Ancho sidebar jugadores: 320 px | Valor explícito del brief                             |
| Grosor líneas de cancha: 1 px | Consistente con `--color-border`                        |
| Barra BRA/GER en KPI: 4 px alto | Valor explícito del brief                            |
| Separación mínima de logos IBM: 1× su altura | Regla de marca IBM estándar              |
| Chip "en vivo": pulso 1 s loop | Animación de punto turquesa; se detiene con reduced-motion |
| Overlay hero: `linear-gradient(to right, rgba(0,0,0,.75) 0%, rgba(0,0,0,.2) 100%)` | Más fuerte a la izquierda para legibilidad del titular |
| `--color-surface` `#1A1A1A` | Un paso entre `#111111` y `#2A2A2A`                       |
