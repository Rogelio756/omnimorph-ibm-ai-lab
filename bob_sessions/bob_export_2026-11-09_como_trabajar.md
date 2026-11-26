# hola bob como podemos trabajarlo?

---

**Status:** active  **Date:** 2026-11-09

---

### 👤 User

hola bob como podemos trabajarlo?

---

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — c:\Users\Dell G3\Documents\omnimorph-pruebas\bob_sessions\sesion_dashboard_omnimorph_2026-11-04.md

### 🤖 Assistant

Hola. El contexto está claro. Retomamos el dashboard OMNIMORPH del 2026-11-04.

Aquí está el estado actual:

---

## ✅ Lo que existe
- Sistema de diseño completo en `dashboard/` (29 archivos, 15 componentes CSS)
- Páginas: `index.html`, `mateo.html`, `loader.html`
- Video hero y logo OMNIMORPH ya colocados
- Adaptador de datos `data-adapter.js`

## 🔴 Pendientes (en orden de prioridad)

**Alta:**
1. Fuentes locales (Jost, Inter, JetBrains Mono en `.woff2`) → `dashboard/assets/fonts/`
2. Logos IBM → `dashboard/assets/logos/ibm/`
3. Logo del programa → `dashboard/assets/logos/programa/`
4. `hero-poster.png` — captura del video como imagen de carga previa

**Media:**
5. Revisar portada en el navegador (video, overlay, logo JPG sobre fondo crema)
6. Completar `config/ui.config.json` con textos de leyenda
7. Menú hamburguesa para móvil

**Baja:**
8. Tema claro `light.css`
9. Íconos SVG
10. Integración tokens CSS con Streamlit

---

¿Por dónde arrancamos? Te doy algunas opciones:

**A)** Automatizar la descarga de las fuentes `.woff2` (Jost, Inter, JetBrains Mono) directamente desde los URLs del manifest.

**B)** Levantar el servidor local ahora y revisar visualmente cómo está la portada antes de seguir.

**C)** Trabajar en lo que tengas listo para subir: logos IBM o logo del programa, y actualizar el manifest.

**D)** Saltar a completar los textos en `ui.config.json` y el menú hamburguesa (no requiere assets externos).

¿Cuál prefieres, o tienes algo específico en mente?