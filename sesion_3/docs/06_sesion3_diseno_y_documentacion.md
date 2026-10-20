# Sesión 3 — Tema 6: Diseño y Documentación de Sistemas LLM

**Capítulo 3 · Duración: ~2 horas**

---

## Objetivos de Aprendizaje

Al finalizar este tema, el estudiante podrá:
- Crear Architecture Decision Records (ADR) con el formato correcto
- Modelar sistemas usando el C4 Model (Context → Containers → Components)
- Redactar RFCs técnicas con análisis de trade-offs
- Realizar análisis de costos TCO a 24 meses
- Organizar documentación técnica usando jerarquías claras

---

## 1. Architecture Decision Records (ADR)

Los ADRs capturan **por qué** se tomó una decisión arquitectónica, no solo qué se decidió.

### Estructura de un ADR

```markdown
# ADR-NNN: Título descriptivo de la decisión

**Estado**: Propuesto | Aceptado | Rechazado | Deprecado | Reemplazado por ADR-XXX
**Fecha**: YYYY-MM-DD
**Autores**: Nombre(s)

## Contexto
Describe el problema o situación que requiere una decisión.
¿Cuáles son las fuerzas en juego? ¿Cuáles son las restricciones?

## Decisión
La decisión tomada, en voz activa: "Usaremos X porque..."

## Alternativas consideradas
| Opción | Pros | Contras |
|--------|------|---------|
| Opción A | ... | ... |
| Opción B | ... | ... |

## Consecuencias
### Positivas
- ...
### Negativas / Trade-offs
- ...
### Neutrales
- ...

## Notas
Referencias, contexto adicional, decisiones relacionadas.
```

### Ejemplo: ADR-001 — Selección de Proveedor LLM

```markdown
# ADR-001: Usar Ollama como LLM primario con fallback a Vertex AI

**Estado**: Aceptado
**Fecha**: 2024-11-15

## Contexto
El sistema requiere un LLM para el curso. Los estudiantes necesitan
ejecutar el sistema localmente sin costo, pero la aplicación de producción
necesita escalar y tener disponibilidad alta.

## Decisión
Usaremos Ollama como LLM primario para desarrollo/classroom, con
fallback automático a Vertex AI (Gemini) para producción.

## Alternativas consideradas
| Opción | Pros | Contras |
|--------|------|---------|
| Solo OpenAI | Simple, potente | Costo alto, latencia red |
| Solo Ollama | Gratis, offline | No escala en producción |
| **Ollama + Vertex** | Gratis en dev, escala en prod | Más complejidad |

## Consecuencias
### Positivas
- Sin costo para estudiantes en clases
- Circuit Breaker gestiona el failover automáticamente
### Negativas
- Dos proveedores = dos configuraciones a mantener
- Ollama requiere GPU para rendimiento óptimo
```

---

## 2. C4 Model

El C4 Model describe arquitecturas en 4 niveles de zoom:

### Nivel 1: System Context (el más alto)

```
┌─────────────────────────────────────────────────────┐
│                   System Context                     │
│                                                     │
│  [Estudiante]──►[LLM Security Platform]─►[Ollama]  │
│  [Profesor] ──►                         ─►[Vertex]  │
│                          │                          │
│                    [Audit Storage]                  │
└─────────────────────────────────────────────────────┘
```

**Pregunta que responde:** ¿Qué hace el sistema y quién lo usa?

### Nivel 2: Containers

```
┌──────────────────────────────────────────────────────┐
│                     Containers                        │
│                                                      │
│  Browser──►[React SPA]──►[FastAPI Backend]──►[Ollama]│
│               :5173         :8000           :11434   │
│                               │                      │
│                        [Audit JSONL]                 │
└──────────────────────────────────────────────────────┘
```

**Pregunta que responde:** ¿Cuáles son las partes ejecutables del sistema?

### Nivel 3: Components (dentro de un container)

```
FastAPI Backend:
  ├── /auth (AuthRouter)      ← JWT + OAuth2
  ├── /api/chat (ChatRouter)  ← WAF + CircuitBreaker + LLM
  ├── /api/health (HealthRouter)
  ├── /api/audit (AuditRouter) ← Solo admin
  └── /api/security (SecurityRouter) ← WAF scan
```

**Pregunta que responde:** ¿Cuáles son los componentes importantes dentro de cada container?

### Nivel 4: Code (opcional, generado)

Diagramas de clase, secuencia UML — generalmente auto-generados por herramientas.

---

## 3. RFC (Request for Comments)

Las RFCs técnicas proponen cambios significativos al sistema, con análisis de impacto.

### Estructura de una RFC

```markdown
# RFC-NNN: Título de la propuesta

**Estado**: Borrador | En revisión | Aceptada | Rechazada | Implementada
**Autor(es)**: Nombre(s)
**Fecha**: YYYY-MM-DD
**PR/Issue**: #XXX

## Resumen Ejecutivo
Una o dos oraciones. ¿Qué propone y por qué?

## Motivación
¿Qué problema resuelve? ¿Cuáles son los casos de uso?

## Diseño Propuesto
La solución técnica detallada.

## Trade-offs y Alternativas
¿Qué más se consideró y por qué se descartó?

## Plan de Implementación
Fases, estimados de tiempo, riesgos.

## Impacto
En rendimiento, costo, operaciones, seguridad.

## Referencias
```

---

## 4. Análisis de Costos TCO

### Componentes del TCO para un sistema LLM

```
TCO = Costos API + Infraestructura + Operaciones + Desarrollo + Oportunidad
```

| Componente | Descripción | Estimado mensual |
|-----------|-------------|-----------------|
| **API LLM** | Tokens de entrada/salida | Variable según uso |
| **Cloud Run** | Cómputo serverless | $5–50/mes |
| **Cloud Storage** | Logs, backups | $1–5/mes |
| **Networking** | Egress, CDN | $1–10/mes |
| **Monitoring** | Cloud Monitoring | $0 (free tier) |
| **DevOps** | Horas/hombre CI/CD | Fijo |

### Modelo de proyección a 24 meses

```python
# Ejemplo: 1000 requests/día, 500 tokens promedio
monthly_requests = 1000 * 30          # 30,000/mes
tokens_per_request = 500              # entrada + salida
total_tokens_monthly = monthly_requests * tokens_per_request

# Vertex AI Gemini Flash: $0.075/1M input, $0.30/1M output
input_tokens  = total_tokens_monthly * 0.6  # 60% input
output_tokens = total_tokens_monthly * 0.4  # 40% output

cost_monthly = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000
# ≈ $2.07/mes para este volumen
```

### Análisis de sensibilidad

| Escenario | Requests/día | Costo mensual | Costo anual |
|-----------|-------------|---------------|-------------|
| Mínimo (clase) | 100 | ~$0.21 | ~$2.50 |
| Típico | 1,000 | ~$2.07 | ~$24.84 |
| Crecimiento | 10,000 | ~$20.70 | ~$248.40 |
| Producción | 100,000 | ~$207.00 | ~$2,484 |

---

## 5. Estructura de Documentación Técnica

### Jerarquía recomendada

```
docs/
├── README.md                    ← Visión general del proyecto
├── arquitectura/
│   ├── adr/                     ← ADR-001, ADR-002...
│   ├── c4/                      ← Diagramas C4 (L1-L3)
│   └── rfcs/                    ← RFC-001, RFC-002...
├── api/
│   ├── openapi.yaml             ← Especificación OpenAPI
│   └── postman_collection.json  ← Colección Postman
├── operaciones/
│   ├── runbook.md               ← Procedimientos de operación
│   ├── dr_plan.md               ← Plan de Disaster Recovery
│   └── on_call.md               ← Guía para guardia nocturna
└── desarrollo/
    ├── setup.md                 ← Configuración del entorno
    ├── contributing.md          ← Guía de contribución
    └── testing.md               ← Estrategia de pruebas
```

---

## Labs de este tema

| Lab | Archivo | Tiempo |
|-----|---------|--------|
| 13 — Diseño Arquitectónico | `labs/sesion3/13_diseno_arquitectonico.py` | 35 min |
| 14 — Análisis de Costos | `labs/sesion3/14_analisis_costos_proyecto.py` | 25 min |

```bash
make lab13   # ADR, C4 Model, RFC
make lab14   # TCO y análisis de sensibilidad
```

---

## Referencias

- C4 Model: https://c4model.com/
- ADR GitHub: https://github.com/joelparkerhenderson/architecture-decision-record
- Google Cloud Pricing Calculator: https://cloud.google.com/products/calculator
- Vertex AI Pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing
- RFC Template (IETF): https://www.ietf.org/rfc/rfc2223.txt
