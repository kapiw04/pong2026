from bisect import bisect_right
import json
import math
from pathlib import Path
import random
import numpy as np
from .physics import Config


class QAgent:
    def __init__(self, cell=50, alpha=.12, gamma=.98, seed=7, config=None):
        self.cfg = config or Config()
        self.cell, self.alpha, self.gamma = cell, alpha, gamma
        self.rows = math.ceil(self.cfg.height / cell)
        self.cols = math.ceil(self.cfg.width / cell)
        self.q = np.zeros((self.cols * self.rows * self.rows * 18, 3), dtype=np.float32)
        self.rng = random.Random(seed)
        self.metadata = {}

    def state(self, obs):
        x, y, vx, vy, py, pvy = obs
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
        return -1 if values[0] >= values[2] else 1

    def update(self, obs, action, reward, next_obs, terminated):
        state, next_state = self.state(obs), self.state(next_obs)
        target = reward if terminated else reward + self.gamma * float(max(self.q[next_state]))
        previous = float(self.q[state, action + 1])
        self.q[state, action + 1] = previous + self.alpha * (target - previous)

    def save(self, path, metadata):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata = {"version": 6, "cell": self.cell, "alpha": self.alpha,
                         "gamma": self.gamma, "config": self.cfg.to_dict(),
                         "reward": {"point": 1, "loss": -1, "hit": .2}, **metadata}
        np.savez_compressed(path, q=self.q, metadata=np.array(json.dumps(self.metadata)))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            if metadata['version'] != 6:
                raise ValueError('Uruchom train, aby przygotować aktualny model.')
            agent = cls(metadata['cell'], metadata['alpha'], metadata['gamma'],
                        config=Config(**metadata['config']))
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
