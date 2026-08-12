# JanSahay AI

JanSahay AI is a full-stack multilingual AI-powered web application that helps farmers discover relevant government welfare schemes through personalized, explainable recommendations.

This repository follows the architecture and phased development plan defined in [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md).

## Current Phase

**Phase 6 — RAG / Government Scheme Knowledge Base**

Phase 6 adds a basic retrieval-augmented generation pipeline:

- PDF ingestion from `backend/data/documents/`
- Text extraction and chunking
- Gemini embeddings (`gemini-embedding-001`)
- Qdrant vector storage and semantic retrieval
- Grounded answers in the existing `/assistant` flow

Phase 4 deterministic eligibility and Phase 5 assistant behavior remain authoritative. RAG provides supporting document context only.

## Technology Stack

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- React Router
- Axios

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic Settings
- JWT (`python-jose`)
- Password hashing (`passlib` + `bcrypt`)
- Google Gemini (`google-genai`)
- Qdrant (`qdrant-client`)
- PDF parsing (`pypdf`)

### Infrastructure

- Docker
- Docker Compose
- Qdrant vector database

## Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development without Docker)
- Python 3.11+ (for local backend development without Docker)

## Local Development

### 1. Environment setup

Copy the example environment file:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Set a development `ADMIN_PASSWORD` in `.env` before creating the admin account.

### 2. Run with Docker Compose

```bash
docker compose up --build
```

### 3. Run Alembic migrations

```bash
docker compose exec backend alembic upgrade head
```

Expected head:

```text
0004_create_schemes
```

### 4. Create the development admin account

Admin accounts cannot be created through public registration.

From the backend container:

```bash
docker compose exec backend python -m scripts.create_admin
```

### 5. Seed development sample schemes

```bash
docker compose exec backend python -m scripts.seed_schemes
```

These are **development sample records**, not official government integrations.

### 6. Access the application

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Authentication Endpoints

- `POST /api/auth/register` — farmer registration only
- `POST /api/auth/login` — farmer or admin login
- `GET /api/auth/me` — current authenticated user
- `GET /api/auth/test/farmer` — development RBAC test (farmer only)
- `GET /api/auth/test/admin` — development RBAC test (admin only)

## Farmer Profile Endpoints (Phase 3)

- `GET /api/profile` — get authenticated farmer profile
- `POST /api/profile` — create farmer profile
- `PUT /api/profile` — update farmer profile
- `GET /api/profile/completion` — profile completion percentage

## Scheme Endpoints (Phase 4)

- `GET /api/schemes` — list active schemes (authenticated; supports `search`, `state`, `scheme_type`)
- `GET /api/schemes/{scheme_id}` — scheme details (authenticated)
- `GET /api/schemes/{scheme_id}/eligibility` — farmer-only eligibility check using JWT profile
- `GET /api/schemes/recommendations` — farmer-only profile-based recommendations

## Assistant Endpoint (Phase 5)

- `POST /api/assistant/chat` — authenticated conversational assistant (farmer profile context for farmers only)

Set `GEMINI_API_KEY` in `.env` to enable the assistant. If missing, the app remains functional and returns a controlled configuration error.

## RAG Endpoints (Phase 6)

- `POST /api/rag/search` — authenticated semantic document search (`query`, `top_k`)

## RAG Ingestion (Phase 6)

Place development PDFs in `backend/data/documents/`, then run:

```bash
docker compose exec backend python -m scripts.ingest_documents
```

Requires `GEMINI_API_KEY` for embedding generation and a running Qdrant service.

Environment:

- `QDRANT_URL=http://qdrant:6333`
- `QDRANT_COLLECTION_NAME=jansahay_documents`
- `EMBEDDING_MODEL=gemini-embedding-001`

## Frontend Routes

- `/` — public home
- `/login` — login
- `/register` — farmer registration
- `/dashboard` — protected dashboard (farmer or admin)
- `/profile` — farmer-only profile management
- `/schemes` — farmer-only scheme listing with search/filter
- `/schemes/:id` — farmer-only scheme details and eligibility check
- `/assistant` — farmer-only AI scheme assistant

## Backend Health Endpoint

`GET /api/health`

Example healthy response:

```json
{
  "status": "ok",
  "database": "connected"
}
```

## Current Features

- Phase 1 foundation (FastAPI, PostgreSQL, React, Docker)
- Phase 2 authentication and RBAC (`farmer`, `admin`)
- Phase 3 farmer profile CRUD and completion tracking
- Phase 4 government scheme discovery, eligibility, and profile-based recommendations
- Phase 5 Gemini-powered scheme assistant with controlled context
- Phase 6 RAG pipeline with Qdrant-backed document retrieval
- Deterministic eligibility engine with explainable reasons
- Development scheme seed script with sample eligibility criteria
- Farmer dashboard recommendations section
- Farmer schemes browse and detail pages

## Phase 6 Limitations

- Development/local PDF documents only (no admin upload UI)
- No Neo4j, GraphRAG, or knowledge graphs
- No persistent chat history storage
- No voice input/output
- Ingestion is script-based, not an admin API

## Phase 5 Limitations

- No persistent chat history storage
- No voice input/output
- Gemini explains Phase 4 deterministic results but does not replace them
- Admin users can use the assistant API for general scheme questions without farmer profile context

## Phase 4 Limitations

- Scheme data is development/sample data unless explicitly sourced from official integrations
- Eligibility and recommendations are rule-based and deterministic (not AI/LLM generated)
- No admin scheme management UI yet
- No external government API integration
- No voice, chatbot, vector search, graph database, or multi-agent orchestration

## Features Intentionally Not Implemented Yet

The following belong to later phases:

- Voice/STT/TTS (Phase 6+)
- Gemini and multi-agent architecture
- Qdrant vector search
- Neo4j graph database
- GraphRAG
- Document ingestion
- Admin scheme management UI
- Conversational chatbot
- External government API integrations
- Notifications and payment systems

See [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) for the full roadmap.

## Project Documentation

- [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)

## Running Tests

From the backend container:

```bash
docker compose exec backend pytest -q
```

Or locally from the `backend/` directory:

```bash
pip install -r requirements.txt
pytest -q
```

Expected: all Phase 1–4 tests pass (including the original 27 tests plus new scheme tests).

## Database Migration Notes

Phase 4 adds:

- `government_schemes`
- `scheme_eligibility_criteria`

To verify migration state:

```bash
docker compose exec backend alembic current
```

To test downgrade/upgrade:

```bash
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic upgrade head
```
