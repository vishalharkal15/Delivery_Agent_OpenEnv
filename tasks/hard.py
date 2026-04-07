from env.environment import DeliveryEnv


def create_env():
    return DeliveryEnv(num_vehicles=3)