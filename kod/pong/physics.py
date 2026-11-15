from dataclasses import dataclass
import math
import random
from .config import Config


def clip(value, low, high):
    return max(low, min(high, value))


@dataclass
class Paddle:
    y: float
    vy: float = 0.0


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    spin: float = 0.0


@dataclass(frozen=True)
class Transition:
    reward: float
    terminated: bool
    truncated: bool
    winner: int
    agent_hits: int

    @property
    def done(self):
        return self.terminated or self.truncated


class Pong:
    def __init__(self, config=None, seed=0):
        self.cfg = config or Config()
        self.rng = random.Random(seed)
        self.reset()

    def reset(self, seed=None):
        if seed is not None:
            self.rng.seed(seed)
        c = self.cfg
        self.left = Paddle(self.rng.uniform(c.height * .25, c.height * .75))
        self.right = Paddle(self.rng.uniform(c.height * .25, c.height * .75))
        angle = self.rng.uniform(-.65, .65)
        direction = self.rng.choice((-1, 1))
        self.ball = Ball(c.width / 2, self.rng.uniform(90, c.height - 90),
                         direction * c.ball_speed * math.cos(angle),
                         c.ball_speed * math.sin(angle))
        self.steps = self.hits = self.right_hits = 0
        self.elapsed = 0.0
        self.done = False
        return self.observe()

    def observe(self):
        b, p = self.ball, self.right
        return b.x, b.y, b.vx, b.vy, p.y, p.vy, b.spin

    def _paddle(self, paddle, action):
        c = self.cfg
        target = action * c.paddle_speed
        delta = c.paddle_accel * c.dt
        paddle.vy += clip(target - paddle.vy, -delta, delta)
        paddle.y += paddle.vy * c.dt
        bound = c.paddle_height / 2
        bounded = clip(paddle.y, bound, c.height - bound)
        if bounded != paddle.y:
            paddle.vy = 0.0
        paddle.y = bounded

    def _bounce(self, paddle, impact_y, direction):
        c, b = self.cfg, self.ball
        speed = min(c.max_ball_speed, math.hypot(b.vx, b.vy) * c.hit_acceleration)
        offset = clip((impact_y - paddle.y) / (c.paddle_height / 2), -1, 1)
        if c.advanced:
            angle = offset * c.max_angle
            vy = speed * math.sin(angle) + c.velocity_transfer * paddle.vy
            vy = clip(vy, -speed * .88, speed * .88)
            b.vy = vy
            b.vx = direction * math.sqrt(speed * speed - vy * vy)
            b.spin = clip(c.spin_transfer * paddle.vy / c.paddle_speed + 2 * offset, -7, 7)
        else:

            b.vx = direction * abs(b.vx) * c.hit_acceleration
            factor = min(1.0, c.max_ball_speed / math.hypot(b.vx, b.vy))
            b.vx *= factor
            b.vy *= factor
            b.spin = 0.0
        self.hits += 1
        if direction < 0:
            self.right_hits += 1

    def step(self, right_action, left_action):
        if self.done:
            raise RuntimeError("Episode ended. Call reset() before step().")
        if right_action not in (-1, 0, 1) or left_action not in (-1, 0, 1):
            raise ValueError("Actions must be -1, 0 or 1.")
        c, b = self.cfg, self.ball
        previous_hits = self.right_hits
        winner = 0
        for _ in range(c.action_repeat):
            old_left, old_right = self.left.y, self.right.y
            self._paddle(self.left, left_action)
            self._paddle(self.right, right_action)
            old_x, old_y = b.x, b.y
            if c.advanced:
                speed = math.hypot(b.vx, b.vy)
                b.vy += c.magnus * b.spin * b.vx * c.dt
                scale = speed / math.hypot(b.vx, b.vy)
                b.vx *= scale
                b.vy *= scale
                b.spin *= math.exp(-c.spin_decay * c.dt)
            b.x += b.vx * c.dt
            b.y += b.vy * c.dt

            if b.y < c.ball_radius:
                b.y = 2 * c.ball_radius - b.y
                b.vy = abs(b.vy)
                b.spin *= -.8
            elif b.y > c.height - c.ball_radius:
                b.y = 2 * (c.height - c.ball_radius) - b.y
                b.vy = -abs(b.vy)
                b.spin *= -.8
            face_left = c.paddle_x + c.paddle_width / 2 + c.ball_radius
            face_right = c.width - face_left
            paddle = None
            if b.vx < 0 and old_x >= face_left >= b.x:
                paddle, old_p, face, direction = self.left, old_left, face_left, 1
            elif b.vx > 0 and old_x <= face_right <= b.x:
                paddle, old_p, face, direction = self.right, old_right, face_right, -1
            if paddle is not None:
                fraction = (face - old_x) / (b.x - old_x)
                impact_y = old_y + fraction * (b.y - old_y)
                paddle_y = old_p + fraction * (paddle.y - old_p)
                if abs(impact_y - paddle_y) <= c.paddle_height / 2 + c.ball_radius:

                    b.x = face + direction * abs(b.x - face)
                    self._bounce(paddle, impact_y, direction)
            self.elapsed += c.dt
            if b.x < -c.ball_radius:
                winner = 1
                break
            if b.x > c.width + c.ball_radius:
                winner = -1
                break
        self.steps += 1
        terminated = winner != 0
        truncated = not terminated and c.max_steps > 0 and self.steps >= c.max_steps
        self.done = terminated or truncated
        hit_delta = self.right_hits - previous_hits
        return Transition(float(winner) + .2 * hit_delta, terminated, truncated,
                          winner, hit_delta)
