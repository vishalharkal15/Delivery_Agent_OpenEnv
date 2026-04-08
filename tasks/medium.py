from env.environment import DeliveryEnv
from env.models import Order


def create_env():
    env = DeliveryEnv(num_vehicles=2)

    env.orders = [
        Order(
            id=i,
            location=(40.74 + i*0.002, -73.99 + i*0.002),
            deadline=30
        )
        for i in range(5)
    ]

    return env