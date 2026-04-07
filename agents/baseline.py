from env.models import Action


def distance(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2


def baseline_agent(obs):
    assignments = {}

    remaining_orders = [o for o in obs.orders if not o.delivered]

    for v in obs.vehicles:
        # sort orders by distance
        sorted_orders = sorted(
            remaining_orders,
            key=lambda o: distance(v.location, o.location)
        )

        # take multiple (up to capacity)
        selected = sorted_orders[:v.capacity]

        assignments[v.id] = [o.id for o in selected]

        # remove assigned to avoid duplication
        for o in selected:
            remaining_orders.remove(o)

    return Action(assignments=assignments)