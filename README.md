# TravelCraft AI

<div align="center">

**A Premium AI-Powered Trip Planning Application**

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Node.js](https://img.shields.io/badge/node.js-18+-green)

</div>

## 📋 Overview

TravelCraft AI is a sophisticated full-stack application that leverages artificial intelligence to generate personalized travel itineraries. Users can create accounts, plan trips, store memories, and access AI-powered destination recommendations based on real-time web data.

## ✨ Features

- **User Authentication**: Secure email/password authentication with HTTP-only cookies
- **Trip Generation**: AI-powered itinerary generation using OpenAI
- **Destination Research**: Live web scraping for current destination information via Firecrawl
- **Trip Management**: Full CRUD operations for trip planning and storage
- **Memory Bank**: Store and manage travel memories and preferences
- **Real-time Exchange Rates**: Currency conversion for international travel planning
- **Responsive UI**: Modern, animated interface with real-time interactions

## 🛠️ Technology Stack

### Frontend

- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS 3
- **Animation**: Framer Motion, GSAP, Three.js
- **Routing**: React Router v6
- **Testing**: Vitest + React Testing Library

### Backend

- **Framework**: FastAPI 0.115
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT with bcrypt hashing
- **Migration Tool**: Alembic
- **External APIs**: OpenAI, Firecrawl
- **Testing**: pytest

## 📦 Prerequisites

Ensure you have the following installed on your system:

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **PostgreSQL**: 12 or higher
- **Git**: For version control

## 🚀 Installation & Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd trip_planner
```

### 2. Backend Setup

#### Create Virtual Environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### Install Dependencies

```powershell
pip install -r requirements.txt
```

#### Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Update `backend/.env` with your configuration:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Firecrawl Configuration
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# Application URLs
FRONTEND_ORIGIN=http://localhost:5173
BACKEND_ORIGIN=http://localhost:8000

# Database Configuration
DATABASE_URL=postgresql+psycopg://travelcraft:travelcraft@localhost:5432/travelcraft_ai

# Authentication
JWT_SECRET_KEY=your-long-random-secret-key-min-32-characters
AUTH_COOKIE_NAME=travelcraft_session
AUTH_COOKIE_SECURE=false
AUTH_TOKEN_EXPIRE_HOURS=168
```

#### Database Setup

```powershell
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE travelcraft_ai;"

# Run migrations
cd backend
alembic upgrade head
```

#### Start Backend Server

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend will be available at `http://localhost:8000`

### 3. Frontend Setup

#### Install Dependencies

```powershell
cd frontend
npm install
```

#### Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Update `frontend/.env` with:

```env
VITE_API_BASE_URL=http://localhost:8000
```

#### Start Development Server

```powershell
npm run dev
```

Frontend will be available at `http://localhost:5173`

## 📁 Project Structure

```
trip_planner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration management
│   │   ├── database.py             # Database connection setup
│   │   ├── db_models.py            # SQLAlchemy ORM models
│   │   ├── models.py               # Pydantic request/response models
│   │   ├── security.py             # Authentication & authorization
│   │   ├── services/
│   │   │   ├── auth_service.py     # User authentication logic
│   │   │   ├── destination_service.py
│   │   │   ├── exchange_rate_service.py
│   │   │   ├── firecrawl_service.py
│   │   │   ├── llm_service.py      # OpenAI integration
│   │   │   ├── memory_service.py
│   │   │   └── planner_service.py
│   │   └── data/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/               # Database migration files
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth_service.py
│   │   ├── test_exchange_rate_service.py
│   │   ├── test_firecrawl_service.py
│   │   └── test_llm_service.py
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   └── run_backend.bat
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── auth/               # Authentication components
│   │   │   ├── shell/              # App shell & layout
│   │   │   └── ui/                 # Reusable UI components
│   │   ├── pages/                  # Page components
│   │   ├── state/                  # Context & state management
│   │   ├── lib/
│   │   │   ├── api.js              # API client
│   │   │   └── currency.js
│   │   └── test/
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── run_frontend_tests.bat
├── pytest.ini
└── README.md
```

## 🧪 Testing

### Backend Tests

```powershell
cd backend
pytest                    # Run all tests
pytest -v               # Verbose output
pytest --cov           # With coverage report
```

### Frontend Tests

```powershell
cd frontend
npm run test            # Run tests
```

## 📝 Database Migrations

### Create New Migration

```powershell
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```powershell
alembic upgrade head
```

### Rollback Migration

```powershell
alembic downgrade -1
```

## 🔐 Environment Configuration

| Variable                  | Description                         | Example                  |
| ------------------------- | ----------------------------------- | ------------------------ |
| `OPENAI_API_KEY`          | OpenAI API credentials              | sk-...                   |
| `FIRECRAWL_API_KEY`       | Firecrawl API credentials           | fc-...                   |
| `DATABASE_URL`            | PostgreSQL connection string        | postgresql+psycopg://... |
| `JWT_SECRET_KEY`          | Secret for JWT token signing        | (32+ characters)         |
| `AUTH_COOKIE_SECURE`      | Enable secure cookies in production | true                     |
| `AUTH_TOKEN_EXPIRE_HOURS` | Session expiration time             | 168                      |

## 🚢 Deployment

### Backend Deployment Checklist

- [ ] Set `AUTH_COOKIE_SECURE=true` for HTTPS
- [ ] Use strong `JWT_SECRET_KEY` (32+ characters)
- [ ] Configure production PostgreSQL URL
- [ ] Set appropriate `CORS_ORIGINS`
- [ ] Enable HTTPS on frontend and backend
- [ ] Configure environment-specific API keys

### Frontend Build

```powershell
cd frontend
npm run build          # Creates optimized production build
npm run preview        # Preview production build locally
```

## 📚 API Documentation

Once the backend is running, visit:

```
http://localhost:8000/docs          # Interactive API docs (Swagger UI)
http://localhost:8000/redoc         # Alternative API docs (ReDoc)
```

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add new feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👥 Support

For issues or questions, please open a GitHub issue or contact the development team.

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
