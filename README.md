# Helios IQ AI

Helios IQ is an AI Workforce Operating System designed for businesses that want to deploy specialized AI employees to handle professional work across research, content, analytics, automation, and operations.

## Product vision

Helios IQ brings together multiple AI employees in a single operating system so teams can manage work, automate tasks, and use knowledge from company documents and structured data.

## MVP scope

Phase 1 focuses on the foundation required to support the future AI workforce platform:

- secure app foundation
- workspace and organization architecture
- authentication-ready backend
- modular AI agent structure
- PostgreSQL-ready architecture
- FastAPI foundation
- Next.js product shell
- development environment and Docker setup

## Tech stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui-compatible structure
- Lucide icons

### Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy-ready architecture

### Data
- PostgreSQL
- pgvector-ready schema
- Redis for async jobs and caching

## Project structure

```text
Helios-IQ/
├── apps/
│   ├── web/
│   └── api/
├── packages/
│   ├── ui/
│   ├── config/
│   └── types/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
└── package.json
```

## Environment setup

1. Copy `.env.example` to `.env`.
2. Update the values for your local development environment.
3. Keep secrets out of source control.

## Running the frontend

```bash
cd apps/web
npm install
npm run dev
```

Frontend runs on: http://localhost:3000

## Running the backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs on: http://localhost:8000

## Health check

```bash
curl http://localhost:8000/api/health
```

## Current MVP focus

The first Phase 1 implementation includes:

- workspace and authentication-ready architecture
- base SaaS UI shell
- modular API foundation
- database schema planning
- AI provider and agent registry scaffold
- health endpoint and environment configuration

## Roadmap

### Phase 1
- platform foundation
- auth/workspace architecture
- base web shell
- API foundation
- AI agent scaffolding

### Phase 2
- RAG knowledge base
- document ingestion
- first AI agents
- execution history
- chat system

### Phase 3
- command center
- workflow automation
- analytics dashboard
- integrations

## Notes

This foundation is intentionally designed for future growth and production architecture without overbuilding the MVP prematurely.
