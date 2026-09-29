
- `app.py` — Flask application and REST API.
- `run.py` — one-command local launcher.
- `backend/db.py` — SQLite persistence and run history.
- `backend/service.py` — adapter that prepares database data and calls the existing optimizer.
- `frontend/templates/index.html` — browser dashboard.
- `frontend/static/style.css` — dashboard styling.
- `frontend/static/app.js` — API calls, optimization action and result rendering.
- `requirements.txt` at project root — Flask + PuLP + HiGHS.
- `PROJECT_STATUS_50_PERCENT.md` — milestone scope and remaining work.
- `CHANGES_50_PERCENT.md` — change summary.

### Modified
- `optimization/README.md` — documents the web milestone integration.
- `.gitignore` — keeps virtual environments, database files and caches out of the repository.

### Removed from the submission archive
- `.venv/` — should be recreated locally rather than committed.
- `.git/` — repository metadata is not needed in a project ZIP.
- macOS `__MACOSX/` metadata.

### Not changed
- The core optimization model, data models, priority logic, sample scenario and existing optimization tests were retained as the project foundation.
