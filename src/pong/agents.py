from bisect import bisect_right
import json
import math
from pathlib import Path
import random
import numpy as np
from .physics import Config


class QAgent:
    X_EDGES = (450, 600, 700, 760, 800, 825, 840)
    ERROR_EDGES = (-250, -150, -100, -70, -50, -40, -30, -20, -10, 0,
                   10, 20, 30, 40, 50, 70, 100, 150, 250)
    VX_EDGES = (-550, 0, 550)
    VY_EDGES = (-400, -180, -60, 60, 180, 400)
    SPIN_EDGES = (-3, -1, 1, 3)
    PADDLE_VY_EDGES = (-250, -60, 60, 250)

    def __init__(self, cell=25, alpha=.15, gamma=.995, seed=7, config=None,
                 representation='relative-v1'):
        self.cfg = config or Config()
        self.cell, self.alpha, self.gamma = cell, alpha, gamma
        self.representation = representation
        self.rows = math.ceil(self.cfg.height / cell)
        self.cols = math.ceil(self.cfg.width / cell)
        self.half_rows = math.ceil(self.cfg.height / (2 * cell))
        if representation == 'grid-v6':
            states = self.cols * self.rows * self.rows * 18
        elif representation == 'relative-v1':
            states = 8 * self.half_rows * 20 * 4 * 7 * 5 * 5
        else:
            raise ValueError('Nieznany sposób kodowania stanu.')
        self.q = np.zeros((states, 3), dtype=np.float32)
        self.rng = random.Random(seed)
        self.metadata = {}

    def state(self, obs):
        x, y, vx, vy, py, pvy = obs[:6]
        if self.representation == 'relative-v1':
            spin = obs[6]
            if y > self.cfg.height / 2:
                y, py = self.cfg.height - y, self.cfg.height - py
                vy, pvy, spin = -vy, -pvy, -spin
            state = bisect_right(self.X_EDGES, x) * self.half_rows
            state += min(self.half_rows - 1, max(0, int(y / self.cell)))
            for value, edges in ((y - py, self.ERROR_EDGES), (vx, self.VX_EDGES),
                                 (vy, self.VY_EDGES), (spin, self.SPIN_EDGES),
                                 (pvy, self.PADDLE_VY_EDGES)):
                state = state * (len(edges) + 1) + bisect_right(edges, value)
            return state
        col = min(self.cols - 1, max(0, int(x / self.cell)))
        row = min(self.rows - 1, max(0, int(y / self.cell)))
        paddle = min(self.rows - 1, max(0, int(py / self.cell)))
        return (((((col * self.rows + row) * self.rows + paddle) * 2 + int(vx > 0)) * 3
                 + bisect_right((-100, 100), vy)) * 3 + bisect_right((-80, 80), pvy))

    def action(self, obs, epsilon=0):
        if epsilon and self.rng.random() < epsilon:
            return self.rng.choice((-1, 0, 1))
        values = self.q[self.state(obs)]
        best = max(values)
        if values[1] == best:
            return 0
        action = -1 if values[0] >= values[2] else 1
        return action * self.orientation(obs)

    def orientation(self, obs):
        return -1 if self.representation == 'relative-v1' and obs[1] > self.cfg.height / 2 else 1

    def update(self, obs, action, reward, next_obs, terminated):
        state, next_state = self.state(obs), self.state(next_obs)
        action *= self.orientation(obs)
        target = reward if terminated else reward + self.gamma * float(max(self.q[next_state]))
        previous = float(self.q[state, action + 1])
        self.q[state, action + 1] = previous + self.alpha * (target - previous)

    def save(self, path, metadata):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata = {"reward": {"point": 1, "loss": -1, "hit": .2}, **metadata,
                         "version": 6 if self.representation == 'grid-v6' else 7,
                         "representation": self.representation,
                         "cell": self.cell, "alpha": self.alpha,
                         "gamma": self.gamma, "config": self.cfg.to_dict()}
        np.savez_compressed(path, q=self.q, metadata=np.array(json.dumps(self.metadata)))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            if metadata['version'] not in (6, 7):
                raise ValueError('Uruchom train, aby przygotować aktualny model.')
            agent = cls(metadata['cell'], metadata['alpha'], metadata['gamma'],
                        config=Config(**metadata['config']),
                        representation='grid-v6' if metadata['version'] == 6 else metadata['representation'])
            if data['q'].shape != agent.q.shape or not np.isfinite(data['q']).all():
                raise ValueError('Niepoprawna tablica Q.')
            agent.q[:] = data['q']
            agent.metadata = metadata
        return agent


class Tracker:
    def __init__(self, side='left'):
        self.side = side

    def action(self, env):
        paddle = env.left if self.side == 'left' else env.right
        difference = env.ball.y - paddle.y
        return 1 if difference > 12 else -1 if difference < -12 else 0
