# Sesión 37 — Estado del Presupuesto Bob Coins

**Fecha:** 2026-11-23
**Agente:** IBM Bob IDE (modo Ask / Agent)
**Rama:** feat-costa-rica

---

## Contexto

Revisión del consumo de Bobcoins para planificar el trabajo restante del proyecto Omnimorph antes del reseteo mensual del 2 de diciembre de 2026.

---

## Estado de cuentas

### Cuenta agotada (anterior)
| Campo | Valor |
|---|---|
| Presupuesto | ~40 Bobcoins |
| Estado | **Agotada** |

### Cuenta activa
| Campo | Valor |
|---|---|
| Cuenta | Cuenta del equipo (Pro Plus) |
| Equipo | default (Región: us-east) |
| Plan | **Pro Plus** |
| Presupuesto mensual | 180.00 Bobcoins |
| Uso acumulado | 155.90 Bobcoins (**87% consumido**) |
| **Saldo restante** | **~24.10 Bobcoins** |
| Reseteo | **2 de diciembre de 2026** |
| Add-ons | Ninguno |

### Consumo total del proyecto
| Cuenta | Bobcoins usados |
|---|---|
| Anterior (agotada) | ~40 |
| Activa (al 23/11) | 155.90 |
| **Total** | **~196** |

---

## Riesgo operativo

Con ~24 Bobcoins disponibles hasta el 2 de diciembre, el margen para operaciones costosas es limitado.

### Operaciones de alto consumo a evitar hasta el reseteo
- Lecturas masivas de archivos grandes (parquet, JSON pesados)
- Pipelines completos (`run_pipeline.py --use-real`)
- Sesiones de debugging con muchos ciclos de edición
- Re-lectura innecesaria de archivos ya conocidos

### Recomendaciones para maximizar el saldo
1. **Crear nuevo contexto (`/new`)** al iniciar cada tarea diferente — evita re-enviar contexto acumulado.
2. Usar `context_focus_query` en todas las lecturas de archivos para comprimir resultados.
3. Priorizar ediciones quirúrgicas (`apply_diff`) sobre reescrituras completas (`write_file`).
4. Consultar el gauge (esquina superior derecha del panel) antes de operaciones largas.
5. Posponer tareas pesadas al 2 de diciembre cuando se renueve el presupuesto.

---

## Dónde revisar el saldo

| Método | Acceso |
|---|---|
| Gauge en panel | Hover sobre el ícono superior derecho del panel Bob |
| Settings → General | Información detallada de cuenta y estadísticas de uso |
| Bob Admin Portal | [bob.ibm.com/admin](https://bob.ibm.com/admin) → pestaña Subscription |
| Bobalytics | Desde Settings o desde el portal admin |

---

## Notas

- Esta sesión no generó cambios de código en el proyecto.
- El estado de Git al momento de la sesión: rama `feat-costa-rica`, sin cambios de código pendientes (sí había documentos sin subir, como los resúmenes ejecutivos y esta sesión).
- La sesión 36 (construcción completa de la página Transmisión) fue la última sesión productiva antes de este registro de presupuesto.
