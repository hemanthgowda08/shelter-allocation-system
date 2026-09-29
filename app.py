"""Flask entry point for the Emergency Shelter Allocation Platform milestone."""
from __future__ import annotations

from flask import Flask, jsonify, request, render_template

from backend import db
from backend.service import run_optimization
from optimization.sample_data import build_synthetic_scenario

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")


def bootstrap() -> None:
    db.init_db()
    groups, shelters, _ = build_synthetic_scenario()
    db.seed_if_empty(
        [g.__dict__ | {"special_requirements": list(g.special_requirements)} for g in groups],
        [s.__dict__ | {"status": s.status.value, "facilities": list(s.facilities)} for s in shelters],
    )


bootstrap()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "emergency-shelter-allocation"})


@app.get("/api/groups")
def groups():
    return jsonify(db.list_groups())


@app.post("/api/groups")
def add_group():
    data = request.get_json(force=True) or {}
    required = ["id", "name", "latitude", "longitude", "people"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        db.insert_group(data)
        return jsonify({"message": "Affected group added", "group": data}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/shelters")
def shelters():
    return jsonify(db.list_shelters())


@app.post("/api/shelters")
def add_shelter():
    data = request.get_json(force=True) or {}
    required = ["id", "name", "latitude", "longitude", "capacity"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        db.insert_shelter(data)
        return jsonify({"message": "Shelter added", "shelter": data}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.patch("/api/shelters/<shelter_id>/status")
def shelter_status(shelter_id: str):
    data = request.get_json(force=True) or {}
    status = data.get("status")
    if status not in {"available", "unavailable"}:
        return jsonify({"error": "status must be 'available' or 'unavailable'"}), 400
    if not db.update_shelter_status(shelter_id, status):
        return jsonify({"error": "Shelter not found"}), 404
    return jsonify({"message": "Shelter status updated", "status": status})


@app.post("/api/seed")
def seed():
    groups, shelters, _ = build_synthetic_scenario()
    db.seed_if_empty(
        [g.__dict__ | {"special_requirements": list(g.special_requirements)} for g in groups],
        [s.__dict__ | {"status": s.status.value, "facilities": list(s.facilities)} for s in shelters],
    )
    return jsonify({"message": "Seed data ensured", "groups": db.list_groups(), "shelters": db.list_shelters()})


@app.post("/api/optimize")
def optimize():
    data = request.get_json(silent=True) or {}
    try:
        travel_weight = float(data.get("travel_weight", 1.0))
        imbalance_weight = float(data.get("imbalance_weight", 10.0))
        if travel_weight < 0 or imbalance_weight < 0:
            raise ValueError("Weights cannot be negative.")
        result = run_optimization(travel_weight, imbalance_weight)
        run_id = db.save_run(result)
        result["run_id"] = run_id
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/runs")
def runs():
    return jsonify(db.list_runs())


@app.get("/api/runs/<int:run_id>")
def run_detail(run_id: int):
    result = db.get_run(run_id)
    if result is None:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
