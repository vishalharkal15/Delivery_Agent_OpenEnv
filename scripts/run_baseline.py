from tasks.hard import create_env
from env.models import Action
from env.grader import grade


def simple_agent(obs):
    assignments = {}

    for v in obs.vehicles:
        pending = [o.id for o in obs.orders if not o.delivered]
        assignments[v.id] = pending[:1]

    return Action(assignments=assignments)


env = create_env()
obs = env.reset()

done = False

while not done:
    action = simple_agent(obs)
    obs, reward, done, _ = env.step(action)

score = grade(env)

print("Final Score:", score)