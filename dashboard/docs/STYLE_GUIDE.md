# STYLE_GUIDE.md — Guía de contribución OMNIMORPH / MATEO

> Este documento es la referencia para cualquier persona que quiera añadir
> un componente, una métrica, un logo o una pantalla al sistema visual de
> OMNIMORPH. Léelo antes de escribir código.

---

## 1. Principio fundamental

**Nada de valores a mano en componentes.** Cada color, tamaño, radio o
espacio debe salir de `styles/tokens.css`. Si el valor que necesitas no
existe como token, añádelo primero en `DESIGN.md`, luego en `tokens.css`,
y anota el valor en la sección "Valores derivados" de `DESIGN.md`.

---

## 2. Cómo añadir un nuevo componente CSS

### Pasos
1. Crea `styles/components/<nombre>.css`.
2. Usa solo variables de `tokens.css`. Nunca `#RRGGBB` ni `px` escritos a mano.
3. Nombra clases con convención **BEM**:
   - Bloque: `.nombre-componente`
   - Elemento: `.nombre-componente__parte`
   - Modificador: `.nombre-componente--variante`
4. Importa el nuevo archivo en el `<head>` de cada página que lo use (en orden: tokens → base → layout → components).
5. Documenta en este archivo qué hace el componente y cómo usarlo.
6. No uses `!important` salvo que sea estrictamente necesario; si lo usas, añade un comentario `/* justificación */`.

### Ejemplo
```css
/* styles/components/mi-componente.css */
.mi-componente {
  padding: var(--cell-padding-y) var(--cell-padding-x);
  border: var(--border);
  color: var(--color-text);
}

.mi-componente__titulo {
  font-family: var(--font-headline);
  font-weight: var(--font-weight-medium);
  font-size: var(--text-title);
}

.mi-componente--activo {
  border-color: var(--color-ok);
}
```

---

## 3. Cómo añadir una nueva métrica

1. Abre `config/ui.config.json`.
2. Añade un objeto al array `metrics`:
   ```json
   { "id": "mi_metrica_en_json", "label": "Mi Métrica", "unit": "m/s" }
   ```
3. Actualiza `active_metric` si quieres que sea la predeterminada.
4. En `components/data-adapter.js`, asegúrate de que `adaptTactical()` mapea
   el campo `mi_metrica_en_json` desde el JSON del pipeline. Si el pipeline
   usa un nombre distinto, el mapeo va aquí, no en los componentes.
5. El componente `kpi-card.css` ya tiene los estilos necesarios; solo crea
   el HTML con los IDs correctos en `mateo.html`.

---

## 4. Cómo añadir un logo

1. Coloca el archivo SVG o PNG transparente en `assets/logos/<categoria>/`.
2. Abre `assets/logos/logos.manifest.json` y añade:
   ```json
   {
     "id": "mi-logo",
     "file": "categoria/mi-logo.svg",
     "alt": "Descripción accesible del logo",
     "max_width": 120,
     "variant": "light"
   }
   ```
   (Sin la clave `status`, o con `"status": "OK"`)
3. El sistema automáticamente lo mostrará en la franja "Impulsado por" o
   donde se lea el manifest.
4. Documenta la fuente y licencia en `assets/logos/README.md`.

---

## 5. Cómo añadir una nueva pantalla (página HTML)

1. Crea `pages/mi-pagina.html`.
2. Importa las hojas en el mismo orden que las existentes:
   ```html
   <link rel="stylesheet" href="../styles/tokens.css">
   <link rel="stylesheet" href="../styles/base.css">
   <link rel="stylesheet" href="../styles/layout.css">
   <!-- luego los componentes que uses -->
   ```
3. Añade un enlace en la navegación de `index.html` y `mateo.html`.
4. Si la página es autosuficiente (como `loader.html`), incrusta el CSS
   directamente en el `<head>` para que funcione sin archivos externos.
5. Actualiza `config/ui.config.json` si la página necesita un enlace en el nav.

---

## 6. Convención de nombrado

| Tipo        | Convención          | Ejemplo                   |
|-------------|---------------------|---------------------------|
| Clases CSS  | BEM con guiones     | `.kpi-card__value--empty` |
| IDs HTML    | kebab-case          | `kpi-bh-val`              |
| Archivos CSS | kebab-case         | `master-clock.css`        |
| Archivos JS | kebab-case          | `data-adapter.js`         |
| Tokens CSS  | `--tipo-nombre`     | `--color-team-a`          |
| IDs de logos | kebab-case         | `ibm-watsonx`             |
| Claves JSON | snake_case          | `block_height_m`          |

---

## 7. Checklist antes de hacer PR

- [ ] No hay valores de color/tamaño escritos a mano en componentes (todo es `var(--…)`)
- [ ] Ningún botón usa color de marca
- [ ] Contraste de texto ≥ 4.5:1 verificado
- [ ] Cada logo tiene `alt` descriptivo
- [ ] Botones icon-only tienen `aria-label`
- [ ] El componente funciona en 768 px de ancho (revisar breakpoints)
- [ ] La pantalla de carga (`loader.html`) sigue siendo autosuficiente
- [ ] Los datos de los componentes no vienen directamente del pipeline:
      pasan por `data-adapter.js`
- [ ] Si se añade un logo IBM: verificar reglas de uso en `assets/logos/README.md`
- [ ] Valores derivados nuevos documentados en `DESIGN.md`
- [ ] `docs/STYLE_GUIDE.md` actualizado si el patrón nuevo no estaba aquí

---

## 8. Archivos pendientes que se deben proveer

| Archivo                              | Descripción                              | Dónde va               |
|--------------------------------------|------------------------------------------|------------------------|
| `hero.mp4` y `hero.webm`             | Video de estadio, 10–20 s, ≤ 10 MB, 1080p | `assets/hero/`      |
| `hero-poster.png`                    | Frame estático del estadio               | `assets/hero/`         |
| `hero-ambient.mp3`                   | Audio ambiente de estadio (sin voz)      | `assets/hero/`         |
| `omnimorph-logo.svg`                 | Logo OMNIMORPH (cubo + wordmark)         | `assets/logos/omnimorph/` |
| `omnimorph-cube.svg`                 | Solo el cubo de Rubik                    | `assets/logos/omnimorph/` |
| `IBM_logo.svg`                       | Logo IBM oficial (de IBM Brand Center)   | `assets/logos/ibm/`    |
| `watsonx_logo.svg`                   | Logo IBM watsonx oficial                 | `assets/logos/ibm/`    |
| `granite_logo.svg`                   | Logo IBM Granite oficial                 | `assets/logos/ibm/`    |
| `programa_logo.svg`                  | Logo del programa / institución          | `assets/logos/programa/` |
| Jost-Regular.woff2                   | Fuente Jost peso 400                     | `assets/fonts/`        |
| Jost-Medium.woff2                    | Fuente Jost peso 500                     | `assets/fonts/`        |
| Inter-Regular.woff2                  | Fuente Inter peso 400                    | `assets/fonts/`        |
| Inter-Medium.woff2                   | Fuente Inter peso 500                    | `assets/fonts/`        |
| JetBrainsMono-Medium.woff2           | JetBrains Mono peso 500                  | `assets/fonts/`        |

### Cómo descargar las fuentes localmente
```bash
# Opción 1: desde Google Fonts (Jost e Inter) con google-webfonts-helper
# Visita: https://gwfh.mranftl.com/fonts/jost?subsets=latin
# Descarga los .woff2 de peso 400 y 500

# Opción 2: JetBrains Mono desde el repo oficial
# https://github.com/JetBrains/JetBrainsMono/releases
```

---

## 9. Cómo ejecutar el proyecto

### Tablero interactivo (Streamlit, con datos reales)
```bash
# Desde la raíz del repositorio:
.\.venv\Scripts\python.exe -m streamlit run implementacion/dashboard/app.py
```

### Páginas HTML estáticas (portada, tablero, loader)
```bash
# Opción 1: Python (desde la carpeta dashboard/)
python -m http.server 8080
# Luego abrir: http://localhost:8080/pages/index.html

# Opción 2: Node (desde la carpeta dashboard/)
npx serve . -p 8080
```

Las páginas HTML también pueden abrirse directamente con doble clic (modo
archivo), pero algunas funciones JS (carga de JSON) requieren un servidor
HTTP por restricciones CORS del navegador.

---

## 10. Verificación de calidad

Antes de considerar terminado cualquier cambio visual:

1. **Contraste:** usa https://webaim.org/resources/contrastchecker/ — mínimo 4.5:1
2. **Sin colores a mano:** `grep -r "#[0-9a-fA-F]" styles/components/` debe dar 0 resultados
3. **Portada con video ausente:** quitar `hero.mp4`; debe verse el poster y funcionar el botón
4. **Portada con audio bloqueado:** no debe aparecer ningún error en consola
5. **Movimiento reducido:** en DevTools, simular `prefers-reduced-motion: reduce`;
   el video debe sustituirse por el poster y todos los dots deben quedar estáticos
6. **Loader sin red:** abrir `pages/loader.html` sin servidor; debe mostrar cubo + dots
7. **Mobile (360 px):** sidebar de jugadores baja debajo del contenido
