# C4 Model — {Nombre del Sistema}

**Versión**: 1.0  
**Fecha**: {YYYY-MM-DD}  
**Autores**: {Nombre(s)}

---

## Nivel 1: System Context (Contexto del Sistema)

> ¿Qué hace el sistema? ¿Quién lo usa? ¿Con qué sistemas externos se conecta?

```
                    ┌──────────────────────────────────┐
                    │          Tu Sistema              │
                    │                                  │
   [Usuario Final]──►   {Nombre del sistema}          │
                    │   {Descripción breve}            │
   [Admin/Ops] ────►                                  │
                    └──────────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
      [{Sistema Externo A}] [{Sistema Externo B}] [{Sistema Externo C}]
      {Descripción}         {Descripción}         {Descripción}
```

### Personas (Usuarios)

| Persona | Descripción | Necesidades principales |
|---------|-------------|------------------------|
| {Usuario 1} | {Descripción} | {Necesidades} |
| {Usuario 2} | {Descripción} | {Necesidades} |

### Sistemas Externos

| Sistema | Tipo | Relación |
|---------|------|----------|
| {Sistema A} | {SaaS/API/DB} | {Descripción de la relación} |
| {Sistema B} | {SaaS/API/DB} | {Descripción de la relación} |

---

## Nivel 2: Containers (Contenedores)

> ¿Cuáles son las partes desplegables del sistema? ¿Cómo se comunican?

```
┌─────────────────────────────────────────────────────────────┐
│                       {Nombre del Sistema}                   │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  {Container} │    │  {Container} │    │  {Container} │  │
│  │              │───►│              │───►│              │  │
│  │  {Tech}      │    │  {Tech}      │    │  {Tech}      │  │
│  │  {Puerto}    │    │  {Puerto}    │    │  {Puerto}    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │  {Container} │    │  {Container} │                      │
│  │  {Tech}      │    │  {Tech}      │                      │
│  └──────────────┘    └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Descripción de Contenedores

| Container | Tecnología | Responsabilidad | Puerto |
|-----------|-----------|-----------------|--------|
| {Nombre} | {Tech stack} | {Qué hace} | {Puerto} |
| {Nombre} | {Tech stack} | {Qué hace} | {Puerto} |

### Comunicación entre Contenedores

| De | A | Protocolo | Descripción |
|----|---|-----------|-------------|
| {Container A} | {Container B} | {HTTP/gRPC/TCP} | {Descripción} |

---

## Nivel 3: Components (Componentes)

> ¿Cuáles son los componentes principales dentro de cada contenedor?

### Container: {Nombre del Container A}

```
{Container A}
├── {Componente 1}    ← {Descripción breve}
├── {Componente 2}    ← {Descripción breve}
│   ├── {Sub-componente}
│   └── {Sub-componente}
└── {Componente N}    ← {Descripción breve}
```

| Componente | Tecnología | Responsabilidad |
|-----------|-----------|-----------------|
| {Nombre} | {Tech} | {Qué hace} |

---

## Decisiones de Diseño

> Decisiones importantes que influyeron en esta arquitectura.

| Decisión | Razón | ADR |
|----------|-------|-----|
| {Decisión 1} | {Razón} | ADR-{NNN} |
| {Decisión 2} | {Razón} | ADR-{NNN} |

---

## Evolución Futura (Nivel 4)

> Áreas donde se planea hacer zoom adicional (diagramas de código/secuencia).

- [ ] Diagrama de secuencia: {flujo crítico 1}
- [ ] Diagrama de clase: {componente complejo}

---

*Plantilla C4 Model v1.0 · Sesión 3 · Maestría BSG*  
*Referencia: https://c4model.com/*
