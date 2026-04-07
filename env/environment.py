import random
import math
from env.models import Order, Vehicle, Observation


class DeliveryEnv:
    def __init__(self, num_vehicles=2, max_steps=100):
        self.num_vehicles = num_vehicles
        self.max_steps = max_steps
        self.reset()

    def reset(self):
        self.time = 0
        self.total_distance = 0
        self.completed = 0

        self.orders = []

        self.vehicles = [
            Vehicle(
                id=str(i),
                location=(
                    random.uniform(40.74, 40.76),
                    random.uniform(-73.99, -73.98)
                ),
                capacity=3
            )
            for i in range(self.num_vehicles)
        ]

        # Track deliveries per vehicle
        self.vehicle_stats = {v.id: 0 for v in self.vehicles}

        # 🔥 Route memory for each vehicle
        self.vehicle_routes = {v.id: [] for v in self.vehicles}

        return self._get_obs()

    def state(self):
        return self._get_obs()

    def _get_obs(self):
        return Observation(
            time=self.time,
            orders=self.orders,
            vehicles=self.vehicles
        )

    def distance(self, a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    def step(self, action):
        self.time += 1
        reward = 0

        delivered_orders = set()

        for vid, order_ids in action.assignments.items():
            vehicle = next((v for v in self.vehicles if v.id == vid), None)

            if not vehicle:
                reward -= 0.2
                continue

            # Capacity constraint
            if len(order_ids) > vehicle.capacity:
                reward -= 0.3
                order_ids = order_ids[:vehicle.capacity]

            # 🔥 Initialize route ONLY if empty
            if not self.vehicle_routes[vid]:
                self.vehicle_routes[vid] = order_ids.copy()

            route = self.vehicle_routes[vid]

            if not route:
                reward -= 0.05  # idle
                continue

            current_oid = route[0]
            order = next((o for o in self.orders if o.id == current_oid), None)

            if not order or order.delivered:
                route.pop(0)
                continue

            # Move toward target
            lat, lon = vehicle.location
            tlat, tlon = order.location

            step_size = 0.0007
            dlat = tlat - lat
            dlon = tlon - lon
            dist = math.sqrt(dlat**2 + dlon**2)

            if dist > 0:
                lat += step_size * (dlat / dist)
                lon += step_size * (dlon / dist)
                vehicle.location = (lat, lon)
                self.total_distance += dist

            # 🔥 Deliver ANY nearby order (important realism)
            for o in self.orders:
                if o.delivered:
                    continue

                if self.distance(vehicle.location, o.location) < 0.0005:
                    o.delivered = True
                    delivered_orders.add(o.id)
                    self.completed += 1

                    self.vehicle_stats[vehicle.id] += 1

                    if self.time <= o.deadline:
                        reward += 1
                    else:
                        reward -= 0.5

                    # Remove from route if present
                    if o.id in route:
                        route.remove(o.id)

        # Remove delivered orders globally
        self.orders = [o for o in self.orders if not o.delivered]

        # Small global penalty
        reward -= 0.02 * len(self.vehicles)

        done = self.time >= self.max_steps

        return self._get_obs(), reward, done, {}