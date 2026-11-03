# 📐 Fundamentos Matemáticos y Físicos — Motor Omnimorph (`P1`, `P2`, `P3` y Métricas Tácticas)

Este documento concentra las ecuaciones matemáticas, modelos cinemáticos y criterios de validación de la rama **`investigacion`**, diseñados junto con el equipo de Matemáticas (**Giselle — Actuaría** y **Caroline — Ingeniería Física**).

---

## 1. Sistema de Referencia y Entradas Congeladas

El pipeline de visión por computadora entrega dos tablas sobre clips de $30\text{ s}$ a $25\text{ fps}$ ($750\text{ cuadros}$):
* **Dimensiones oficiales de cancha:** Largo $L = 12000\text{ cm}$ ($120\text{ m}$), Ancho $W = 7000\text{ cm}$ ($70\text{ m}$).
* **Origen de coordenadas:**
  * $x \in [0, 12000]\text{ cm}$ ($0 =$ línea de meta Argentina, $12000 =$ línea de meta Francia).
  * $y \in [0, 7000]\text{ cm}$ ($0 =$ banda sur, $7000 =$ banda norte).
* **Paso temporal nominal:** $\Delta t = \frac{1}{\text{fps}} = 0.04\text{ s}$.

---

## 2. Fase 1: Reconciliación Estadística de Equipo y Separación de Fuentes

### Problema
1. La tabla `objects.parquet` ($35,870$ filas) contiene tres flujos: detecciones brutas sin ID (`source == "det"`), objetos rastreados (`source == "track"`) y el balón (`source == "ball"`).
2. El clasificador visual SigLIP + UMAP + KMeans (`A5`) opera cuadro a cuadro sin memoria, provocando parpadeos en la etiqueta `team` por sombras o giros del jugador.

### Formulación
1. **Filtrado de conjuntos disjuntos:**
   $$\mathcal{T} = \{r \in \text{objects} \mid r.\text{source} = \text{"track"}\}, \quad \mathcal{B} = \{r \in \text{objects} \mid r.\text{source} = \text{"ball"}\}$$
2. **Estimador por Moda (Voto de Mayoría) por `track_id` ($k$):**
   $$\hat{c}(k) = \operatorname*{arg\,max}_{c \in \{0, 1\}} \sum_{t \in \mathcal{T}_k} \mathbb{I}(\text{team}_{k,t} = c)$$
3. **Heurística Espacial para Porteros (`class_id == 1`):**
   $$\hat{c}_{\text{GK}}(k) = \begin{cases} 0 \text{ (ARG)} & \text{si } \frac{1}{|\mathcal{T}_k|}\sum_{t} x_{k,t} < 6000\text{ cm} \\ 1 \text{ (FRA)} & \text{si } \frac{1}{|\mathcal{T}_k|}\sum_{t} x_{k,t} \ge 6000\text{ cm} \end{cases}$$

---

## 3. Fase 2 (`P1`): Estabilización Geométrica en el Espacio de Homografías Normalizadas

### Problema
El Agente 6 (`ViewTransformer`) estima $H_t \in \mathbb{R}^{3\times 3}$ en cada cuadro usando únicamente los puntos clave visibles ($N_t = \text{n\_kp\_visible}_t \in [0, 32]$). Cuando un punto clave entra o sale del encuadre de la cámara, el estimador RANSAC salta abruptamente y las posiciones proyectadas en cancha sufren discontinuidades de varios metros en $0.04\text{ s}$.

### Formulación
1. **Fijación de escala proyectiva ($8\text{ DOF}$):**
   Toda matriz de homografía es invariante por multiplicación escalar ($\lambda H_t \sim H_t$). Antes de aplicar cualquier combinación convexa temporal, se fija la carta afín dividiendo por el elemento $H_t[2,2]$:
   $$\tilde{H}_t = \frac{H_t}{H_t[2,2]}, \quad \text{con } \tilde{H}_t[2,2] = 1$$
2. **Factor de Confianza de Puntos Clave Visibles:**
   Sea $\mathcal{V}_t = \{i \in \{1,\dots,32\} \mid \text{kp\_conf}_{t,i} > 0.5\}$ el conjunto de marcadores visibles en el cuadro $t$. Definimos la confianza media efectiva:
   $$\bar{\gamma}_t = \frac{1}{|\mathcal{V}_t|} \sum_{i \in \mathcal{V}_t} \text{kp\_conf}_{t,i}$$
3. **Filtro Exponencial Adaptativo (EMA con retención de inercia):**
   El peso de innovación $\alpha_t$ pondera cuántos puntos clave sostienen la geometría en el instante $t$:
   $$\alpha_t = \begin{cases} 0.01 & \text{si } N_t < 4 \text{ o } \neg\text{homography\_valid}_t \\ \operatorname{clip}\!\left(\frac{N_t}{24} \cdot \bar{\gamma}_t \cdot 0.5, \, 0.05, \, 0.60\right) & \text{en otro caso} \end{cases}$$
   La matriz estabilizada se actualiza recursivamente como:
   $$\hat{H}_t = \alpha_t \tilde{H}_t + (1 - \alpha_t)\hat{H}_{t-1}$$
4. **Proyección Directa del Punto de Contacto con el Césped ($z = 0$):**
   Para cada caja $[x_1, y_1, x_2, y_2]$, el punto de apoyo de los pies en coordenadas homogéneas de imagen es $\mathbf{p}_{\text{img}} = \left[\frac{x_1+x_2}{2}, \, y_2, \, 1\right]^T$:
   $$\begin{bmatrix} x' \\ y' \\ w' \end{bmatrix} = \hat{H}_t \mathbf{p}_{\text{img}}, \quad x_{\text{smooth}} = \operatorname{clip}\!\left(\frac{x'}{w'}, 0, 12000\right), \quad y_{\text{smooth}} = \operatorname{clip}\!\left(\frac{y'}{w'}, 0, 7000\right)$$

---

## 4. Fase 3 (`P3`): Re-identificación y Unificación de Fragmentos (*Track Stitching*)

### Problema
ByteTrack (`A4`) asigna $39$ `track_id` distintos para $\approx 25$ personas físicas durante los $30\text{ s}$ debido a oclusiones entre jugadores.

### Formulación (Asignación Óptima Bipartita + Clausura Transitiva)
1. **Extrapolación Cinemática de Frontera:**
   Para cada fragmento $i$ que termina en el cuadro $t_{\text{end}}^{(i)}$ con posición $\mathbf{x}_{\text{end}}^{(i)}$ y velocidad terminal $\mathbf{v}_{\text{end}}^{(i)}$, y cada fragmento candidato $j$ que inicia en $t_{\text{start}}^{(j)}$ con posición inicial $\mathbf{x}_{\text{start}}^{(j)}$, sea $\delta t_{ij} = (t_{\text{start}}^{(j)} - t_{\text{end}}^{(i)})\Delta t$.
   La posición predicha de $i$ al momento en que nace $j$ es:
   $$\hat{\mathbf{x}}_{i \to j} = \mathbf{x}_{\text{end}}^{(i)} + \mathbf{v}_{\text{end}}^{(i)} \delta t_{ij}$$
2. **Matriz de Costos con Restricciones Duras ($C \in \mathbb{R}^{M\times M}$):**
   $$C_{ij} = \begin{cases} \|\hat{\mathbf{x}}_{i \to j} - \mathbf{x}_{\text{start}}^{(j)}\|_2 + \lambda \delta t_{ij} & \text{si } 0 < \delta t_{ij} \le 3.0\text{ s}, \; \hat{c}(i) = \hat{c}(j), \; \|\hat{\mathbf{x}}_{i \to j} - \mathbf{x}_{\text{start}}^{(j)}\|_2 \le 500\text{ cm} \\ \infty & \text{en otro caso} \end{cases}$$
3. **Asignación Húngara y Grafo de Uniones:**
   Se minimiza $\sum_{i,j} C_{ij} X_{ij}$ mediante el Algoritmo Húngaro (`scipy.optimize.linear_sum_assignment`) y se aplica búsqueda de raíz (`find_root`) para colapsar cadenas transitivas $k_3 \to k_2 \to k_1$.

---

## 5. Fase 4 (`P2`): Filtrado Cinemático Savitzky-Golay y Cotas Biodinámicas

### Problema
La diferenciación numérica directa sobre coordenadas ruidosas amplifica el ruido de alta frecuencia por un factor de $\frac{1}{\Delta t} = 25\text{ Hz}$, generando velocidades imposibles (ej. `track_id=19` con $1382\text{ cm/s} = 49.7\text{ km/h}$ en el cuadro 300).

### Formulación
1. **Filtro Mediano contra Impulsos (Ventana $W_m = 5$):**
   $$\tilde{x}_t = \operatorname{median}\{x_{t-2}, x_{t-1}, x_t, x_{t+1}, x_{t+2}\}$$
2. **Ajuste Polinomial Local de Savitzky-Golay ($W_{sg} = 11\text{ cuadros} = 0.44\text{ s}$, grado $p = 2$):**
   En cada entorno local se ajusta por mínimos cuadrados un polinomio cuadrático $P(u) = a_0 + a_1 u + a_2 u^2$.
   * Posición suavizada en $u=0$: $\hat{x}_t = a_0$
   * **Derivada analítica exacta en $u=0$:** $v_{x,t} = \frac{a_1}{\Delta t}$ (con $\Delta t = 0.04\text{ s}$).
3. **Acotamiento Fisiológico Vectorial:**
   Con $v_{\max} = 950\text{ cm/s}$ ($9.5\text{ m/s} = 34.2\text{ km/h}$) y $a_{\max} = 500\text{ cm/s}^2$ ($5.0\text{ m/s}^2$):
   $$\mathbf{v}_t \leftarrow \mathbf{v}_t \cdot \min\!\left(1, \, \frac{v_{\max}}{\|\mathbf{v}_t\|_2 + \epsilon}\right), \quad \mathbf{a}_t \leftarrow \mathbf{a}_t \cdot \min\!\left(1, \, \frac{a_{\max}}{\|\mathbf{a}_t\|_2 + \epsilon}\right)$$

---

## 6. Fase 5: Métricas Colectivas en Ventanas Tácticas ($W = 4.0\text{ s} = 100\text{ cuadros}$)

Para cada ventana $W_m$ y cada equipo $E \in \{\text{ARG}, \text{FRA}\}$:
1. **Altura Media de Bloque (respecto al mediocampo $x=6000\text{ cm}$, en metros):**
   $$H_{\text{bloque}}(E) = \frac{1}{100}\left(\bar{x}_E - 6000\right)$$
2. **Compactación del Bloque (Largo $\times$ Ancho en metros):**
   $$L_E = \frac{1}{|W_m|}\sum_{t \in W_m} \frac{\max_{i \in E_t} x_{i,t} - \min_{i \in E_t} x_{i,t}}{100}, \quad A_E = \frac{1}{|W_m|}\sum_{t \in W_m} \frac{\max_{i \in E_t} y_{i,t} - \min_{i \in E_t} y_{i,t}}{100}$$
3. **Índice de Presión Instantánea Cuadro a Cuadro:**
   En cada cuadro $t$, sea $k^*(t) = \arg\min_{k} \|\mathbf{x}_{k,t} - \mathbf{x}_{\text{ball},t}\|_2$. Si $\|\mathbf{x}_{k^*,t} - \mathbf{x}_{\text{ball},t}\|_2 \le 3.5\text{ m}$, se contabiliza el número de rivales $j$ tales que $\|\mathbf{x}_{j,t} - \mathbf{x}_{k^*,t}\|_2 \le 2.5\text{ m}$.
