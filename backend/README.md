# Flask Backend — Layered (Services / Blueprints / Routes)

This is a minimal Flask backend with folders split by responsibility:
- **services/**: business logic (pure functions/classes; no Flask imports)
- **routes/**: endpoint functions (no app object here)
- **blueprints/**: blueprint instances that wire routes to a Blueprint

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
flask run
# or:
python app.py
```

## Layout
```
flask-backend-layered/
├─ app.py                   # app factory & server entrypoint
├─ config.py                # simple config classes
├─ blueprints/
│  ├─ __init__.py
│  └─ api.py               # defines api_bp and registers route modules
├─ routes/
│  ├─ __init__.py
│  └─ health_routes.py     # defines endpoints and attaches to a provided Blueprint
├─ services/
│  ├─ __init__.py
│  └─ health_service.py    # business logic used by routes
├─ tests/
│  └─ test_health.py
├─ .flaskenv
├─ .env.example
├─ requirements.txt
└─ .gitignore
```
