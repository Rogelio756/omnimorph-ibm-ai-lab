# assets/logos/README.md — Guía de logos OMNIMORPH

## Estructura de carpetas

```
assets/logos/
├── omnimorph/      Logo principal OMNIMORPH y variantes
├── ibm/            Logos de IBM y sus herramientas (IBM, watsonx, Granite)
├── programa/       Logo del programa o institución académica
├── logos.manifest.json  ← Fuente de verdad; los componentes leen esto
└── README.md        ← Este archivo
```

---

## Cómo añadir un logo

1. Coloca el archivo en su carpeta (`omnimorph/`, `ibm/`, `programa/`).
2. Abre `logos.manifest.json` y añade una entrada con:
   - `id`: identificador único en kebab-case (ej. `ibm-watsonx`)
   - `file`: ruta relativa desde `assets/logos/` (ej. `ibm/watsonx_logo.svg`)
   - `alt`: texto alternativo descriptivo (ej. `"IBM watsonx — plataforma de IA"`)
   - `max_width`: ancho máximo en píxeles que el componente puede usar
   - `variant`: `"light"` (para fondos oscuros) | `"dark"` (para fondos claros) | `"both"`
   - `status`: eliminar la clave `status` o poner `"OK"` cuando el archivo esté listo
3. El sistema automáticamente muestra el placeholder punteado si `status` empieza por `"PENDING"`.

---

## Logos pendientes

| ID                | Archivo esperado              | Dónde obtenerlo |
|-------------------|-------------------------------|-----------------|
| `omnimorph-main`  | `omnimorph/omnimorph-logo.svg` | Diseño propio  |
| `omnimorph-cube`  | `omnimorph/omnimorph-cube.svg` | Diseño propio  |
| `ibm-main`        | `ibm/IBM_logo.svg`             | Ver sección IBM abajo |
| `ibm-watsonx`     | `ibm/watsonx_logo.svg`         | Ver sección IBM abajo |
| `ibm-granite`     | `ibm/granite_logo.svg`         | Ver sección IBM abajo |
| `programa-main`   | `programa/programa_logo.svg`   | Institución    |

---

## Reglas de uso: logos IBM

> **Importante:** los logos de IBM son activos de marca registrada.
> Usar únicamente las versiones oficiales sin modificar.

### Dónde descargar
- **IBM Brand Center:** https://www.ibm.com/brand/experience-guides/developer/
- Solo personal/colaboradores de IBM o socios autorizados tienen acceso completo.
- Para proyectos académicos o de investigación, contactar al responsable del
  programa IBM para obtener los archivos autorizados.

### Reglas de uso (estándar IBM)
1. **No modificar** el logo: no cambiar colores, proporciones, tipografía ni elementos.
2. **Espacio libre:** mantener un espacio mínimo alrededor del logo igual a **1× la altura del logo** en todas las direcciones.
3. **Tamaño mínimo:** el logo IBM no debe aparecer con menos de **24 px** de altura.
4. **Fondos:** usar la variante `light` (logo en negro/gris oscuro) sobre fondos claros;
   la variante `dark` (logo en blanco) sobre fondos oscuros. No usar sobre fondos
   de color saturado.
5. **No superponer** texto, iconos ni otros elementos sobre el logo.
6. **No usar** el logo para implicar aval de IBM a menos que sea un proyecto
   formalmente patrocinado.

### Implementación en OMNIMORPH
- Los logos IBM aparecen únicamente en la franja "Impulsado por herramientas de IBM"
  de la portada y en el pie de página del tablero.
- Se usan con su `alt` descriptivo para accesibilidad.
- El espacio libre lo gestiona el `gap` del contenedor flex (`var(--space-6)` = 24 px).
- Cuando el logo está pendiente, se muestra un recuadro punteado `[Logo IBM]`.

---

## Reglas de uso: logo OMNIMORPH

- El cubo de Rubik es el símbolo principal; el wordmark "OMNIMORPH" es Jost 500.
- **Variante oscura:** cubo de colores sobre fondo `#111111`.
- **Variante crema:** cubo de colores sobre tarjeta `#F5F3EE` (solo en hero).
- No cambiar los colores de las caras del cubo (naranja, turquesa, morado, rosa, lima).
- Tamaño mínimo de uso: 32 px de altura.

---

## Reglas de uso: logo del programa

- [Completar con las reglas de uso del programa o institución]
- Fuente: [añadir URL o contacto]
- Licencia: [añadir]
