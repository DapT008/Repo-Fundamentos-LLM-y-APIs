# ============================================================
# Sesión 3 · LLM Security Lab — Makefile
# ============================================================
# Uso:
#   make setup      → configurar entorno por primera vez
#   make backend    → levantar FastAPI en http://localhost:8000/docs
#   make frontend   → levantar React en http://localhost:5173
#   make test       → correr pruebas (sin Ollama)
#   make labs       → ejecutar todos los labs en secuencia
#   make simulado   → Ollama simulado (sin GPU)
#   make docker     → levantar todo con Docker
#   make clean      → limpiar archivos temporales
# ============================================================

PYTHON   := python3.12
PIP      := $(PYTHON) -m pip
VENV     := .venv
ACTIVATE := source $(VENV)/bin/activate

.PHONY: setup backend frontend test labs lab09 lab10 lab11 lab12 lab13 lab14 \
        simulado docker docker-down clean help

# ─── Configuración inicial ───────────────────────────────────────────────────

setup:
	@echo "── Creando entorno virtual con Python 3.12 ──"
	$(PYTHON) -m venv $(VENV)
	@echo "── Instalando dependencias del backend ──"
	$(ACTIVATE) && pip install -r requirements.txt --break-system-packages 2>/dev/null || \
	$(ACTIVATE) && pip install -r requirements.txt
	@echo "── Creando backend/.env desde .env.example ──"
	@test -f backend/.env || cp backend/.env.example backend/.env
	@echo "── Instalando dependencias del frontend ──"
	@command -v node >/dev/null 2>&1 || (echo "⚠️  Node.js no encontrado. Instala Node 22+" && exit 1)
	cd frontend && npm install
	@echo ""
	@echo "✅ Setup completo. Ahora puedes:"
	@echo "   make backend    → terminal 1"
	@echo "   make frontend   → terminal 2"

# ─── Servicios ───────────────────────────────────────────────────────────────

backend:
	@echo "── Iniciando FastAPI en http://localhost:8000/docs ──"
	@test -f $(VENV)/bin/activate || (echo "⚠️  Ejecuta 'make setup' primero" && exit 1)
	cd backend && $(ACTIVATE) && uvicorn app.main:app --reload --port 8000

frontend:
	@echo "── Iniciando React en http://localhost:5173 ──"
	@test -d frontend/node_modules || (echo "⚠️  Ejecuta 'make setup' primero" && exit 1)
	cd frontend && npm run dev

simulado:
	@echo "── Iniciando Ollama simulado (sin GPU) en puerto 11434 ──"
	@$(ACTIVATE) && $(PYTHON) scripts/ollama_simulado.py

docker:
	@echo "── Levantando servicios con Docker Compose ──"
	docker compose up -d --build
	@echo "✅ Servicios disponibles:"
	@echo "   Frontend:  http://localhost:8080"
	@echo "   Backend:   http://localhost:8000/docs"
	@echo "   Ollama:    http://localhost:11434"

docker-down:
	docker compose down

# ─── Tests ───────────────────────────────────────────────────────────────────

test:
	@echo "── Ejecutando pruebas ──"
	cd backend && $(ACTIVATE) && pytest tests/ -v --cov=app --cov-report=term-missing

# ─── Labs ────────────────────────────────────────────────────────────────────

labs: lab09 lab10 lab11 lab12 lab13 lab14

lab09:
	@echo "── Lab 09 · Autenticación JWT ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/09_autenticacion_jwt.py

lab10:
	@echo "── Lab 10 · Rate Limiting y WAF ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/10_rate_limiting_y_waf.py

lab11:
	@echo "── Lab 11 · Alta Disponibilidad ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/11_alta_disponibilidad.py

lab12:
	@echo "── Lab 12 · Monitoreo y Logging ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/12_monitoreo_y_logging.py

lab13:
	@echo "── Lab 13 · Diseño Arquitectónico ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/13_diseno_arquitectonico.py

lab14:
	@echo "── Lab 14 · Análisis de Costos ──"
	$(ACTIVATE) && $(PYTHON) labs/sesion3/14_analisis_costos_proyecto.py

# ─── Limpieza ────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/logs/*.jsonl 2>/dev/null || true
	rm -rf backend/llm_security_lab.db 2>/dev/null || true
	@echo "✅ Limpieza completa"

# ─── Ayuda ───────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Sesión 3 · LLM Security Lab"
	@echo "════════════════════════════"
	@echo "  make setup     Configurar entorno (primera vez)"
	@echo "  make backend   Levantar FastAPI (puerto 8000)"
	@echo "  make frontend  Levantar React (puerto 5173)"
	@echo "  make simulado  Ollama simulado sin GPU (puerto 11434)"
	@echo "  make test      Ejecutar pruebas unitarias"
	@echo "  make labs      Ejecutar todos los labs en secuencia"
	@echo "  make lab09     Lab 09 · JWT y Autenticación"
	@echo "  make lab10     Lab 10 · Rate Limiting y WAF"
	@echo "  make lab11     Lab 11 · Alta Disponibilidad"
	@echo "  make lab12     Lab 12 · Monitoreo y Logging"
	@echo "  make lab13     Lab 13 · Diseño Arquitectónico"
	@echo "  make lab14     Lab 14 · Análisis de Costos"
	@echo "  make docker    Docker Compose: todo en un comando"
	@echo "  make clean     Limpiar archivos temporales"
	@echo ""
