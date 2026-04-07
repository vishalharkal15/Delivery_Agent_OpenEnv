def compute_reward(state):
    reward = 0

    for order in state.orders:
        if order.delivered:
            if state.time <= order.deadline:
                reward += 1.0
            else:
                reward += 0.3

        if order.priority == "high" and order.delivered:
            reward += 0.5

    idle = sum(1 for v in state.vehicles if not v.load)
    reward -= 0.2 * idle

    return reward