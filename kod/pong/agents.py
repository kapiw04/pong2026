"""Tabular Q-learning and explicit comparison policies."""
from bisect import bisect_right
import math
import json
from pathlib import Path
import random
import numpy as np
from .config import Config


ACTIONS = (-1, 0, 1)
ERROR_EDGES = (-300, -200, -130, -85, -50, -25, -8, 8, 25, 50, 85, 130, 200, 300)
STATE_SHAPE = (15, 3, 2, 3, 3)
N_STATES = int(np.prod(STATE_SHAPE))
ENCODER_VERSION = 4


def target_y(obs, config=None):
    """Linear wall-reflected landing estimate. Spin curvature is not predicted."""
    c = config or Config()
    x, y, vx, vy, *_ = obs
    if vx <= 0:
        return c.height / 2
    face = c.width - c.paddle_x - c.paddle_width / 2 - c.ball_radius
    time_to_face = max(0.0, (face - x) / vx)
    span = c.height - 2 * c.ball_radius
    unfolded = (y - c.ball_radius + vy * time_to_face) % (2 * span)
    return c.ball_radius + (unfolded if unfolded <= span else 2 * span - unfolded)


def encode(obs, config=None):
    c = config or Config()
    x, y, vx, vy, py, pvy, spin = obs
    parts = (bisect_right(ERROR_EDGES, (target_y(obs, c) - py) * 500 / c.height),
             min(2, max(0, int(3 * x / c.width))), int(vx > 0),
             bisect_right((-80, 80), pvy),
             0 if py < c.height * .25 else 2 if py > c.height * .75 else 1)
    index = 0
    for part, size in zip(parts, STATE_SHAPE):
        index = index * size + part
    return index


def potential(obs, config=None):
    """Potential based on the same approximate landing feature as the table."""
    c = config or Config()
    return -abs(target_y(obs, c) - obs[4]) / c.height


class QAgent:
    def __init__(self, seed=0, config=None, alpha=.12, gamma=.98, shaping=True,
                 movement_cost=.001, distance_cost=.02, encoder="relative", cell=50):
        self.cfg = config or Config()
        self.encoder, self.cell = encoder, cell
        if encoder not in ("relative", "grid") or cell <= 0:
            raise ValueError("Invalid encoder or grid cell size")
        self.grid_rows = math.ceil(self.cfg.height / cell)
        self.grid_cols = math.ceil(self.cfg.width / cell)
        n = N_STATES if encoder == "relative" else self.grid_cols * (2 * self.grid_rows - 1) * 18
        self.q = np.zeros((n, 3), dtype=np.float32)
        self.visits = np.zeros((n, 3), dtype=np.uint32)
        self.rng = random.Random(seed)
        self.alpha, self.gamma, self.shaping = alpha, gamma, shaping
        self.movement_cost, self.distance_cost = movement_cost, distance_cost
        self.metadata = {}

    def state(self, obs):
        if self.encoder == "relative":
            return encode(obs, self.cfg)
        x, y, vx, vy, py, pvy, _ = obs
        col = min(self.grid_cols - 1, max(0, int(x / self.cell)))
        by = min(self.grid_rows - 1, max(0, int(y / self.cell)))
        p = min(self.grid_rows - 1, max(0, int(py / self.cell)))
        difference = by - p + self.grid_rows - 1
        return ((((col * (2 * self.grid_rows - 1) + difference) * 2 + int(vx > 0)) * 3
                 + bisect_right((-100, 100), vy)) * 3 + bisect_right((-80, 80), pvy))

    def action(self, obs, epsilon=0.0):
        if epsilon > 0 and self.rng.random() < epsilon:
            return self.rng.choice(ACTIONS)
        values = self.q[self.state(obs)]
        # Deterministic and unbiased vertical tie handling: prefer staying still.
        best = max(values)
        if values[1] == best:
            return 0
        return -1 if values[0] >= values[2] else 1

    def update(self, obs, action, reward, next_obs, terminated):
        s, ns = self.state(obs), self.state(next_obs)
        a = action + 1
        reward -= self.movement_cost * abs(action)
        if self.shaping:
            reward -= self.distance_cost * abs(target_y(next_obs, self.cfg) - next_obs[4]) / self.cfg.height
        if self.shaping:
            reward += self.gamma * (0.0 if terminated else potential(next_obs, self.cfg))
            reward -= potential(obs, self.cfg)
        target = reward
        if not terminated:
            target += self.gamma * float(max(self.q[ns]))
        previous = float(self.q[s, a])
        self.q[s, a] = previous + self.alpha * (target - previous)
        self.visits[s, a] += 1

    def save(self, path, metadata=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"encoder_version": ENCODER_VERSION, "config": self.cfg.to_dict(),
                "alpha": self.alpha, "gamma": self.gamma, "shaping": self.shaping,
                "encoder": self.encoder, "cell": self.cell,
                "movement_cost": self.movement_cost, "distance_cost": self.distance_cost,
                **self.metadata, **(metadata or {})}
        np.savez_compressed(path, q=self.q, visits=self.visits,
                            metadata=np.array(json.dumps(meta)))

    @classmethod
    def load(cls, path):
        # Numeric arrays + JSON only. No pickle or executable model objects.
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"]))
            if meta["encoder_version"] != ENCODER_VERSION:
                raise ValueError("Incompatible state encoder in model.")
            q, visits = data["q"], data["visits"]
            agent = cls(config=Config(**meta["config"]), alpha=meta["alpha"],
                        gamma=meta["gamma"], shaping=meta["shaping"],
                        movement_cost=meta["movement_cost"], distance_cost=meta["distance_cost"],
                        encoder=meta["encoder"], cell=meta["cell"])
            if q.shape != agent.q.shape or visits.shape != q.shape or not np.isfinite(q).all():
                raise ValueError("Invalid model arrays.")
            agent.q[:] = q
            agent.visits[:] = visits
            agent.metadata = meta
        return agent


class Tracker:
    def __init__(self, side="left", deadzone=12.0, reaction_steps=4):
        self.side, self.deadzone = side, deadzone
        self.reaction_steps = reaction_steps
        self.last_action = 0

    def action(self, env):
        if env.steps % self.reaction_steps:
            return self.last_action
        paddle = env.left if self.side == "left" else env.right
        error = env.ball.y - paddle.y
        self.last_action = 1 if error > self.deadzone else -1 if error < -self.deadzone else 0
        return self.last_action


class RandomAgent:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def action(self, obs):
        return self.rng.choice(ACTIONS)
