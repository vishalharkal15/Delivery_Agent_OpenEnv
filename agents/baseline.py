from env.models import Action


def distance(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2


def nearest_neighbor_route(start, orders):
    """
    Simple TSP approximation using nearest neighbor
    """
    route = []
    current = start
    remaining = orders[:]

    while remaining:
        next_order = min(remaining, key=lambda o: distance(current, o.location))
        route.append(next_order)
        current = next_order.location
        remaining.remove(next_order)

    return route


def baseline_agent(obs):
    assignments = {}

    remaining_orders = [o for o in obs.orders if not o.delivered]

    for v in obs.vehicles:
        if not remaining_orders:
            assignments[v.id] = []
            continue

        # Step 1: pick nearby orders
        sorted_orders = sorted(
            remaining_orders,
            key=lambda o: distance(v.location, o.location)
        )

        selected = sorted_orders[:v.capacity]

        # Step 2: optimize route order (TSP approx)
        optimized_route = nearest_neighbor_route(v.location, selected)

        assignments[v.id] = [o.id for o in optimized_route]

        # remove assigned
        for o in selected:
            remaining_orders.remove(o)

    return Action(assignments=assignments)