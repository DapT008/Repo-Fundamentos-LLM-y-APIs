# PRD: {Nombre del Producto/Feature}

**Estado**: Borrador  
**Product Owner**: {Nombre}  
**Ingeniería**: {Nombre(s)}  
**Fecha**: {YYYY-MM-DD}  
**Versión objetivo**: {X.Y}

---

## TL;DR

> Una o dos oraciones que expliquen QUÉ se construye y POR QUÉ.

{Resumen aquí}

---

## Problema

> ¿Qué dolor o necesidad existe? Sé específico con datos cuando sea posible.

### Situación actual
{Descripción del estado actual}

### Evidencia del problema
- {Evidencia 1} (ej: "85% de usuarios no completan el onboarding")
- {Evidencia 2}

### Costo de no resolver
- {Impacto en negocio/usuarios si no se resuelve}

---

## Objetivos y Métricas

### Objetivos
1. {Objetivo primario}
2. {Objetivo secundario}

### KPIs (Key Performance Indicators)

| Métrica | Línea base | Objetivo | Método de medición |
|---------|-----------|----------|-------------------|
| {KPI 1} | {Valor actual} | {Valor objetivo} | {Cómo medir} |
| {KPI 2} | {Valor actual} | {Valor objetivo} | {Cómo medir} |

### Out of scope
> Qué NO forma parte de esta versión.
- {Cosa 1} — se considerará en {versión futura}
- {Cosa 2} — no es prioritario para este ciclo

---

## Usuarios Target

| Persona | % del uso | Necesidad principal |
|---------|-----------|---------------------|
| {Persona 1} | {X%} | {Necesidad} |
| {Persona 2} | {X%} | {Necesidad} |

---

## Requerimientos Funcionales

### Must Have (P0 — sin esto no se lanza)

| ID | Historia de usuario | Criterios de aceptación |
|----|--------------------|-----------------------|
| F-01 | Como {usuario}, quiero {acción} para {beneficio} | {Criterios} |
| F-02 | ... | ... |

### Should Have (P1 — importante pero no bloqueante)

| ID | Historia de usuario | Criterios de aceptación |
|----|--------------------|-----------------------|
| F-10 | ... | ... |

### Nice to Have (P2 — si queda tiempo)

| ID | Historia de usuario | Notas |
|----|--------------------|----|
| F-20 | ... | ... |

---

## Requerimientos No Funcionales

| Categoría | Requerimiento | Métrica |
|-----------|--------------|---------|
| **Rendimiento** | Latencia P99 de respuesta | < {X} ms |
| **Disponibilidad** | Uptime mensual | ≥ {X}% |
| **Seguridad** | Autenticación requerida | JWT con scope {X} |
| **Escalabilidad** | Usuarios concurrentes | Hasta {X} |
| **Compatibilidad** | Navegadores | Chrome, Firefox, Safari (últimas 2 versiones) |

---

## Diseño (Alto nivel)

> Referencia a mockups, wireframes o descripciones de UX.
> No incluir diseño técnico aquí — eso va en el design doc.

### Flujo principal del usuario

```
{Paso 1} → {Paso 2} → {Paso 3} → {Resultado}
```

### Pantallas / Componentes afectados

- [ ] {Pantalla/componente 1}
- [ ] {Pantalla/componente 2}

---

## Consideraciones Técnicas

> Restricciones técnicas o riesgos que el equipo de producto debe conocer.

| Consideración | Impacto | Mitigación |
|---------------|---------|-----------|
| {Consideración 1} | {Alto/Medio/Bajo} | {Mitigación} |

---

## Dependencias

| Dependencia | Tipo | Estado | Propietario |
|-------------|------|--------|-------------|
| {Dependencia 1} | {Técnica/Equipo/Tercero} | {Estado} | {Nombre} |

---

## Plan de Lanzamiento

### Fases de rollout
1. **Interno** ({fecha}): Equipo de desarrollo
2. **Beta** ({fecha}): {X}% de usuarios
3. **GA** ({fecha}): 100% de usuarios

### Criterios de lanzamiento
- [ ] {Criterio 1}
- [ ] {Criterio 2}
- [ ] Documentación actualizada
- [ ] Plan de rollback definido

---

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| {Riesgo 1} | {Alta/Media/Baja} | {Alto/Medio/Bajo} | {Mitigación} |

---

## Open Questions

- [ ] {Pregunta 1} — Propietario: {Nombre}, Fecha límite: {fecha}
- [ ] {Pregunta 2} — Propietario: {Nombre}, Fecha límite: {fecha}

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambios |
|---------|-------|-------|---------|
| 1.0 | {YYYY-MM-DD} | {Nombre} | Versión inicial |

---

*Plantilla PRD v1.0 · Sesión 3 · Maestría BSG*
