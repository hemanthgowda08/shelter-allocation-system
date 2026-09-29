# Emergency Shelter Allocation Platform — 50% Milestone

**PRJ_525 · Optimization + Web/API + Persistence prototype**

## What is implemented

This milestone converts the original standalone optimization engine into a runnable end-to-end prototype:

- Existing integer-programming shelter allocation engine using **PuLP + HiGHS** (CBC fallback).
- Priority-aware allocation, shelter capacity, availability and facility eligibility constraints.
- Flask REST API around the optimization engine.
- SQLite persistence for affected groups, shelters and optimization runs.
- Browser dashboard for viewing the scenario and running optimization.
- Configurable travel and utilization-balance weights.
- Allocation result table and shelter-utilization dashboard.
- Optimization run history stored in the database.
- Automatic Haversine distance calculation from stored coordinates.
- Seeded synthetic scenario so the application works immediately after installation.

## What is intentionally still future work

This is a **50% milestone**, not the final production system. The following are not claimed as complete:

- React/Tailwind production frontend (the current UI is a lightweight HTML/CSS/JS milestone UI).
- PostgreSQL production deployment (SQLite is used locally for zero-configuration execution).
- Authentication and role-based authorization.
- Leaflet/Google Maps production GIS integration and road-network routing.
- Live disaster/population data feeds.
- AI/ML demand forecasting or dynamic prediction.
- Real emergency-management/government integration.
- Production deployment, monitoring and security hardening.

## Run locally

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the application

```bash
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

The first startup automatically creates `data/shelter.db` and seeds the deterministic synthetic scenario if the database is empty.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service health check |
| GET | `/api/groups` | List affected groups |
| POST | `/api/groups` | Add an affected group |
| GET | `/api/shelters` | List shelters |
| POST | `/api/shelters` | Add a shelter |
| PATCH | `/api/shelters/<id>/status` | Change shelter availability |
| POST | `/api/optimize` | Run the allocation optimizer |
| GET | `/api/runs` | List previous optimization runs |
| GET | `/api/runs/<id>` | Retrieve one saved optimization run |

## Important data note

The default scenario is **synthetic demonstration data**. It must not be represented as real disaster data or evidence of real-world emergency performance.

## Project architecture at this milestone

```text
Browser Dashboard
      |
      v
   Flask API
      |
      +------ SQLite persistence
      |
      v
Scenario + Distance Preparation
      |
      v
PuLP Integer Optimization
      |
      v
HiGHS / CBC Solver
      |
      v
Allocation + Metrics + Run History
```

## Next implementation phase

The natural next phase is to replace the lightweight milestone UI with the planned React/Tailwind application, move persistence to PostgreSQL, add GIS visualization/routing, authentication, and then evaluate the platform with larger and more realistic scenarios.
