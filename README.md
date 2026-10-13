# Indian Ramsar Wetlands Climate & Environment Monitoring Portal

Monorepo containing the public portal (Next.js) and API (FastAPI) for
monitoring India's Ramsar wetlands: climate indicators, water quality, and
dataset management.

> **Status:** the public portal (Ramsar Site explorer, site profiles, analysis,
> climate theme pages) and the administration area (sign-in, dataset upload,
> validation and publishing) are working. Climate indicator values appear once
> the project team uploads them; nothing is estimated. Water-quality
> monitoring (Sentinel Hub) is not built yet.

## Repository layout

```
frontend/   Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
backend/    FastAPI + SQLAlchemy 2 + Alembic + PostGIS-ready models
docker-compose.yml   Local dev stack: frontend, backend, PostGIS, Redis
```

See `frontend/` and `backend/` for their own structure; both are documented
inline via placeholder modules and TODO comments marking future work.

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- PostgreSQL with PostGIS (via Docker, or a local install)
- Redis (via Docker, or a local install)
- Docker + Docker Compose (optional, for the full local stack)

## Getting started

### 1. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev       # http://localhost:3000
```

Other scripts: `npm run build`, `npm run lint`, `npm run typecheck`, `npm run format`.

### 2. Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate      # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload   # http://localhost:8000
```

Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`.
Interactive API docs: `http://localhost:8000/docs`.

Backend dev tooling:

```bash
ruff check .        # lint
ruff format .       # format
pytest              # tests
```

### 3. Database migrations (Alembic)

Requires a running PostgreSQL/PostGIS instance (see Docker section below).

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### 4. Full local stack (Docker Compose)

```bash
docker compose up --build
```

This starts PostgreSQL/PostGIS, Redis, the backend (`:8000`), and the
frontend (`:3000`). No Copernicus/Earth Engine credentials are required to
start the stack locally.

## Administration and dataset uploads

The admin area is at `/admin/login` (header link **Admin Login**).

1. **First sign-in:** the backend creates one administrator on startup while
   there are no users, from `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`
   (`admin` / `admin@wetlands`, as set in the project brief). That password
   only works to set a new one: every other page and API call is refused
   until it is changed, and it cannot be reused. Changing a password signs out
   all other sessions.
2. **Uploading:** *Upload dataset* takes one JSON file per climate theme, in
   the format described in `frontend/data/climate/README.md`. The file is
   checked (theme, years, official Ramsar Site numbers, one value per year) and
   either published straight away or rejected with a list of problems.
3. **History and rollback:** *Datasets* lists every upload, including rejected
   ones. Any valid version can be published again, which is also how you roll
   back; *Unpublish* returns a theme page to "dataset not yet loaded".

Security details: passwords are hashed with bcrypt; after
`LOGIN_MAX_ATTEMPTS` (5) failed attempts the account is locked for
`LOGIN_LOCKOUT_MINUTES` (15); the session token is kept in an httpOnly
cookie and never reaches browser scripts. Set a strong random `JWT_SECRET`
before deploying — the backend refuses to start in production without one.

**Running it locally without Docker:** `backend/.env` can use
`DATABASE_URL=sqlite:///./dev.db` (accounts and dataset history only). Start
the backend (`uvicorn app.main:app --reload`) and the frontend (`npm run dev`);
published files are written to `frontend/data/climate/`, which the site reads
directly.

## Environment variables

Copy `frontend/.env.example` → `frontend/.env.local` and
`backend/.env.example` → `backend/.env` and fill in real values before
deploying. Never commit real secrets. Notably:

- `COPERNICUS_CLIENT_ID` / `COPERNICUS_CLIENT_SECRET` — Copernicus Data
  Space / Sentinel Hub credentials (backend only; never exposed to the
  frontend).
- `EARTH_ENGINE_PROJECT` — reserved for the future Google Earth Engine
  integration.
- `S3_*` — S3-compatible object storage for uploaded/processed datasets.
- `JWT_SECRET` — replace the development placeholder before deploying.
- `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` — first administrator
  (created only while there are no users; must be changed at first sign-in).
- `CLIMATE_PUBLISH_DIR` (backend) and `CLIMATE_DATA_DIR` (frontend) — must
  point at the same folder so published datasets appear on the site. Docker
  Compose shares it as the `climate_data` volume.
- `API_URL` (frontend) — server-side backend address (`http://backend:8000` in
  Docker).

## Tech stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui,
Lucide React, MapLibre GL JS, deck.gl, Apache ECharts, React Hook Form,
Zod, TanStack Query.

**Backend:** FastAPI, Pydantic, SQLAlchemy 2, Alembic, psycopg,
GeoAlchemy2, GeoPandas, Shapely, Rasterio, xarray, netCDF4, Celery, Redis.

**Database:** PostgreSQL + PostGIS.
