import argparse
import os
import socket
import sys
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask, jsonify, request
from pydantic import ValidationError

from agents.baseline import baseline_agent
from env.grader import grade
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


def run_episode(max_steps=100, timeout_seconds=20.0):
    global env, obs

    env = create_env()
    obs = env.reset()

    steps = 0
    done = False
    total_reward = 0.0
    timed_out = False
    started_at = time.monotonic()
    last_assignments = {}
    step_records = []

    while not done and steps < max_steps:
        if time.monotonic() - started_at > timeout_seconds:
            timed_out = True
            break

        try:
            action = baseline_agent(obs)
        except Exception:
            # Fall back to no-op assignments to keep inference bounded.
            action = Action(assignments={v.id: [] for v in obs.vehicles})

        last_assignments = {
            str(vehicle_id): [int(order_id) for order_id in order_ids]
            for vehicle_id, order_ids in action.assignments.items()
        }

        try:
            obs, reward, done, _ = env.step(action)
        except Exception:
            timed_out = True
            break

        total_reward += float(reward)
        steps += 1
        step_records.append({
            "step": int(steps),
            "reward": float(reward),
            "done": bool(done),
        })

    result = {
        "status": "ok",
        "done": bool(done),
        "timed_out": bool(timed_out),
        "steps": int(steps),
        "total_reward": float(total_reward),
        "score": float(grade(env)),
        "action": {"assignments": last_assignments},
        "assignments": last_assignments,
        "observation": _observation_to_dict(obs),
        "step_records": step_records,
    }
    return result


def emit_structured_output(result, task_name):
    print(f"[START] task={task_name}", flush=True)

    step_records = result.get("step_records", [])
    if step_records:
        for item in step_records:
            step_value = int(item.get("step", 0))
            reward_value = float(item.get("reward", 0.0))
            done_value = str(bool(item.get("done", False))).lower()
            print(
                f"[STEP] step={step_value} reward={reward_value:.6f} done={done_value}",
                flush=True,
            )
    else:
        done_value = str(bool(result.get("done", True))).lower()
        print(f"[STEP] step=0 reward=0.000000 done={done_value}", flush=True)

    end_score = float(result.get("score", 0.0))
    end_steps = int(result.get("steps", 0))
    end_done = str(bool(result.get("done", False))).lower()
    end_timeout = str(bool(result.get("timed_out", False))).lower()
    end_status = str(result.get("status", "ok"))
    print(
        f"[END] task={task_name} score={end_score:.6f} steps={end_steps} done={end_done} timed_out={end_timeout} status={end_status}",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Run delivery optimization inference")
    parser.add_argument("--serve", action="store_true", help="Run Flask server mode")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "7860")))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--max-steps", type=int, default=int(os.environ.get("MAX_STEPS", "100")))
    parser.add_argument("--timeout-seconds", type=float, default=float(os.environ.get("TIMEOUT_SECONDS", "20.0")))
    parser.add_argument("--task-name", default=os.environ.get("TASK_NAME", "delivery-optimization-env"))
    args = parser.parse_args()

    if not args.serve:
        try:
            result = run_episode(max_steps=max(1, args.max_steps), timeout_seconds=max(1.0, args.timeout_seconds))
        except Exception as exc:
            result = {
                "status": "error",
                "error": str(exc),
                "done": True,
                "timed_out": True,
                "steps": 0,
                "score": 0.0,
                "step_records": [],
                "action": {"assignments": {}},
                "assignments": {},
            }

        emit_structured_output(result, args.task_name)
        return

    selected_port = args.port
    for candidate_port in range(args.port, args.port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((args.host, candidate_port))
                selected_port = candidate_port
                break
            except OSError:
                continue

    if selected_port != args.port:
        print(f"Port {args.port} is in use. Starting inference server on {selected_port} instead.")

    app.run(host=args.host, port=selected_port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()