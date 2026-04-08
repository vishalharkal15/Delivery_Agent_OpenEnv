from env.environment import DeliveryEnv
from env.models import Order


def create_env():
    env = DeliveryEnv(num_vehicles=1)

    # Few orders, no deadlines pressure
    env.orders = [
        Order(id=0, location=(40.75, -73.98), deadline=50),
        Order(id=1, location=(40.751, -73.981), deadline=50)
    ]

    return env