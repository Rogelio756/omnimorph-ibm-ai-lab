# Fuentes y Referencias de Datos — Brasil 1–7 Alemania (2014)

Este documento detalla el origen de cada dato, estadística y métrica incluida en este repositorio para el partido de la semifinal de la Copa Mundial de la FIFA 2014 (8 de julio de 2014, Estádio Mineirão, Belo Horizonte).

---

## 1. Fuentes Principales

### A. Reporte Oficial de Partido de la FIFA (Partido 61)
- **Documento**: FIFA World Cup Brazil 2014 - Match Report: Brazil - Germany (Match 61, `miugox7gokyia8zss6k2.pdf`).
- **Referencia web**: [Reporte de Partido FIFA (PDF)](https://digitalhub.fifa.com/m/3dc76f2796b2e941/original/miugox7gokyia8zss6k2-pdf.pdf) | [FIFA.com Match Centre (Match 300186474)](https://www.fifa.com/en/match-centre/match/17/251164/255955/300186474)
- **Datos extraídos**:
  - Marcador oficial por periodos (1T: 0-5, 2T: 1-2, Final: 1-7).
  - Alineaciones oficiales titulares, suplentes, dorsales y sustituciones.
  - Minutos y autores oficiales de goles y amonestaciones.
  - Cuerpo arbitral: Marco Antonio Rodríguez (árbitro principal, MEX), Marvin Torrentera (asistente 1, MEX), Marcos Quintero (asistente 2, MEX), Mark Geiger (cuarto árbitro, USA).
  - Asistencia confirmada en el Estádio Mineirão: 58.141 espectadores.
  - Totales disciplinarios y arbitrales: 11 faltas cometidas por Brasil, 14 por Alemania; 1 tarjeta amarilla (Dante 68'); 3 fueras de juego de Brasil, 0 de Alemania.
  - Tiros de esquina: 7 para Brasil, 5 para Alemania.
  - Atajadas de arquero: 3 de Júlio César, 7 de Manuel Neuer.

### B. Reporte Técnico de la FIFA (Technical Report and Statistics - 2014 FIFA World Cup Brazil)
- **Documento**: Publicación oficial del Grupo de Estudios Técnicos (TSG) de la FIFA (`2014fwc_tsg_report_15082014web_neutral.pdf`, 284 páginas).
- **Referencia web**: [Reporte Técnico FIFA Brasil 2014 (PDF)](https://web.archive.org/web/20150614131111/http://resources.fifa.com/mm/document/footballdevelopment/technicalsupport/02/42/15/40/2014fwc_tsg_report_15082014web_neutral.pdf)
- **Sección clave**: Ficha oficial y telegrama del Partido 61 (Semifinal Brasil vs. Alemania) y perfiles estadísticos de equipo (físicos y territoriales).
- **Datos extraídos**:
  - Desglose por tiempos de posesión y volumen de tiro: posesión 47% Brasil vs 53% Alemania.
  - Conteo de tiros totales: 18 Brasil vs 14 Alemania (tiros a puerta: 8 Brasil vs 10 Alemania).
  - Distribución espacial del juego en tercios de campo.
  - Distancias recorridas y estadísticas físicas de jugadores (Kroos 11.5 km, Müller 11.8 km, Lahm 10.9 km, Oscar 10.7 km).

### C. Registro de Partido FBref (Cotejo Secundario)
- **Referencia web**: [FBref - Brazil vs Germany Match Report (2014 World Cup)](https://fbref.com/en/matches/04e9fcbd/Brazil-Germany-July-8-2014-World-Cup)
- **Datos extraídos y uso**:
  - Cotejo secundario de alineaciones, sustituciones y minutos jugados.
  - Verificación cruzada de autores de goles y asistencias oficiales.
  - *Nota metodológica*: El desglose de pases completados/intentados (Brasil 402/508, Alemania 512/594) y precisión individual (Kroos 93%, Lahm 92.6%, Khedira 90.5%) proviene de los registros oficiales de partido Opta / FIFA TSG, ya que FBref no cuenta con tablas de pases avanzados para la edición 2014.

### D. Aclaración Técnica sobre StatsBomb Open Data
- En el repositorio público abierto de StatsBomb (`statsbomb/open-data`), los torneos masculinos disponibles cubren 2018 y 2022. En esa base de datos, el archivo `7584.json` corresponde al partido Bélgica vs. Japón del Mundial 2018.
- La cobertura del Mundial Brasil 2014 corresponde a la base histórica de eventos Opta / StatsBomb comercial. Los valores de goles esperados ($xG$) utilizados aquí (Müller 0.35, Kroos 0.38 y 0.88, total partido Brasil ~1.25 vs Alemania ~3.75) provienen de los modelos calibrados de $xG$ post-partido comúnmente utilizados en analítica de fútbol (Opta / StatsBomb historical shot models).

---

## 2. Asignación de Métricas por Archivo

| Archivo | Métrica o Bloque | Fuente Principal |
| :--- | :--- | :--- |
| `01_primer_gol_muller/gol_muller_min11.json` | Minuto, reloj y tipo de jugada (10:33, córner) | Reporte oficial FIFA |
| `01_primer_gol_muller/gol_muller_min11.json` | Coordenadas en campo ($12000 \times 7000\text{ cm}$) | Homologación espacial OMNIMORPH |
| `01_primer_gol_muller/gol_muller_min11.json` | Radio de separación de marca ($3.4\text{ m}$) y $xG$ ($0.35$) | Videoanálisis táctico y modelo $xG$ Opta/StatsBomb |
| `01_primer_gol_muller/gol_muller_min11.json` | Estadísticas acumuladas al minuto 11 | Registro de eventos oficiales minuto a minuto |
| `02_partido_completo/contexto_partido.json` | Datos de sede, clima, alineaciones y árbitros | FIFA Match 61 Official Match Report |
| `02_partido_completo/estadisticas_partido.*` | Posesión, tiros, córners, faltas, tarjetas, atajadas | Reporte FIFA y Reporte Técnico TSG |
| `02_partido_completo/estadisticas_partido.*` | Pases intentados/completados y distancias | Reporte Técnico TSG / Registro oficial Opta |
| `02_partido_completo/cronologia_goles.*` | Minuto exacto, asistencias, pie de remate y $xG$ | Reporte FIFA + feed de eventos Opta |
