# GCP Agent Platform — Tres Enfoques

Comparación práctica de cómo desplegar un agente de IA en Google Cloud Platform,
desde el nivel cero (consola web) hasta integración avanzada con ADK.

## Resumen de los tres enfoques

| Aspecto | Parte 1: Consola | Parte 2: ADK + Cloud Run | Parte 3: Docker sin ADK |
|---------|-----------------|--------------------------|-------------------------|
| **Código requerido** | Ninguno | Python (ADK) | Python (FastAPI) |
| **Despliegue** | Clic en UI | Cloud Build → Cloud Run | Docker → Cloud Run |
| **Flexibilidad** | Baja | Alta | Total |
| **Curva aprendizaje** | Mínima | Media | Media-alta |
| **Casos de uso** | Demos, prototipos rápidos | Agentes con herramientas | APIs personalizadas |
| **Costo estimado** | ~$0 (free tier) | ~$5–20/mes | ~$5–20/mes |
| **Tiempo setup** | 10 minutos | 30–60 minutos | 30–60 minutos |

## Estructura

```
gcp-agent-platform/
├── README.md                    ← Este archivo
├── parte1_consola/
│   └── README.md               ← Guía paso a paso (sin código)
├── parte2_adk/
│   ├── agent.py                ← Agente con Google ADK
│   ├── requirements.txt        ← Dependencias
│   ├── Dockerfile              ← Contenedor para Cloud Run
│   └── cloudbuild.yaml         ← CI/CD con Cloud Build
└── parte3_docker_sin_adk/
    ├── main.py                 ← FastAPI + Vertex AI directo
    ├── requirements.txt        ← Dependencias
    ├── Dockerfile              ← Contenedor para Cloud Run
    └── cloudbuild.yaml         ← CI/CD con Cloud Build
```

## Prerrequisitos comunes

```bash
# Instalar gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Autenticarse
gcloud auth login
gcloud auth application-default login

# Configurar proyecto
export PROJECT_ID="tu-proyecto-gcp"
gcloud config set project $PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

## Cuándo usar cada enfoque

**Parte 1 (Consola)**: Prototipado rápido, demos a clientes, exploración de capacidades
sin comprometer código de producción.

**Parte 2 (ADK)**: Agentes complejos con múltiples herramientas, memoria de sesión,
orquestación de sub-agentes. El ADK maneja el loop de razonamiento automáticamente.

**Parte 3 (Docker sin ADK)**: Control total sobre el sistema prompt, integración con
APIs propias, o cuando el ADK añade complejidad innecesaria para casos simples.
