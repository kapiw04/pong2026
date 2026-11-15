from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Config:
    width: float = 900.0
    height: float = 500.0
    paddle_x: float = 38.0
    paddle_width: float = 12.0
    paddle_height: float = 88.0
    paddle_speed: float = 460.0
    paddle_accel: float = 3600.0
    ball_radius: float = 8.0
    ball_speed: float = 430.0
    max_ball_speed: float = 800.0
    hit_acceleration: float = 1.06
    max_angle: float = 0.96
    velocity_transfer: float = 0.22
    spin_transfer: float = 5.0
    magnus: float = 0.13
    spin_decay: float = 0.55
    physics_hz: int = 120
    action_repeat: int = 4
    max_steps: int = 600
    advanced: bool = True

    @property
    def dt(self):
        return 1.0 / self.physics_hz

    @property
    def decision_dt(self):
        return self.dt * self.action_repeat

    def to_dict(self):
        return asdict(self)
