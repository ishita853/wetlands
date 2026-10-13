# Backend — Indian Ramsar Wetlands Monitoring Portal

FastAPI + SQLAlchemy 2 + PostGIS-ready API.

See the [repository root README](../README.md) for full setup instructions,
environment variables, and the overall project structure.

```bash
python -m venv .venv
./.venv/Scripts/activate      # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload   # http://localhost:8000
```

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Lint/format: `ruff check .` / `ruff format .`
- Tests: `pytest`
- Migrations: `alembic revision --autogenerate -m "..."` / `alembic upgrade head`
