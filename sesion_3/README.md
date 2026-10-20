# Sesión 3 · Capítulos 2 y 3: Seguridad, Alta Disponibilidad y Diseño Arquitectónico

Repositorio del curso **Fundamentos de Arquitectura LLM** (BSG Institute) —
**Capítulo 2 (Bases Arquitectónicas) · Capítulo 3 (Proyecto Integrador)**.

| Sesión | Capítulo | Tema | Guía |
|---|---|---|---|
| 3 · T5 | Cap. 2 | Seguridad y alta disponibilidad: autenticación, cifrado, WAF/IAM, failover, monitoreo | [docs/05_sesion3_seguridad_y_ha.md](docs/05_sesion3_seguridad_y_ha.md) |
| 3 · T6 | Cap. 3 | Diseño y documentación: alcance, requerimientos, arquitectura, análisis de costos | [docs/06_sesion3_diseno_y_documentacion.md](docs/06_sesion3_diseno_y_documentacion.md) |

**Stack:** Python 3.12 · FastAPI · React 18 · Vite 6 · Ollama · JWT/OAuth2 · Docker Swarm · Kubernetes · Ubuntu 24.04+

---

## ¿Qué hay en este repositorio?

```
sesion3-seguridad-arquitectura-llm/
├── backend/                  API FastAPI "LLM Security Lab": auth JWT, rate-limiting, audit log, health
│   ├── app/routers/          Endpoints: auth, chat, audit, health, architecture
│   ├── app/services/         JWT service, rate limiter, audit logger, circuit breaker
│   ├── app/middleware/       Security headers, request logging, CORS
│   ├── app/models/           Modelos de datos (Pydantic v2)
│   └── tests/                Pruebas unitarias (sin Ollama requerido)
├── frontend/                 React 18 + Vite 6: panel de seguridad y diseño de arquitectura
│   └── src/
│       ├── components/       SecurityDashboard, AuthPanel, AuditLog, ArchDiagram
│       ├── pages/            Login, Dashboard, Architecture, Documentation
│       └── services/         API client con interceptores de seguridad
├── labs/sesion3/
│   ├── 09_autenticacion_jwt.py        JWT, OAuth2 y buenas prácticas de autenticación
│   ├── 10_rate_limiting_y_waf.py      Rate limiting, WAF simulado, detección de anomalías
│   ├── 11_alta_disponibilidad.py      Circuit breaker, failover, health checks
│   ├── 12_monitoreo_y_logging.py      Structured logging, métricas, audit trail
│   ├── 13_diseno_arquitectonico.py    Generador de plantillas de documentación técnica
│   └── 14_analisis_costos_proyecto.py TCO proyecto integrador con 3 escenarios
├── gcp-agent-platform/
│   ├── parte1_consola/       README paso a paso para Agent Studio (sin código)
│   ├── parte2_adk/           Agente con Google ADK publicado en Agent Runtime
│   └── parte3_docker_sin_adk/  Agente FastAPI sin framework → Cloud Run vía Docker
├── infrastructure/
│   ├── kubernetes/           Manifests: NetworkPolicy, PodDisruptionBudget, HPA, secrets
│   └── docker-swarm/         Stack con TLS, secrets, healthchecks y restart policies
├── docs/                     Guías de sesión, plantillas de documentación, glosario T5-T6
├── presentacion/             Presentación PPTX completa (Temas 5-6) con notas del orador
├── scripts/ollama_simulado.py  Plan B sin GPU (respuestas fijas, misma API)
├── docker-compose.yml        Ollama + backend + frontend con un comando
└── Makefile                  Atajos: setup, backend, frontend, test, labs…
```

## Inicio rápido (Ubuntu 24.04+)

```bash
# Prerrequisitos: Python 3.12, Node 22, Ollama → ver docs/00_instalacion_ubuntu.md
git clone <URL-DEL-REPOSITORIO> && cd sesion3-seguridad-arquitectura-llm
make setup          # entorno virtual + dependencias + backend/.env
make test           # pruebas (no requieren Ollama)

make backend        # terminal 1 → http://localhost:8000/docs
make frontend       # terminal 2 → http://localhost:5173
```

¿Sin GPU? `make simulado` levanta un Ollama simulado en puerto 11434.

Con Docker: `docker compose up -d --build` → <http://localhost:8080>

## Los 6 laboratorios de la Sesión 3

| Lab | Tema | Qué se aprende | API key |
|---|---|---|---|
| 09 | T5 | JWT, scopes, refresh tokens, OAuth2 password flow | No |
| 10 | T5 | Rate limiting por IP/usuario, WAF simulado, detección de prompts maliciosos | No |
| 11 | T5 | Circuit breaker, health checks, failover automático entre proveedores | No |
| 12 | T5 | Structured logging (JSON), audit trail inmutable, alertas por umbral | No |
| 13 | T6 | Plantillas de documentación arquitectónica: ADR, RFC, diagramas C4 | No |
| 14 | T6 | TCO del proyecto integrador a 24 meses, sensibilidad por escenario | No |

## API del backend (Sesión 3)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/token` | Login → JWT access + refresh token |
| POST | `/auth/refresh` | Renovar access token |
| GET  | `/auth/me` | Perfil del usuario autenticado |
| POST | `/api/chat` | Chat con LLM (requiere JWT) |
| GET  | `/api/health` | Estado del servicio y Ollama |
| GET  | `/api/audit/logs` | Últimas N entradas del audit log |
| POST | `/api/security/scan` | Detección de prompt injection |
| GET  | `/api/architecture/canvas` | Plantilla Architecture Decision Record |
| POST | `/api/architecture/costs` | Estimación TCO proyecto integrador |

Swagger interactivo: <http://localhost:8000/docs>

## Tema #5 — Seguridad y Alta Disponibilidad

### Conceptos clave implementados

| Componente | Implementación en este repo |
|---|---|
| Autenticación | JWT (HS256) + OAuth2 Password Flow (`/auth/token`) |
| Autorización | Scopes: `read`, `write`, `admin`; decoradores por rol |
| Cifrado en tránsito | HTTPS con certificado auto-firmado (Nginx + docker-compose) |
| Rate limiting | In-process (Redis-compatible) con ventana deslizante de 60s |
| WAF simulado | Detección de prompt injection, SQL injection en inputs |
| Circuit breaker | 3 estados: CERRADO → ABIERTO → SEMIABIERTO |
| Health checks | Endpoint `/health` con liveness + readiness |
| Audit log | Append-only JSONL con hash de integridad SHA-256 |
| Monitoreo | Structured logging JSON + métricas Prometheus-ready |

### Laboratorios T5 (sin API key)

```bash
python labs/sesion3/09_autenticacion_jwt.py    # Demostración completa de JWT
python labs/sesion3/10_rate_limiting_y_waf.py  # Rate limiter + WAF simulado
python labs/sesion3/11_alta_disponibilidad.py  # Circuit breaker y failover
python labs/sesion3/12_monitoreo_y_logging.py  # Audit trail y alertas
```

## Tema #6 — Diseño y Documentación

### Entregables del Proyecto Integrador

El Tema 6 produce la documentación base del Proyecto Integrador usando TechCorp Latinoamérica como caso de estudio:

| Documento | Plantilla | Descripción |
|---|---|---|
| PRD | `docs/plantillas/prd_template.md` | Product Requirements Document |
| ADR-001 | `docs/plantillas/adr_template.md` | Architecture Decision Record: elección de LLM |
| Diagrama C4 | `docs/plantillas/c4_template.md` | Contexto → Contenedores → Componentes |
| TCO inicial | Lab 14 | 3 escenarios × 24 meses |
| RFC-001 | `docs/plantillas/rfc_template.md` | Request for Comments: diseño de la API |

```bash
python labs/sesion3/13_diseno_arquitectonico.py    # Genera plantillas rellenas
python labs/sesion3/14_analisis_costos_proyecto.py # TCO proyecto integrador
```

## Google Cloud Agent Platform

Ver [gcp-agent-platform/README.md](gcp-agent-platform/README.md) — el mismo agente **TechCorp Security Assistant** construido de tres formas:

| Parte | Herramienta | Cuándo usarla |
|---|---|---|
| 1 | Agent Studio (consola GCP) | PoC rápido, sin código, ideal para demos |
| 2 | Google ADK + Agent Runtime | Agentes complejos en producción |
| 3 | FastAPI + Docker → Cloud Run | Control total, sin dependencia del SDK |

## ⚠️ Sobre las credenciales

`backend/.env` contiene valores de ejemplo. **Nunca** suba claves reales a un repositorio.
Ver `docs/05_sesion3_seguridad_y_ha.md` para la gestión segura de secretos con Docker Secrets y Kubernetes Secrets.

## Materiales docentes

- **Presentación completa**: `presentacion/Sesion3_Fundamentos_Arquitectura_LLM.pptx`
- Guía Tema 5: [docs/05_sesion3_seguridad_y_ha.md](docs/05_sesion3_seguridad_y_ha.md)
- Guía Tema 6: [docs/06_sesion3_diseno_y_documentacion.md](docs/06_sesion3_diseno_y_documentacion.md)
- Plantillas de documentación: [docs/plantillas/](docs/plantillas/)
- Glosario T5-T6: [docs/07_glosario_t5_t6.md](docs/07_glosario_t5_t6.md)

*Última actualización: octubre 2026*
