# Glosario — Temas 5 y 6: Seguridad, Alta Disponibilidad, Diseño y Documentación

---

## A

**ADR (Architecture Decision Record)**  
Documento que captura una decisión arquitectónica importante, su contexto, las alternativas
consideradas y las consecuencias esperadas. Vive en el repositorio junto al código.

**Algorithm Confusion Attack**  
Ataque a JWT donde el atacante modifica el campo `alg` del header (ej: de RS256 a HS256)
para que el servidor verifique la firma con la clave pública como si fuera una clave simétrica.

**Audit Trail (Rastro de Auditoría)**  
Registro cronológico e inmutable de eventos del sistema. Cada entrada contiene: timestamp,
actor, acción, objeto afectado, y hash SHA-256 que encadena con la entrada anterior.

**Authorization Code Flow**  
Flujo OAuth2 donde el cliente recibe un código temporal que intercambia por tokens.
Más seguro que el Password Flow pero requiere redirección al proveedor de identidad.

---

## B

**Blacklist (Lista Negra de Tokens)**  
Almacén (generalmente Redis) de JTIs de tokens que han sido revocados antes de su expiración.
En cada request se verifica que el `jti` del token no esté en la blacklist.

**Bulk Head Pattern**  
Patrón de resiliencia que aísla componentes del sistema en "compartimentos estancos" para
que el fallo de uno no afecte a los demás. Análogo a los mamparos de un barco.

---

## C

**C4 Model**  
Framework para documentar arquitecturas de software en 4 niveles de abstracción:
Context (L1), Containers (L2), Components (L3), Code (L4). Creado por Simon Brown.

**Circuit Breaker**  
Patrón de resiliencia con 3 estados: CERRADO (normal), ABIERTO (rechaza requests),
SEMIABIERTO (prueba recuperación). Previene fallos en cascada en sistemas distribuidos.

**Claims (JWT)**  
Pares clave-valor en el payload de un JWT. Claims registrados (sub, exp, iat, jti),
públicos (definidos en IANA) y privados (específicos de la aplicación como `scopes`).

**CSP (Content Security Policy)**  
Header HTTP que restringe las fuentes de contenido que un navegador puede cargar,
mitigando ataques XSS al definir origins permitidos para scripts, styles e imágenes.

---

## D

**Disaster Recovery (DR)**  
Conjunto de políticas y procedimientos para restaurar sistemas críticos después de un
evento catastrófico. Incluye estrategias de Backup & Restore, Pilot Light, Warm Standby
y Multi-site Active/Active.

---

## E

**Exponential Backoff**  
Estrategia de reintento donde el tiempo de espera aumenta exponencialmente después
de cada fallo. Incluye "jitter" (variación aleatoria) para evitar tormentas de reintentos.

---

## F

**Failover**  
Proceso de cambiar automáticamente a un sistema redundante cuando el principal falla.
Puede ser manual (cold failover) o automático (hot failover).

**FAPI (Financial-grade API)**  
Especificación de seguridad de OAuth2 para APIs de alto riesgo. Requiere PKCE, mTLS,
access tokens con vida muy corta y binding de tokens a certificados de cliente.

---

## G

**Game Day**  
Ejercicio planificado de simulación de fallos para validar la resiliencia del sistema
y los procedimientos de DR. Popularizado por Netflix y Amazon.

---

## H

**Hash Chain (Cadena de Hashes)**  
Estructura donde cada entrada del log incluye el hash SHA-256 de la entrada anterior,
creando una cadena inmutable. Cualquier modificación invalida todas las entradas posteriores.

**HSTS (HTTP Strict Transport Security)**  
Header HTTP que indica al navegador que solo debe conectar vía HTTPS para este dominio,
protegiendo contra ataques de downgrade y SSL stripping.

---

## J

**JTI (JWT ID)**  
Claim estándar de JWT que proporciona un identificador único al token. Permite la
revocación individual de tokens usando una blacklist.

**JWT (JSON Web Token)**  
Estándar RFC 7519 para transmitir información segura como objeto JSON firmado.
Estructura: `header.payload.signature`, donde cada parte es Base64url-encoded.

---

## L

**Liveness Probe**  
Verificación que determina si un proceso está vivo (no bloqueado en deadlock). En
Kubernetes, si falla, el pod se reinicia. Endpoint típico: `/health/live`.

---

## O

**OAuth2 (Open Authorization 2.0)**  
Framework de autorización (RFC 6749) que permite a aplicaciones de terceros acceder
a recursos de usuario sin exponer credenciales. Define 4 flujos según el tipo de cliente.

**OWASP LLM Top 10**  
Lista de los 10 riesgos más críticos en aplicaciones LLM. #1: Prompt Injection;
#2: Insecure Output Handling; #3: Training Data Poisoning.

---

## P

**Pilot Light**  
Estrategia DR donde se mantiene una infraestructura mínima siempre encendida en la
región de recuperación, lista para escalar en minutos. RTO: 4-8 horas.

**Prompt Injection**  
Ataque donde entradas maliciosas manipulan las instrucciones del LLM, ignorando el
system prompt o extrayendo información confidencial del contexto.

**PRD (Product Requirements Document)**  
Documento que define QUÉ construir (requisitos funcionales y no funcionales) y POR QUÉ.
Se diferencia del design doc que define CÓMO construirlo.

---

## R

**Rate Limiting**  
Control que limita el número de requests que un cliente puede hacer en un período.
Algoritmos: Token Bucket, Sliding Window, Fixed Window.

**Readiness Probe**  
Verificación que determina si un servicio está listo para recibir tráfico. Verifica
dependencias (DB, LLM, caché). Si falla, el load balancer deja de enviarle tráfico.

**RFC (Request for Comments)**  
En contexto interno, documento formal que propone un cambio técnico significativo,
solicita revisión de pares y documenta la decisión final.

**RPO (Recovery Point Objective)**  
Pérdida máxima aceptable de datos medida en tiempo. Un RPO de 1 hora significa que
si hay un desastre, es aceptable perder los últimos 60 minutos de datos.

**RTO (Recovery Time Objective)**  
Tiempo máximo aceptable que el sistema puede estar caído después de un desastre.
Un RTO de 4 horas significa que el servicio debe estar restaurado en máximo 4 horas.

---

## S

**Scopes (JWT)**  
Lista de permisos asignados a un token. Ejemplo: `["read", "write", "admin"]`.
El servidor verifica que el scope requerido esté en el token antes de permitir el acceso.

**SLI (Service Level Indicator)**  
Métrica concreta que mide un aspecto del servicio. Ejemplo: latencia p99, tasa de error.

**SLO (Service Level Objective)**  
Objetivo de nivel de servicio basado en SLIs. Ejemplo: "latencia p99 < 2000ms en 99.9% del tiempo".

**Sliding Window Rate Limiting**  
Algoritmo de rate limiting que usa una ventana temporal deslizante en lugar de una
ventana fija, evitando ráfagas al cambiar de ventana.

---

## T

**TCO (Total Cost of Ownership)**  
Análisis de todos los costos asociados a un sistema durante su vida útil: costos
directos (API, infra) e indirectos (operaciones, desarrollo, entrenamiento).

**Token Bucket**  
Algoritmo de rate limiting donde cada cliente tiene un "balde" con tokens. Cada request
consume un token; el balde se recarga a una tasa constante. Permite ráfagas controladas.

---

## W

**WAF (Web Application Firewall)**  
Componente que filtra, monitorea y bloquea tráfico HTTP malicioso. En sistemas LLM,
agrega protección contra prompt injection y ataques clásicos (SQLi, XSS).

**Warm Standby**  
Estrategia DR donde se mantiene una instancia secundaria completamente funcional pero
con capacidad reducida. Puede escalar a producción en minutos. RTO: 30-60 minutos.

---

## X

**XSS (Cross-Site Scripting)**  
Ataque donde scripts maliciosos se inyectan en páginas web. En sistemas LLM, podría
usarse para robar tokens JWT almacenados en localStorage del navegador.

---

*Glosario generado para Sesión 3 · Capítulos 2 y 3 · Maestría BSG*
