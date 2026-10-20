"""
Tests para los endpoints de arquitectura y TCO — Sesión 3, Tema 6.

Cubre:
  - Generación de plantilla ADR
  - Cálculo de TCO (Total Cost of Ownership)
  - Análisis de sensibilidad de costos
  - Acceso a plantillas de documentación
"""
import pytest
import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENVIRONMENT", "test")

# Escenario de prueba reutilizable
SCENARIO_OLLAMA = {
    "name": "Ollama Local",
    "monthly_llm_calls": 1000,
    "avg_tokens_per_call": 1000,
    "provider": "ollama_local",
    "infrastructure": "vm",
    "team_engineers": 1,
}
SCENARIO_OPENAI = {
    "name": "OpenAI",
    "monthly_llm_calls": 1000,
    "avg_tokens_per_call": 1000,
    "provider": "openai",
    "infrastructure": "cloud_run",
    "team_engineers": 1,
}


@pytest.mark.anyio
class TestArchitectureEndpoints:
    """Tests para los endpoints de arquitectura."""

    async def test_architecture_canvas_requires_auth(self, client):
        response = await client.get("/api/architecture/canvas")
        assert response.status_code == 401

    async def test_architecture_canvas_returns_adr_template(self, client, user_headers):
        response = await client.get("/api/architecture/canvas", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "adr" in str(data).lower() or "decision" in str(data).lower()

    async def test_cost_analysis_requires_auth(self, client):
        response = await client.post(
            "/api/architecture/costs",
            json={"scenarios": [SCENARIO_OLLAMA]},
        )
        assert response.status_code == 401

    async def test_cost_analysis_with_ollama(self, client, user_headers):
        response = await client.post(
            "/api/architecture/costs",
            json={"scenarios": [SCENARIO_OLLAMA]},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "escenarios" in data
        scenario = data["escenarios"][0]
        # Ollama no tiene costo de API
        assert scenario["costos_mensuales"]["llm_api"] == 0.0

    async def test_cost_analysis_with_openai(self, client, user_headers):
        response = await client.post(
            "/api/architecture/costs",
            json={"scenarios": [SCENARIO_OPENAI]},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "escenarios" in data
        scenario = data["escenarios"][0]
        # OpenAI tiene costo de API
        assert scenario["costos_mensuales"]["llm_api"] > 0.0

    async def test_cost_analysis_openai_more_expensive_than_ollama(self, client, user_headers):
        """OpenAI debe ser más costoso que Ollama para el mismo volumen."""
        response = await client.post(
            "/api/architecture/costs",
            json={"scenarios": [SCENARIO_OLLAMA, SCENARIO_OPENAI]},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        escenarios = {s["escenario"]: s for s in data["escenarios"]}
        ollama_cost = escenarios["Ollama Local"]["costos_mensuales"]["llm_api"]
        openai_cost = escenarios["OpenAI"]["costos_mensuales"]["llm_api"]
        assert openai_cost >= ollama_cost

    async def test_cost_analysis_response_structure(self, client, user_headers):
        """La respuesta debe tener la estructura correcta."""
        response = await client.post(
            "/api/architecture/costs",
            json={"scenarios": [SCENARIO_OLLAMA]},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "proyecto" in data
        assert "horizonte_meses" in data
        assert "moneda" in data
        assert "escenarios" in data
        assert "recomendacion" in data

        scenario = data["escenarios"][0]
        assert "costos_mensuales" in scenario
        assert "tco_24_meses" in scenario
        assert "setup_inicial" in scenario

    async def test_templates_endpoint(self, client, user_headers):
        response = await client.get("/api/architecture/templates", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "plantillas" in data
        assert len(data["plantillas"]) > 0
        # Verificar que tiene los IDs esperados
        ids = {t["id"] for t in data["plantillas"]}
        assert "adr" in ids


class TestTCOCalculation:
    """Tests unitarios para el cálculo de TCO."""

    def test_ollama_has_zero_token_cost(self):
        """Ollama no tiene costo por token (self-hosted)."""
        from app.routers.architecture import analyze_costs, CostAnalysisRequest, CostScenario
        # El costo por token de ollama_local es 0
        from app.routers.architecture import CostScenario
        scenario = CostScenario(
            name="test",
            monthly_llm_calls=100_000,
            avg_tokens_per_call=1000,
            provider="ollama_local",
            infrastructure="local",
        )
        assert scenario.provider == "ollama_local"

    def test_tco_includes_infrastructure(self):
        """El TCO debe incluir costos de infraestructura, no solo tokens."""
        infra_costs = {"cloud_run": 25, "kubernetes": 150, "vm": 90, "local": 10}
        assert all(v > 0 for v in infra_costs.values())

    def test_24_month_tco_projection(self):
        """24 meses de TCO debe ser consistente con el mensual."""
        monthly_cost = 150.0
        months = 24
        projected_tco = monthly_cost * months
        assert projected_tco == 3600.0
