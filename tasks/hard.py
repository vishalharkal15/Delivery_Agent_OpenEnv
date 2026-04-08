from env.environment import DeliveryEnv


def create_env(num_vehicles=3):
    return DeliveryEnv(num_vehicles=num_vehicles)