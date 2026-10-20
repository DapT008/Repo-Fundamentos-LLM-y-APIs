# Sesión 3 — Tema 5: Seguridad y Alta Disponibilidad en Sistemas LLM

**Capítulo 2 · Duración: ~2 horas**

---

## Objetivos de Aprendizaje

Al finalizar este tema, el estudiante podrá:
- Implementar autenticación JWT con scopes y refresh tokens en FastAPI
- Diseñar un WAF simulado para proteger endpoints LLM
- Aplicar el patrón Circuit Breaker con estados CERRADO/ABIERTO/SEMIABIERTO
- Configurar estrategias de failover multi-proveedor
- Interpretar métricas de salud y diseñar políticas de monitoreo

---

## 1. Autenticación JWT

### Anatomía de un JWT

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9     ← Header (Base64url)
.eyJzdWIiOiJ1c2VyMSIsInNjb3BlcyI6WyJyZWFkIl19  ← Payload (Base64url)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c   ← Firma (HMAC-SHA256)
```

**Header decodificado:**
```json
{ "alg": "HS256", "typ": "JWT" }
```

**Payload con claims estándar:**
```json
{
  "sub": "user@example.com",   // Subject (identificador)
  "iat": 1700000000,           // Issued at (Unix timestamp)
  "exp": 1700001800,           // Expiration (30 min después)
  "scopes": ["read", "write"], // Claims custom
  "jti": "uuid-único"          // JWT ID (para revocación)
}
```

### OAuth2 Password Flow (RFC 6749 §4.3)

```
Cliente → POST /auth/token (username + password)
        ← { access_token, refresh_token, expires_in }

Cliente → GET /api/resource
          Authorization: Bearer <access_token>
        ← Recurso protegido

(expirado) Cliente → POST /auth/refresh { refresh_token }
                   ← Nuevo { access_token, refresh_token }
```

### Sistema de Scopes

| Scope | Permisos |
|-------|----------|
| `read` | Ver historial, consultas básicas |
| `write` | Enviar mensajes al LLM |
| `admin` | Ver audit logs, gestionar usuarios |

### Ataques a JWT y mitigaciones

| Ataque | Técnica | Mitigación |
|--------|---------|-----------|
| **Algorithm confusion** | Cambiar `alg: RS256` a `alg: none` | Validar `alg` explícitamente |
| **Secret brute force** | Probar secrets débiles | Secrets ≥ 32 bytes aleatorios |
| **Token replay** | Reusar token robado | `exp` corto + blacklist por `jti` |
| **Claim injection** | Modificar payload sin firma | Verificar firma siempre |

---

## 2. Web Application Firewall (WAF) Simulado

### Taxonomía de amenazas en sistemas LLM

```
Prompt Injection     → Manipular el comportamiento del LLM
Indirect Injection   → Inyección vía datos recuperados (RAG)
SQL Injection        → Atacar la DB de historial
XSS                  → Robar tokens vía frontend
Path Traversal       → Leer archivos sensibles del servidor
Sensitive Data Leak  → Exponer claves/credenciales en logs
```

### Arquitectura del WAF en FastAPI

```
Request → [Rate Limiter] → [WAF Middleware] → [Auth] → [Route Handler]
                              ↓ (blocked)
                         [Audit Log]
                              ↓
                         [Response 400 + reason]
```

### Reglas WAF (expresiones regulares)

```python
WAF_RULES = {
    "prompt_injection": (r"ignore.*instructions|you are now.*mode", "HIGH"),
    "sql_injection":    (r"select.*from|drop\s+table|'.*or.*'='", "HIGH"),
    "xss":              (r"<script>|javascript:|on\w+\s*=",        "MEDIUM"),
    "path_traversal":   (r"\.\./|\%2e\%2e",                       "MEDIUM"),
    "sensitive_data":   (r"api_key\s*=|password\s*=\s*\S+",       "LOW"),
}
```

---

## 3. Circuit Breaker

### Máquina de estados

```
                    threshold fallos alcanzado
    CERRADO ──────────────────────────────────► ABIERTO
       ▲                                          │
       │                                          │ timeout (30s)
       │ request exitoso                          ▼
       │                                      SEMIABIERTO
       └──────────────────────────────────────────┘
              (deja pasar 1 request de prueba)
```

### Configuración recomendada

| Parámetro | Desarrollo | Producción |
|-----------|-----------|-----------|
| `failure_threshold` | 3 | 5 |
| `recovery_timeout` | 10s | 30s |
| `half_open_max_calls` | 1 | 2 |
| Métrica base | Conteo | Tasa de error (%) |

---

## 4. Alta Disponibilidad

### Failover Multi-Proveedor

```python
PROVIDERS = [
    ("ollama_local",  priority=1, cost="gratis"),
    ("vertex_gemini", priority=2, cost="$0.075/1M tokens"),
    ("openai_gpt4o",  priority=3, cost="$2.50/1M tokens"),
]
```

**Estrategia de fallback:**
1. Intenta con Ollama (Circuit Breaker CERRADO)
2. Si falla → activa Circuit Breaker → prueba Vertex
3. Si Vertex falla → prueba OpenAI como último recurso
4. Si todo falla → respuesta en caché o error controlado

### Health Checks

| Tipo | Endpoint | Verificación |
|------|----------|--------------|
| **Liveness** | `/api/health/live` | Proceso vivo, no deadlock |
| **Readiness** | `/api/health/ready` | DB + LLM disponibles |
| **Startup** | (Kubernetes) | Inicialización completa |

---

## 5. Disaster Recovery

### Estrategias y sus características

| Estrategia | RTO | RPO | Costo relativo |
|-----------|-----|-----|----------------|
| Backup & Restore | 24-48h | 24h | 1x |
| Pilot Light | 4-8h | 1h | 2x |
| Warm Standby | 30min-1h | 5min | 3x |
| Multi-site Active/Active | <1min | ~0 | 8x |

**RTO** (Recovery Time Objective): tiempo máximo aceptable de caída
**RPO** (Recovery Point Objective): pérdida máxima aceptable de datos

---

## Labs de este tema

| Lab | Archivo | Tiempo |
|-----|---------|--------|
| 09 — Autenticación JWT | `labs/sesion3/09_autenticacion_jwt.py` | 30 min |
| 10 — Rate Limiting y WAF | `labs/sesion3/10_rate_limiting_y_waf.py` | 25 min |
| 11 — Alta Disponibilidad | `labs/sesion3/11_alta_disponibilidad.py` | 30 min |
| 12 — Monitoreo y Logging | `labs/sesion3/12_monitoreo_y_logging.py` | 25 min |

```bash
make lab09   # Ejecuta lab de JWT
make lab10   # Rate Limiting y WAF
make lab11   # Circuit Breaker y failover
make lab12   # Monitoreo y audit log
```

---

## Referencias

- RFC 7519 — JSON Web Token: https://tools.ietf.org/html/rfc7519
- RFC 6749 — OAuth 2.0: https://tools.ietf.org/html/rfc6749
- OWASP Top 10 LLM: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Circuit Breaker (Martin Fowler): https://martinfowler.com/bliki/CircuitBreaker.html
- AWS DR Strategies: https://aws.amazon.com/blogs/architecture/disaster-recovery-options/
