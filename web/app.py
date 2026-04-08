import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, jsonify, request
from tasks.hard import create_env
from env.models import Action
from env.grader import grade
from agents.baseline import baseline_agent

app = Flask(__name__)

env = create_env()
obs = env.reset()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/step")
def step():
    global obs

    action = baseline_agent(obs)
    obs, reward, done, _ = env.step(action)

    metrics = {
        "reward": reward,
        "score": grade(env),
        "time": obs.time,
        "delivery_rate": env.completed / (env.completed + len(env.orders) + 1),
        "avg_distance": env.total_distance / (env.completed + 1),
        "vehicle_stats": getattr(env, "vehicle_stats", {})
    }

    return jsonify({
        "orders": [
            {"lat": o.location[0], "lon": o.location[1], "delivered": o.delivered}
            for o in obs.orders
        ],
        "vehicles": [
            {"id": v.id, "lat": v.location[0], "lon": v.location[1]}
            for v in obs.vehicles
        ],
        "metrics": metrics,
        "done": done
    })


@app.route("/reset", methods=["POST"])
def reset():
    global env, obs

    data = request.get_json(silent=True) or {}

    try:
        vehicles = int(data.get("vehicles", 2))
    except (TypeError, ValueError):
        vehicles = 2

    env = create_env(num_vehicles=vehicles)
    obs = env.reset()

    return jsonify({"status": "reset"})


@app.route("/add_order", methods=["POST"])
def add_order():
    data = request.get_json()

    from env.models import Order

    env.orders.append(
        Order(
            id=len(env.orders),
            location=(data["lat"], data["lon"]),
            deadline=env.time + 20
        )
    )

    return jsonify({"status": "added"})

@app.route("/step_action", methods=["POST"])
def step_action():
    global obs

    data = request.get_json()

    action = Action(**data)
    obs, reward, done, _ = env.step(action)

    return jsonify({
        "reward": reward,
        "done": done
    })

if __name__ == "__main__":
    app.run(debug=True)