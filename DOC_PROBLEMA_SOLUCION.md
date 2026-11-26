# Omnimorph — Problema y solución

**IBM SkillsBuild AI Experiential Learning Lab · Entregable 2**
**Fecha:** 2026-11-26 · **Prototipo:** <https://github.com/Rogelio756/omnimorph-ibm-ai-lab> (rama `feat-costa-rica`; se ejecuta en local, ver «Cómo probarlo»)

---

## 1. El problema

Un club pequeño, una academia o un equipo universitario graba sus partidos, pero casi nunca tiene un analista que convierta ese video en conclusiones. El cuerpo técnico revisa horas de grabación a ojo y llega al vestidor con impresiones, no con datos. Las herramientas profesionales de análisis táctico existen, pero están pensadas para clubes con presupuesto y personal especializado, y entregan tablas en inglés que hay que saber leer.

**El problema, centrado en el usuario:**

> Un cuerpo técnico sin analista necesita entender, en español y en pocos minutos, dónde estuvo su equipo y dónde estuvo el rival en cada momento del partido, y poder comprobarlo en el mismo video, sin depender de la palabra de una herramienta que no puede verificar.

La segunda mitad importa tanto como la primera: si la herramienta dice algo que el video contradice, el técnico deja de confiar en ella. Por eso Omnimorph prefiere decir menos, pero solo lo que se puede comprobar.

## 2. Usuario objetivo

| | |
|---|---|
| **Usuario principal** | Cuerpo técnico de un equipo sin analista: director técnico, asistente o preparador de un club pequeño, una academia o un equipo universitario |
| **Qué tiene** | Video del partido (hoy, de transmisión de TV) y poco tiempo entre partidos |
| **Qué necesita** | Saber qué equipo ocupó más campo, a qué distancia de su portería jugó cada uno y cómo cambió eso a lo largo del clip, explicado en español |
| **Qué le genera desconfianza** | Cifras que no puede verificar, términos en inglés y conclusiones que el video no respalda |
| **Usos posteriores** (no cubiertos todavía) | Jugadores amateur, visorías y aficionados que quieren una experiencia tipo transmisión |

## 3. La solución propuesta

**Omnimorph convierte un clip de partido en una explicación táctica en español que un cuerpo técnico puede entender sin ayuda y comprobar en el mismo video.**

El flujo tiene cuatro pasos:

1. **Ver:** visión por computadora ubica a cada jugador, al árbitro y al balón en cada cuadro del video, y los pasa a un radar de la cancha.
2. **Medir:** un motor de análisis divide el clip en tramos de 4.5 segundos y calcula, para **los dos equipos**, a qué distancia de su portería juegan, qué porcentaje de sus jugadores está en campo rival, el largo y el ancho que ocupan, y quién tiene el territorio.
3. **Explicar:** IBM Granite (en watsonx.ai) redacta una frase corta por tramo y responde preguntas en un chat. Un monitor de gobernanza revisa cada frase contra los datos del tramo: si contradice los números, se descarta.
4. **Comprobar:** la web sincroniza video, radar, métricas y crónica en un mismo reloj, para que el técnico vea en el video lo que dice el texto.

## 4. Funcionalidades clave del MVP

| Función | Qué hace | Estado |
|---|---|---|
| **MATEO (tablero táctico)** | Video, radar, métricas de ambos equipos y crónica en un mismo reloj. Cambia de tramo y todo se actualiza | Funciona |
| **Radar** | Posición aproximada de cada jugador en la cancha. Su error está medido y publicado: mediana 2.4 m, 90 % de los casos hasta 3.2 m | Funciona |
| **Crónica y voz de MATEO** | Una frase por tramo, narrada en español y sincronizada con el video. Las 8 frases del clip coinciden con los datos | Funciona |
| **Chat sobre el partido** | Responde goles, autores, minutos, tarjetas y estadísticas con los datos, sin inventar. Lo que no cubre una regla lo responde IBM Granite, con verificación de cifras | Funciona (62 de 62 pruebas) |
| **Partido** | Ficha, alineaciones, estadísticas comparadas, goles y eventos del encuentro | Funciona |
| **Transmisión** | Vista tipo TV con la voz de MATEO, radar y alineaciones | Funciona; el radar de esta vista está en mejora |
| **Método** | Explica de dónde sale cada dato, qué se verifica y cuáles son los límites | Funciona |
| **9 monitores de calidad** | Revisan cada etapa: dataset, separación de equipos, calibración, unión de rastros, cinemática, tramos, integridad, narración y sincronía de la voz | 9 de 9 en PASS en la última corrida |

**Caso de demostración:** clip de transmisión de 36 segundos de **Costa Rica 4–0 San Cristóbal y Nieves** (eliminatorias de Concacaf al Mundial 2026).

## 5. Qué no promete hoy

Omnimorph es honesto sobre sus límites, y eso es parte de la solución:

- **No es en vivo:** analiza un clip ya grabado. No se ha probado con video de celular.
- **No mide velocidad, distancia, sprints, posesión, xG ni PPDA:** la calibración de cámara todavía no da cifras confiables para eso.
- **No identifica jugadores de forma automática:** 10 de 46 jugadores se identificaron a mano.
- **Una persona aún no ha validado el radar punto por punto:** el error publicado se mide con puntos de la cancha que detecta el modelo.

## 6. Cómo probarlo

Prototipo: <https://github.com/Rogelio756/omnimorph-ibm-ai-lab> (rama `feat-costa-rica`). Requiere Python 3.12 y Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe dashboard/serve.py
```

Abrir <http://localhost:8600>. Sin credenciales de watsonx.ai todo funciona salvo las respuestas libres del chat. Los videos no están en Git por reglas del proyecto; se piden al equipo y se copian en `dashboard/media/`.

## 7. Siguientes pasos

1. Probar con video grabado con celular, con permiso de los jugadores, para medir qué falla fuera de la transmisión de TV.
2. Mejorar la calibración y la lectura de dorsales antes de ofrecer métricas por jugador.
3. Piloto con un cuerpo técnico real y al menos 5 personas que digan si entendieron la explicación sin ayuda.
