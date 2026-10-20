"""
Security Router — Tema 5: WAF y Detección de Amenazas

POST /api/security/scan  → analizar texto en busca de amenazas
GET  /api/security/stats → estadísticas de amenazas detectadas
"""

import re
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.routers.auth import get_current_user, TokenData
from app.services.audit_logger import AuditLogger, AuditEvent

router = APIRouter()

# ── Reglas WAF (Web Application Firewall simulado) ────────────────────────────

WAF_RULES = {
    "prompt_injection": {
        "severity": "HIGH",
        "patterns": [
            r"ignore\s+(previous|all|prior)\s+instructions",
            r"you\s+are\s+now\s+(a|an)",
            r"disregard\s+your\s+(training|instructions|guidelines)",
            r"system\s*prompt",
            r"jailbreak",
            r"DAN\s+mode",
            r"developer\s+mode",
        ],
    },
    "sql_injection": {
        "severity": "HIGH",
        "patterns": [
            r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",
            r"UNION\s+SELECT",
            r"DROP\s+TABLE",
            r"--\s*$",
            r";\s*DELETE\s+FROM",
        ],
    },
    "xss": {
        "severity": "MEDIUM",
        "patterns": [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=\s*[\"']",
            r"<iframe",
        ],
    },
    "path_traversal": {
        "severity": "MEDIUM",
        "patterns": [
            r"\.\./",
            r"\.\.\\",
            r"/etc/passwd",
            r"/etc/shadow",
            r"C:\\Windows",
        ],
    },
    "sensitive_data_leak": {
        "severity": "LOW",
        "patterns": [
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # tarjeta de crédito
            r"\b[A-Z]{2}\d{6}[A-Z]?\b",                   # pasaporte
        ],
    },
}


# ── Modelos ──────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    text: str = Field(..., max_length=5000, description="Texto a analizar")
    context: str = Field(default="user_input", description="Origen del texto")


class ThreatMatch(BaseModel):
    rule: str
    severity: str
    pattern: str
    match: str


class ScanResponse(BaseModel):
    safe: bool
    threat_count: int
    threats: list[ThreatMatch]
    recommendation: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Analizar texto con el WAF simulado",
)
async def scan_text(
    request: Request,
    body: ScanRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Analiza un texto en busca de patrones maliciosos conocidos.

    Categorías detectadas:
    - **prompt_injection**: intentos de manipular el comportamiento del LLM
    - **sql_injection**: inyección SQL clásica
    - **xss**: Cross-Site Scripting
    - **path_traversal**: acceso a archivos del sistema
    - **sensitive_data_leak**: datos sensibles que no deberían enviarse al LLM

    **Nota pedagógica**: Este es un WAF básico de demostración.
    Un WAF de producción (AWS WAF, Cloudflare, ModSecurity) tiene miles de reglas
    y usa ML para detectar variantes no conocidas.
    """
    audit = AuditLogger.get()
    ip = request.client.host if request.client else "unknown"
    threats: list[ThreatMatch] = []

    for rule_name, rule in WAF_RULES.items():
        for pattern in rule["patterns"]:
            matches = re.findall(pattern, body.text, re.IGNORECASE)
            for match in matches:
                threats.append(ThreatMatch(
                    rule=rule_name,
                    severity=rule["severity"],
                    pattern=pattern,
                    match=str(match)[:100],
                ))

    safe = len(threats) == 0

    if not safe:
        high_severity = any(t.severity == "HIGH" for t in threats)
        await audit.log(
            AuditEvent.WAF_BLOCK,
            user=current_user.sub,
            ip=ip,
            severity="WARNING" if not high_severity else "ERROR",
            details={
                "context": body.context,
                "threats": [t.rule for t in threats],
                "text_preview": body.text[:100],
            },
        )

    recommendation = _get_recommendation(threats)

    return ScanResponse(
        safe=safe,
        threat_count=len(threats),
        threats=threats,
        recommendation=recommendation,
    )


def _get_recommendation(threats: list[ThreatMatch]) -> str:
    if not threats:
        return "✅ El texto no contiene patrones maliciosos conocidos."

    severities = {t.severity for t in threats}
    rules = {t.rule for t in threats}

    if "HIGH" in severities:
        return (
            "🚨 BLOQUEAR: Se detectaron amenazas de alta severidad. "
            f"Categorías: {', '.join(rules)}. No procesar este input."
        )
    return (
        f"⚠️ REVISAR: Se detectaron posibles amenazas de severidad media/baja. "
        f"Categorías: {', '.join(rules)}. Sanitizar antes de procesar."
    )
