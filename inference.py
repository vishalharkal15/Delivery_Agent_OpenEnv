import os

from flask import Flask, jsonify, request
from pydantic import ValidationError

from env.models import Action
from tasks.hard import create_env

app = Flask(__name__)

env = create_env()
obs = env.reset()


def _model_dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _order_to_dict(order):
    payload = _model_dump(order) if hasattr(order, "dict") or hasattr(order, "model_dump") else dict(order)
    location = payload.get("location", (0.0, 0.0))
    return {
        "id": int(payload.get("id", 0)),
        "location": [float(location[0]), float(location[1])],
        "deadline": int(payload.get("deadline", 0)),
        "delivered": bool(payload.get("delivered", False)),
    }


def _vehicle_to_dict(vehicle):
    payload = _model_dump(vehicle) if hasattr(vehicle, "dict") or hasattr(vehicle, "model_dump") else dict(vehicle)
    location = payload.get("location", (0.0, 0.0))
    return {
        "id": str(payload.get("id", "")),
        "location": [float(location[0]), float(location[1])],
        "capacity": int(payload.get("capacity", 0)),
    }


def _observation_to_dict(observation):
    return {
        "time": int(observation.time),
        "orders": [_order_to_dict(order) for order in observation.orders],
        "vehicles": [_vehicle_to_dict(vehicle) for vehicle in observation.vehicles],
    }


def _parse_action(payload):
    if not isinstance(payload, dict):
        raise ValueError("action payload must be an object")

    assignments = payload.get("assignments", payload)

    if not isinstance(assignments, dict):
        raise ValueError("assignments must be a mapping")

    normalized = {}
    for vehicle_id, order_ids in assignments.items():
        if order_ids is None:
            normalized[str(vehicle_id)] = []
            continue

        if not isinstance(order_ids, list):
            raise ValueError("each vehicle assignment must be a list")

        normalized[str(vehicle_id)] = [int(order_id) for order_id in order_ids]

    return Action(assignments=normalized)


@app.get("/")
def index():
    return jsonify({"status": "ok"})


@app.post("/reset")
def reset():
    global env, obs

    data = request.get_json(silent=True) or {}
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    vehicles = data.get("vehicles", options.get("vehicles"))

    if vehicles is not None:
        try:
            vehicles = int(vehicles)
        except (TypeError, ValueError):
            return jsonify({"error": "vehicles must be an integer"}), 400

    try:
        env = create_env(num_vehicles=vehicles) if vehicles is not None else create_env()
    except TypeError:
        env = create_env()
        if vehicles is not None and hasattr(env, "num_vehicles"):
            env.num_vehicles = vehicles

    obs = env.reset()

    return jsonify({
        "status": "reset",
        "observation": _observation_to_dict(obs),
    })


@app.post("/step")
def step():
    global obs

    data = request.get_json(silent=True) or {}
    action_payload = data.get("action", data)

    try:
        action = _parse_action(action_payload)
    except (ValidationError, ValueError, TypeError):
        return jsonify({"error": "invalid action payload"}), 400

    obs, reward, done, info = env.step(action)

    return jsonify({
        "observation": _observation_to_dict(obs),
        "reward": float(reward),
        "done": bool(done),
        "info": info or {},
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    app.run(host="0.0.0.0", port=port)
