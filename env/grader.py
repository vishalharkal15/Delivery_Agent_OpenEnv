def grade(env):
    total = len(env.orders) + env.completed

    if total == 0:
        return 0.0

    delivery_score = env.completed / total
    efficiency = 1 / (env.total_distance + 1)

    score = 0.7 * delivery_score + 0.3 * efficiency

    return round(score, 2)