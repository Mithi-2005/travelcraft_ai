# TravelCraft AI

TravelCraft AI is a premium full-stack trip planner built with:

- React + Vite + Tailwind + Framer Motion + GSAP + Three.js
- FastAPI for backend APIs
- Firecrawl for live destination research
- OpenAI for itinerary generation
- PostgreSQL + SQLAlchemy + Alembic for persistent user data
- HTTP-only cookie authentication for local development

## What Changed

The app now supports:

- full core email/password auth
- protected dashboard, generator, memory, and trip detail routes
- PostgreSQL-backed user profiles and trip history
- per-user memory and generated trips instead of the old JSON-only single-user store

The legacy `backend/app/data/memento.json` remains as reference/demo data only and is no longer the active persistence path.

## Folder Structure

```text
GENAI-1/
|-- backend/
|   |-- .env.example
|   |-- alembic.ini
|   |-- requirements.txt
|   |-- alembic/
|   |   `-- versions/
|   `-- app/
|       |-- config.py
|       |-- database.py
|       |-- db_models.py
|       |-- main.py
|       |-- models.py
|       |-- security.py
|       `-- services/
|           |-- auth_service.py
|           |-- firecrawl_service.py
|           |-- llm_service.py
|           |-- memory_service.py
|           `-- planner_service.py
|-- frontend/
|   |-- .env.example
|   `-- src/
|       |-- App.jsx
|       |-- lib/api.js
|       |-- state/
|       |-- components/
|       `-- pages/
`-- README.md
```

## Backend Setup

1. Create and activate the virtual environment:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy the backend env template:

```powershell
Copy-Item .env.example .env
```

4. Fill `backend/.env` with local values:

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
FIRECRAWL_API_KEY=your_firecrawl_key
FRONTEND_ORIGIN=http://localhost:5173
BACKEND_ORIGIN=http://localhost:8000
DATABASE_URL=postgresql+psycopg://travelcraft:travelcraft@localhost:5432/travelcraft_ai
JWT_SECRET_KEY=replace-with-a-long-random-secret
AUTH_COOKIE_NAME=travelcraft_session
AUTH_COOKIE_SECURE=false
AUTH_TOKEN_EXPIRE_HOURS=168
```

5. Create a local PostgreSQL database:

```sql
CREATE DATABASE travelcraft_ai;
```

6. Run migrations:

```powershell
alembic upgrade head
```

7. Start the backend:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

1. Install dependencies:

```powershell
cd frontend
npm install
```

2. Copy the frontend env template if needed:

```powershell
Copy-Item .env.example .env
```

3. Make sure `frontend/.env` uses `localhost`, not `127.0.0.1`:

```env
VITE_API_URL=http://localhost:8000
```

4. Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:5173`.

## Auth API

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

## App API

- `GET /health`
- `GET /user-memory`
- `POST /update-memory`
- `POST /generate-trip`

All app data endpoints require an authenticated cookie session.

## Local Dev Notes

- Use `localhost` consistently for both frontend and backend to avoid cookie/session issues.
- The backend stores auth in an HTTP-only cookie with `SameSite=Lax`.
- The backend packages for PostgreSQL/auth must be installed in `backend/.venv` before runtime checks will pass.
- Firecrawl can run live independently of OpenAI; if OpenAI quota is unavailable, itinerary generation will still fall back and report that state in the UI.

## Verification Checklist

1. `http://localhost:8000/health` returns `{"status":"ok"}`.
2. Register a new user from the UI.
3. Refresh the page and confirm the session is restored.
4. Open dashboard, generator, and memory without being redirected.
5. Log out and confirm protected routes redirect back to `/login`.
6. Run `alembic upgrade head` on a fresh database and verify the schema builds cleanly.

## Reference Sources Used For Integration Patterns

- Firecrawl Search docs: https://docs.firecrawl.dev/features/search
- Firecrawl Extract docs: https://docs.firecrawl.dev/features/extract
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses/create
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
