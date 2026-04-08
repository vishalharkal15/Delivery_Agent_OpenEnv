import argparse
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
import uvicorn

from env.models import Action
from tasks.hard import create_env

app = FastAPI(title="Delivery Agent OpenEnv Server")

env = create_env()
obs = env.reset()


class StepPayload(BaseModel):
    action: dict[str, list[int]] | None = None


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _order_to_dict(order: Any) -> dict[str, Any]:
    payload = _model_dump(order) if hasattr(order, "dict") or hasattr(order, "model_dump") else dict(order)
    location = payload.get("location", (0.0, 0.0))
    return {
        "id": int(payload.get("id", 0)),
        "location": [float(location[0]), float(location[1])],
        "deadline": int(payload.get("deadline", 0)),
        "delivered": bool(payload.get("delivered", False)),
    }


def _vehicle_to_dict(vehicle: Any) -> dict[str, Any]:
    payload = _model_dump(vehicle) if hasattr(vehicle, "dict") or hasattr(vehicle, "model_dump") else dict(vehicle)
    location = payload.get("location", (0.0, 0.0))
    return {
        "id": str(payload.get("id", "")),
        "location": [float(location[0]), float(location[1])],
        "capacity": int(payload.get("capacity", 0)),
    }


def _observation_to_dict(observation: Any) -> dict[str, Any]:
    return {
        "time": int(observation.time),
        "orders": [_order_to_dict(order) for order in observation.orders],
        "vehicles": [_vehicle_to_dict(vehicle) for vehicle in observation.vehicles],
    }


def _parse_action(payload: dict[str, Any]) -> Action:
    if not isinstance(payload, dict):
        raise ValueError("action payload must be an object")

    assignments = payload.get("assignments", payload)
    if not isinstance(assignments, dict):
        raise ValueError("assignments must be a mapping")

    normalized: dict[str, list[int]] = {}
    for vehicle_id, order_ids in assignments.items():
        if order_ids is None:
            normalized[str(vehicle_id)] = []
            continue

        if not isinstance(order_ids, list):
            raise ValueError("each vehicle assignment must be a list")

        normalized[str(vehicle_id)] = [int(order_id) for order_id in order_ids]

    return Action(assignments=normalized)


@app.get("/")
def index() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
def reset(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    global env, obs

    data = payload or {}
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    vehicles = data.get("vehicles", options.get("vehicles"))

    if vehicles is not None:
        try:
            vehicles = int(vehicles)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="vehicles must be an integer") from exc

    env = create_env(num_vehicles=vehicles) if vehicles is not None else create_env()
    obs = env.reset()

    return {
        "status": "reset",
        "observation": _observation_to_dict(obs),
    }


@app.post("/step")
def step(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    global obs

    data = payload or {}
    action_payload = data.get("action", data)

    try:
        action = _parse_action(action_payload)
    except (ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid action payload") from exc

    obs, reward, done, info = env.step(action)

    return {
        "observation": _observation_to_dict(obs),
        "reward": float(reward),
        "done": bool(done),
        "info": info or {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OpenEnv FastAPI server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()

    uvicorn.run("server.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
