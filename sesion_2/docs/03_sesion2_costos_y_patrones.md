# Sesión 2 — Temas 3 y 4: Costos y Patrones de Escalabilidad

## Guía del instructor

**Duración sugerida:** 3 horas (90 min por tema + breaks)  
**Nivel:** Posgrado / Maestría  
**Prerrequisitos:** Temas 1 y 2 (Tokens, parámetros de decodificación, embeddings, comparación de proveedores)

---

## Tema #3: Consideraciones de Costos (90 min)

### Objetivos de aprendizaje

Al finalizar el tema, el estudiante podrá:

1. Identificar los costos **visibles y ocultos** de un despliegue LLM
2. Calcular el **TCO (Costo Total de Propiedad)** a 12 y 24 meses para los tres escenarios de despliegue principales
3. Evaluar proveedores usando un **framework multicriterio ponderado** adaptado al contexto LATAM
4. Estimar el **ROI ajustado por riesgo** y el **período de recuperación de la inversión**

### Estructura de la clase

| Bloque | Duración | Contenido |
|--------|----------|-----------|
| A | 20 min | Iceberg de costos: ¿qué se ve y qué se oculta? |
| B | 25 min | Modelos de precios y referencia oct-2026 |
| C | 30 min | Framework TCO: CAPEX + VP(OPEX) + Riesgo |
| D | 15 min | Lab 05 + Lab 06 en vivo |

### Conceptos clave

#### 1. Estructura de costos

```
COSTO VISIBLE (iceberg superficial)
├── Precio por token (input/output)
├── Suscripción mensual
└── Hosting básico

COSTO OCULTO (bajo el agua)
├── Ingeniería: diseño de prompts, guardrails, evaluación
├── Latencia: pérdida de conversión por respuestas lentas
├── Cumplimiento: auditorías, legal, privacidad (LGPD, Ley 25.326)
├── Integración: adaptadores, ETL, migración de datos
├── Calidad: hallucination rate, fact-checking manual
└── Migración: lock-in y costos de salida
```

#### 2. Modelos de precios (oct-2026)

| Modelo | Input ($/1M tk) | Output ($/1M tk) | Ventaja |
|--------|-----------------|------------------|---------|
| GPT-4o mini | $0.15 | $0.60 | Precio/rendimiento |
| Gemini 1.5 Flash | $0.075 | $0.30 | Más barato |
| Claude 3 Haiku | $0.25 | $1.25 | Alta velocidad |
| GPT-4o | $2.50 | $10.00 | Calidad máxima |
| Gemini 1.5 Pro | $1.25 | $5.00 | Contexto largo |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Razonamiento |
| Llama 3.1 70B (HF) | $0.59 | $0.79 | Open source |

> ⚠️ Estos precios son ilustrativos. Verificar siempre en la web oficial del proveedor.

#### 3. Fórmula TCO

```
TCO = CAPEX + Σ (OPEX_mes_t / (1 + r)^t)  para t = 1..N
```

Donde:
- `CAPEX`: infraestructura inicial, licencias, consultoría de setup
- `OPEX_mes_t`: tokens + hosting + personal + mantenimiento en el mes t
- `r`: tasa de descuento mensual = `(1 + tasa_anual)^(1/12) - 1`

#### 4. ROI y payback

```
ROI = (Beneficio Neto / TCO) × 100
Beneficio Neto = Σ VP(beneficios_mes_t) - TCO

ROI ajustado = ROI × (1 - prob_fallo) - (prob_fallo × impacto / TCO × 100)
```

**Payback** = mes en que el flujo acumulado cruza cero (interpolación lineal entre meses)

#### 5. Framework de evaluación multicriterio (LATAM)

| Criterio | Banco (BR) | E-comm (MX) | Startup (AR) | Hospital (CL) |
|----------|------------|-------------|--------------|---------------|
| Costo/token | 15% | 35% | 25% | 10% |
| Cumplimiento | 35% | 10% | 10% | 30% |
| Latencia P95 | 10% | 25% | 20% | 20% |
| Ecosistema | 10% | 15% | 30% | 15% |
| Privacidad datos | 20% | 10% | 10% | 40% |
| Soporte técnico | 5% | 0% | 0% | 5% |
| Soporte español | 5% | 5% | 5% | 0% |

### Labs del Tema 3

#### Lab 05: Evaluación de proveedores
```bash
python labs/sesion2/05_evaluacion_proveedores.py
```
- No requiere API keys
- Evalúa 7 proveedores con datos ilustrativos
- Permite cambiar los pesos para diferentes casos de uso LATAM
- Exporta `resultados_proveedores.json`

#### Lab 06: TCO y ROI
```bash
python labs/sesion2/06_tco_y_roi.py
```
- Calcula TCO para 3 escenarios de una empresa de 200 empleados
- Muestra flujo acumulado en ASCII
- Incluye análisis de sensibilidad por tasa de crecimiento

### Preguntas para debate

1. ¿Por qué el On-Premise puede tener ROI más alto a largo plazo pero payback más largo?
2. ¿Qué criterio adicional agregarías para el mercado de tu país?
3. ¿Cómo cambia la evaluación si el modelo necesita procesar datos personales sensibles?
4. ¿Cuándo tiene sentido un modelo PTU vs pago por uso?

---

## Tema #4: Patrones y Escalabilidad (90 min)

### Objetivos de aprendizaje

Al finalizar el tema, el estudiante podrá:

1. Explicar la diferencia entre arquitectura **monolítica y de microservicios** aplicada a LLMs
2. Implementar los patrones **API Gateway**, **Circuit Breaker** y **Sidecar** conceptualmente
3. Decidir cuándo usar **escalado horizontal vs vertical**
4. Elegir entre **Kubernetes y Docker Swarm** según el contexto del proyecto
5. Diferenciar integración **síncrona (SSE)** vs **asíncrona (cola de mensajes)**

### Estructura de la clase

| Bloque | Duración | Contenido |
|--------|----------|-----------|
| A | 20 min | Monolito vs microservicios en LLMs |
| B | 25 min | 5 patrones esenciales + contenedores |
| C | 30 min | Escalabilidad y orquestadores |
| D | 15 min | Lab 07 + Lab 08 en vivo |

### Conceptos clave

#### 1. Cinco patrones arquitectónicos para LLMs

**Patrón 1 — API Gateway**
```
Cliente → [Gateway] → Auth → Rate Limit → Router → Backend LLM
                                                   ↘ Fallback
```
Centraliza autenticación, throttling, logging y enrutamiento. Permite A/B testing entre modelos.

**Patrón 2 — Circuit Breaker**
```
Estados: CERRADO → (N errores consecutivos) → ABIERTO
                                              ↓ (timeout)
                                          SEMIABIERTO → (éxito) → CERRADO
```
Previene cascada de fallos cuando un proveedor LLM está saturado.

**Patrón 3 — Sidecar**
```
Pod Kubernetes:
  ┌─────────────────┬────────────────┐
  │  App Principal  │  Sidecar       │
  │  (FastAPI)      │  (log, métricas│
  │                 │   mTLS, proxy) │
  └─────────────────┴────────────────┘
```
Extiende la funcionalidad sin modificar el servicio principal.

**Patrón 4 — Caché semántica**
```
Query → Embedding → Búsqueda en caché (coseno > 0.92) → Hit? → Respuesta
                                                        ↓ Miss
                                                    LLM → Guardar → Respuesta
```
Ahorra 40-70% de tokens en casos de uso con preguntas frecuentes.

**Patrón 5 — Worker asíncrono**
```
API → Cola (Kafka/SQS) → Worker Pool → LLM → Resultado
                                            → Webhook / SSE push
```
Ideal para procesamiento masivo de documentos, generación de reportes.

#### 2. Contenedores multi-stage

| Métrica | Imagen monolítica | Multi-stage |
|---------|-------------------|-------------|
| Tamaño | ~1.5 GB | ~335 MB |
| Reducción | — | ~78% |
| Vulnerabilidades | Alto | Mínimo |
| Tiempo de pull | Lento | Rápido |

Principio clave: el stage de **build** compila e instala dependencias; el stage de **runtime** copia solo los archivos compilados, sin compiladores ni herramientas de build.

#### 3. Escalado horizontal vs vertical

| Dimensión | Horizontal (scale-out) | Vertical (scale-up) |
|-----------|------------------------|---------------------|
| Límite | Prácticamente ilimitado | Máquina más grande disponible |
| HA | Inherente | SPOF (punto único de fallo) |
| Costo | Escala lineal | Escala superlineal |
| LLM | Funciona para APIs stateless | Necesario para GPU única muy grande |
| Complejidad | Load balancer, estado distribuido | Simple de operar |

#### 4. HPA (Horizontal Pod Autoscaler)

```yaml
minReplicas: 2
maxReplicas: 8
targetCPUUtilizationPercentage: 70
scaleUpStabilization: 60s    # Evita flapping
scaleDownStabilization: 300s  # Conservador en reducción
```

**KEDA** extiende esto con triggers basados en colas (Kafka lag, SQS depth), permitiendo **scale-to-zero** en horas de baja demanda.

#### 5. Kubernetes vs Docker Swarm

| Criterio | Docker Swarm | Kubernetes |
|----------|-------------|------------|
| Curva de aprendizaje | Baja | Alta |
| Setup | `docker swarm init` | Múltiples componentes |
| Auto-scaling | Manual | HPA + KEDA |
| GPU scheduling | Básico | Avanzado |
| Recomendado para | MVP, <5 servicios | Producción, >10 servicios |

#### 6. Integración con sistemas existentes

```
SÍNCRONO (REST/SSE):
  Cliente ←→ API ←→ LLM     (streaming tiempo real)
  
ASÍNCRONO (Cola):
  API → Kafka/SQS → Workers → LLM → Resultado
  (procesamiento batch, alto volumen, resiliente)
```

**Cuándo usar cada patrón:**
- **SSE/streaming**: chat, búsqueda, asistente en tiempo real
- **Cola de mensajes**: análisis de documentos, generación de reportes, ETL con LLM, pipelines de datos

### Labs del Tema 4

#### Lab 07: Microservicios y contenedores
```bash
python labs/sesion2/07_microservicios_y_contenedores.py
```
- Simula API Gateway con Round-Robin y retry
- Implementa Circuit Breaker con transiciones de estado
- Muestra comparativa Dockerfile monolítico vs multi-stage
- No requiere Docker instalado

#### Lab 08: Escalabilidad y orquestación
```bash
python labs/sesion2/08_escalabilidad_y_orquestacion.py
```
- Simula 24 horas de tráfico LATAM (picos 12-14h y 19-22h)
- Autoscaler con lógica de cooldown
- Comparativa K8s vs Docker Swarm
- Cola de mensajes asíncrona con Kafka/SQS/Redis

### Archivos de infraestructura

Los manifests son **didácticos** — cada sección está comentada con el "por qué":

```
infrastructure/
├── kubernetes/deployment.yaml      # Namespace, ConfigMap, Secret, Deployments,
│                                   # Services, Ingress, HPA, KEDA (comentado)
└── docker-swarm/docker-stack.yml   # Traefik, Ollama, Backend, Frontend, Watchtower
```

### API del backend (Tema 4)

```
POST /api/architecture/proveedores/evaluar    # Evalúa y rankea proveedores
GET  /api/architecture/proveedores/lista       # Catálogo completo
GET  /api/architecture/proveedores/casos-uso   # Presets LATAM
POST /api/architecture/tco/calcular            # TCO/ROI/VAN/payback
POST /api/architecture/scaling/analizar        # Recomendación horizontal/vertical
GET  /api/architecture/patrones                # Catálogo de 5 patrones
```

### Preguntas para debate

1. ¿Un LLM debería ser un microservicio o parte del monolito? ¿Cuándo cambia la respuesta?
2. ¿Por qué el Circuit Breaker es especialmente importante cuando el LLM es un tercero (OpenAI, Gemini)?
3. ¿Qué tiene que ser verdad para que el escalado horizontal funcione bien con LLMs?
4. ¿Cuándo elegiría Docker Swarm sobre Kubernetes en tu organización?
5. ¿Cómo diseñaría la integración con un bus de mensajería existente (RabbitMQ, Kafka)?

---

## Resumen ejecutivo del módulo

| Tema | Decisión clave | Herramienta del repo |
|------|---------------|----------------------|
| Costos | TCO 24m > precio/token | Lab 06 + `/api/architecture/tco` |
| Proveedores | Framework ponderado por contexto | Lab 05 + `/api/architecture/proveedores` |
| Patrones | Circuit Breaker + Caché semántica para resiliencia | Lab 07 |
| Escalado | Horizontal para APIs, Vertical para modelos grandes | Lab 08 |
| Orquestación | Swarm para MVP, K8s para producción | `infrastructure/` |

---

*Última actualización: octubre 2026*
