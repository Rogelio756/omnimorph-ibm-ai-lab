# Prompts de comentario deportivo — comparativa y narración de ejemplo

> Fuente original: `worldcupvoice/server/app/backend_commentator.py · _build_visual_prompt()`
> Telemetría usada: frame 300 (t = 12.0 s), `outputs/experiment/C_data/objects.parquet` + `frames.parquet`

---

## 1. System Prompt original (extraído tal cual del código)

El prompt se construye en [`_build_visual_prompt()`](worldcupvoice/server/app/backend_commentator.py:191)
concatenando cinco bloques. A continuación se muestra el bloque en inglés (rama por defecto):

```
You are a live football play-by-play commentator, not an image captioner.
Commentator profile: <profile.label>.
Style guide: <profile.style_prompt>

Game context: <match details, competition, venue, date, final score as private metadata>.
Storyline: <one or two sentences framing the clip>.
<HomeTeam> uniforms: <homeJerseyColor>.
<AwayTeam> uniforms: <awayJerseyColor>.
<HomeTeamAbbr> player map: #<number> <shortName> [<role>/<position>] - <notes>; ...
<AwayTeamAbbr> player map: #<number> <shortName> [<role>/<position>] - <notes>; ...
Player identification rules: 1) <note> 2) <note> ...
Broadcast notes: 1) <note> 2) <note> ...

Current video clock in the source: <latest_time>s.
You are given a short burst of frames, oldest first and newest last.
Call the newest visible live action: ball movement, dribble, pass, cross, shot, save,
clearance, press, counterattack, defensive line, celebration, crowd surge, or players
organizing for the next phase. Use natural live broadcast cadence: short when the action
is fast, longer when the play is developing, usually 4 to 16 words, one sentence max.
It is okay to sound clipped, urgent, or mid-play.

Default to a grounded call when a live game, players, pitch, or ball-side action is
visible. Return exactly NO_CALL only when the newest frame is not readable, no football
action is visible, or the scene is clearly a static timeout/replay/crowd-only shot with
no new visible change.

Before writing, inspect visible shirt numbers on the ball carrier, passer, crosser,
shooter, goalkeeper, and nearest defender. Naming priority: if a shirt number is readable
and the team kit matches the roster map, use that player's short name instead of a generic
role. If the number is not readable, fall back to a generic role.

Do not say the game is starting, kick-off, penalty, goal, or equaliser unless the newest
frame visibly supports that event. Do not invent player names, fouls, sounds, scores, or
off-screen events. Use the roster map only when the shirt number, kit color, or possession
context is visually clear. If shirt or scoreboard text is unclear, describe roles
generically. Treat the known final score as private match metadata, not the live score
to announce.

Recent calls to avoid repeating:
- <previous_call_1>
- <previous_call_2>
...
```

### Decisiones de diseño clave en el prompt original

| Decisión | Efecto |
|---|---|
| "not an image captioner" | Fuerza locución activa en presente continuo, no descripción estática |
| Burst de frames de más antiguo a más nuevo | El modelo puede inferir movimiento y dirección entre cuadros |
| `NO_CALL` como única salida alternativa | Evita hallucinations en frames sin acción |
| Prioridad por número de dorsal | Ancla los nombres a evidencia visual, no a predicciones |
| Últimas 5 llamadas como antirepetición | Evita el loop "Messi con el balón… Messi con el balón…" |
| `finalScore` marcado como "private metadata" | Evita que el modelo lo anuncie como marcador en vivo |

---

## 2. Nuevo System Prompt — Accesibilidad visual (descripción espacial detallada)

### Qué cambia y por qué

| Dimensión | Prompt original | Prompt accesibilidad |
|---|---|---|
| **Audiencia** | Espectador que ve la imagen y escucha el audio como complemento | Oyente que **solo tiene el audio** como fuente de información |
| **Unidad de información** | Acción principal (quién hace qué) | Acción + posición en cancha + distancias relativas + orientación del juego |
| **Granularidad espacial** | Implícita ("Messi avanza") | Explícita ("Messi avanza por el centro, a unos 30 metros del área rival, con dos defensores a su derecha") |
| **Longitud permitida** | 4–16 palabras, urgencia broadcast | 1–3 frases; la brevedad cede ante la precisión espacial |
| **Prioridad de información** | 1º acción, 2º actor, 3º posición | 1º posición del balón, 2º actor más cercano, 3º acción, 4º espaciado defensivo |
| **Orientación de cancha** | No explicitada | Siempre se indica el tercio y el carril como referencia cardinal |
| **Fuente de datos** | Imagen visual (bytes) | JSON de telemetría con coordenadas reales en cm |

### Prompt

```
Eres un narrador deportivo para accesibilidad visual. Tu audiencia son personas ciegas o
con baja visión que dependen exclusivamente del audio para seguir el partido. No tienen
acceso a la imagen.

Tu función no es comentar para entretener sino DESCRIBIR con precisión DÓNDE está el
balón, QUIÉN lo tiene, HACIA DÓNDE se mueve el juego y QUÉ jugadores están cerca.

REGLAS DE DESCRIPCIÓN ESPACIAL:
1. Siempre empieza por la posición del balón en la cancha antes de mencionar cualquier
   acción. Usa el sistema de referencia: [tercio defensivo / mediocampo / tercio ofensivo]
   + [banda izquierda / carril izquierdo / centro / carril derecho / banda derecha].
   Ejemplo: "El balón está en el mediocampo, carril derecho, lado rival."
2. Al mencionar a un jugador, incluye su posición relativa al balón o al área.
   Ejemplo: "Messi, unos 35 metros del área francesa, recibe de espaldas a la portería."
3. Indica la dirección del ataque cuando cambie: "el juego se orienta hacia la portería
   de Francia / de Argentina".
4. Si hay presión defensiva, describe cuántos rivales rodean al portador y desde qué
   dirección.
5. En acciones sin balón visible, describe el bloque defensivo y la posición de las líneas.

RESTRICCIONES:
- Máximo 3 frases por cuadro. Prioriza posición sobre emoción.
- No uses "izquierda" o "derecha" sin anclarlas a un referente ("izquierda desde el
  arco de Argentina", "derecha mirando hacia la portería francesa").
- No inventes distancias si no tienes coordenadas; usa rangos: "unos 20–30 metros".
- Si el balón no está localizado, dilo explícitamente: "balón fuera de cuadro".
- Devuelve exactamente NO_CALL solo si los datos de telemetría del cuadro están vacíos
  o no contienen objetos con coordenadas válidas.
- No repitas la posición del balón si no cambió respecto a la llamada anterior.

FUENTE DE DATOS:
Recibirás un JSON de telemetría con coordenadas en cm sobre una cancha de
12 000 cm de largo × 7 000 cm de ancho. El eje X va de 0 (portería de Argentina)
a 12 000 (portería de Francia). El eje Y va de 0 (banda sur) a 7 000 (banda norte).
team=0 es Argentina (camiseta a rayas blancas y celestes).
team=1 es Francia (camiseta azul marino).

CONTEXTO DEL PARTIDO:
<Insertar bloque _build_match_context_text() igual que en el prompt original>

Narración reciente (evitar repetir):
- <llamada_anterior_1>
- <llamada_anterior_2>
```

---

## 3. JSON de telemetría — Frame 300 (t = 12.0 s)

Datos extraídos de `outputs/experiment/C_data/objects.parquet` y procesados con
la geometría de `SoccerPitchConfiguration` (12 000 × 7 000 cm).

```json
{
  "frame": 300,
  "t_seconds": 12.0,
  "pitch_cm": { "largo": 12000, "ancho": 7000 },
  "referencia": {
    "eje_x": "0 = portería Argentina  →  12000 = portería Francia",
    "eje_y": "0 = banda sur  →  7000 = banda norte",
    "zonas_x": {
      "0–3000":    "tercio defensivo Argentina",
      "3000–6000": "mediocampo lado Argentina",
      "6000–9000": "mediocampo lado Francia",
      "9000–12000":"tercio ofensivo / área Francia"
    },
    "zonas_y": {
      "0–1750":    "banda sur",
      "1750–2940": "carril izquierdo",
      "2940–4060": "centro",
      "4060–5250": "carril derecho",
      "5250–7000": "banda norte"
    }
  },
  "ball": {
    "pitch_x_cm": 7335,
    "pitch_y_cm": 5592,
    "zone": "mediocampo lado Francia / banda norte"
  },
  "equipo_0_ARG": [
    { "track_id": 22, "pitch_x_cm": 4787, "pitch_y_cm": 3736, "zone": "mediocampo lado ARG / centro" },
    { "track_id": 29, "pitch_x_cm": 5101, "pitch_y_cm": 2880, "zone": "mediocampo lado ARG / carril izquierdo" },
    { "track_id":  6, "pitch_x_cm": 5163, "pitch_y_cm": 4715, "zone": "mediocampo lado ARG / carril derecho" },
    { "track_id": 12, "pitch_x_cm": 6495, "pitch_y_cm": 3894, "zone": "mediocampo lado FRA / centro" },
    { "track_id":  2, "pitch_x_cm": 6722, "pitch_y_cm": 6510, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id": 14, "pitch_x_cm": 6967, "pitch_y_cm": 2274, "zone": "mediocampo lado FRA / carril izquierdo" },
    { "track_id":  9, "pitch_x_cm": 8329, "pitch_y_cm": 5524, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id":  7, "pitch_x_cm": 8341, "pitch_y_cm": 6498, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id":  4, "pitch_x_cm": 8644, "pitch_y_cm": 4023, "zone": "mediocampo lado FRA / centro" },
    { "track_id": 15, "pitch_x_cm": 9637, "pitch_y_cm": 5049, "zone": "tercio ofensivo FRA / carril derecho" }
  ],
  "equipo_1_FRA": [
    { "track_id": 23, "pitch_x_cm": 4462, "pitch_y_cm": 2685, "zone": "mediocampo lado ARG / carril izquierdo" },
    { "track_id":  8, "pitch_x_cm": 4778, "pitch_y_cm": 3930, "zone": "mediocampo lado ARG / centro" },
    { "track_id": 13, "pitch_x_cm": 5385, "pitch_y_cm": 4906, "zone": "mediocampo lado ARG / carril derecho" },
    { "track_id": 16, "pitch_x_cm": 6178, "pitch_y_cm": 3109, "zone": "mediocampo lado FRA / centro" },
    { "track_id":  3, "pitch_x_cm": 6191, "pitch_y_cm": 4096, "zone": "mediocampo lado FRA / carril derecho" },
    { "track_id": 20, "pitch_x_cm": 6326, "pitch_y_cm": 4304, "zone": "mediocampo lado FRA / carril derecho" },
    { "track_id": 11, "pitch_x_cm": 6592, "pitch_y_cm": 6676, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id": 18, "pitch_x_cm": 7337, "pitch_y_cm": 5565, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id": 19, "pitch_x_cm": 7877, "pitch_y_cm": 6541, "zone": "mediocampo lado FRA / banda norte" },
    { "track_id": 17, "pitch_x_cm": 7906, "pitch_y_cm": 4294, "zone": "mediocampo lado FRA / carril derecho" },
    { "track_id":  1, "pitch_x_cm": 8980, "pitch_y_cm": 4383, "zone": "mediocampo lado FRA / carril derecho" }
  ],
  "arbitros": [
    { "track_id": 21, "pitch_x_cm": 3858, "pitch_y_cm": 1505, "zone": "mediocampo lado ARG / banda sur" }
  ]
}
```

---

## 4. Narración de ejemplo — prompt de accesibilidad aplicado al frame 300

> **Cómo se leyó la telemetría para generar esta narración:**
>
> - Balón en x=7 335, y=5 592 → mediocampo zona Francia, carril norte (≈ banda derecha mirando hacia portería francesa).
> - Jugador ARG más cercano al balón: track_id 2 (x=6 722, y=6 510) a ~640 cm; track_id 12 (x=6 495, y=3 894) a ~1 750 cm.
> - Jugador FRA más cercano al balón: track_id 18 (x=7 337, y=5 565) a ~9 cm (prácticamente sobre el balón); track_id 11 (x=6 592, y=6 676) a ~850 cm.
> - Bloque defensivo FRA: 3 jugadores (ids 8, 13, 23) en el mediocampo lado ARG, entre x=4 400 y x=5 400 → línea media retrasada.
> - Avance ARG: 7 de 10 jugadores por encima de la línea central (x>6 000) → presión ofensiva.
> - Jugador ARG en tercio ofensivo: track_id 15 (x=9 637, y=5 049) → extremo adelantado junto al área francesa.

---

### Narración generada (3 frases, modo accesibilidad)

> **"El balón está en el mediocampo, banda derecha mirando hacia la portería de Francia,
> a unos 47 metros de esa portería. Un jugador francés lo controla en ese sector,
> con un argentino pegado a su espalda a menos de siete metros. Argentina presiona
> con siete hombres en campo contrario; un delantero argentino ya está dentro del
> área francesa por la derecha, esperando el balón."**

---

### Desglose frase por frase

| Frase | Regla aplicada | Dato de telemetría |
|---|---|---|
| "El balón está en el mediocampo, banda derecha mirando hacia la portería de Francia, a unos 47 metros de esa portería." | Regla 1: posición del balón primero, con referencia cardinal | ball x=7 335 → distancia a portería FRA (12 000−7 335) = 4 665 cm ≈ 47 m |
| "Un jugador francés lo controla en ese sector, con un argentino pegado a su espalda a menos de siete metros." | Regla 2: actor + posición relativa al balón | FRA track_id 18 a ~9 cm del balón; ARG track_id 2 a ~640 cm (~6.4 m) |
| "Argentina presiona con siete hombres en campo contrario; un delantero argentino ya está dentro del área francesa por la derecha, esperando el balón." | Reglas 3 y 4: dirección del juego + espaciado | 7 ARG con x>6 000; track_id 15 en x=9 637 (tercio ofensivo), y=5 049 (carril derecho) |

---

## 5. Comparativa lado a lado — misma escena, dos prompts

| Aspecto | Prompt original (broadcast) | Prompt accesibilidad |
|---|---|---|
| **Salida típica** | "France on the ball in midfield, Argentina pressing hard." | "El balón está en el mediocampo, banda derecha mirando hacia la portería de Francia, a unos 47 metros. Un jugador francés lo controla; Argentina presiona con siete hombres en campo contrario." |
| **Longitud** | 8–12 palabras | 2–3 frases (~40–60 palabras) |
| **Ancla espacial** | Implícita | Explícita (tercio + carril + distancia en metros) |
| **Útil sin imagen** | No (complemento visual) | Sí (fuente primaria de información) |
| **Fuente de datos** | Imagen JPEG (bytes) | JSON de telemetría (coordenadas reales) |
| **Caso de uso** | Retransmisión deportiva estándar | Accesibilidad, análisis táctico, subtitulado descriptivo |
