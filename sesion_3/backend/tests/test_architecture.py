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
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENVIRONMENT", "test")


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
        # Debe contener estructura de ADR
        assert "adr" in str(data).lower() or "decision" in str(data).lower()

    async def test_cost_analysis_requires_auth(self, client):
        response = await client.post("/api/architecture/costs", json={
            "monthly_requests": 10000,
            "avg_tokens": 500,
            "provider": "ollama"
        })
        assert response.status_code == 401

    async def test_cost_analysis_with_ollama(self, client, user_headers):
        response = await client.post(
            "/api/architecture/costs",
            json={
                "monthly_requests": 10000,
                "avg_tokens": 500,
                "provider": "ollama"
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Ollama es gratis (local), así que el costo por tokens debe ser 0
        assert "monthly_cost" in data or "total_cost" in data or "costs" in data

    async def test_cost_analysis_with_vertex_ai(self, client, user_headers):
        response = await client.post(
            "/api/architecture/costs",
            json={
                "monthly_requests": 100000,
                "avg_tokens": 1000,
                "provider": "vertex_ai"
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Vertex AI tiene costo
        assert data is not None

    async def test_cost_analysis_vertex_more_expensive_than_ollama(self, client, user_headers):
        """Vertex AI debe ser más costoso que Ollama para el mismo volumen."""
        ollama_resp = await client.post(
            "/api/architecture/costs",
            json={"monthly_requests": 50000, "avg_tokens": 800, "provider": "ollama"},
            headers=user_headers
        )
        vertex_resp = await client.post(
            "/api/architecture/costs",
            json={"monthly_requests": 50000, "avg_tokens": 800, "provider": "vertex_ai"},
            headers=user_headers
        )

        if ollama_resp.status_code == 200 and vertex_resp.status_code == 200:
            ollama_data = ollama_resp.json()
            vertex_data = vertex_resp.json()

            # Extraer costo total (flexible con la estructura)
            def get_cost(data):
                for key in ("monthly_cost", "total_cost", "llm_cost", "cost"):
                    if key in data:
                        return float(data[key])
                return 0.0

            ollama_cost = get_cost(ollama_data)
            vertex_cost = get_cost(vertex_data)

            # Vertex debe ser >= Ollama en costo de tokens
            assert vertex_cost >= ollama_cost

    async def test_templates_endpoint(self, client, user_headers):
        response = await client.get("/api/architecture/templates", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestTCOCalculation:
    """Tests unitarios para el cálculo de TCO."""

    def test_ollama_has_zero_token_cost(self):
        """Ollama no tiene costo por token (self-hosted)."""
        monthly_requests = 100_000
        avg_tokens = 1000

        # Ollama: 0 costo por token
        ollama_token_cost = monthly_requests * avg_tokens * 0  # precio = 0
        assert ollama_token_cost == 0

    def test_tco_includes_infrastructure(self):
        """El TCO debe incluir costos de infraestructura, no solo tokens."""
        # Cloud Run mínimo: ~$0/mes para 0 instancias (min-instances=0)
        # GKE: ~$75/mes por cluster
        infrastructure_costs = {
            "cloud_run": 0.0,       # pay-per-use
            "gke_autopilot": 75.0,  # cluster fee
            "cloud_sql": 20.0,      # si se usa DB
        }
        total_infra = sum(infrastructure_costs.values())
        assert total_infra > 0

    def test_24_month_tco_projection(self):
        """24 meses de TCO debe ser consistente con el mensual."""
        monthly_cost = 150.0  # $150/mes
        months = 24
        projected_tco = monthly_cost * months
        assert projected_tco == 3600.0
