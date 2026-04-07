from env.environment import DeliveryEnv


def create_env():
    env = DeliveryEnv(num_vehicles=1)

    # Few orders, no deadlines pressure
    env.orders = [
        {"id": 0, "location": (40.75, -73.98), "deadline": 50},
        {"id": 1, "location": (40.751, -73.981), "deadline": 50}
    ]

    return env