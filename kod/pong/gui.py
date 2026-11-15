from collections import deque
from dataclasses import replace
from enum import Enum
import math
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.mixer.pre_init(frequency=0, size=0, channels=0, buffer=0)
from .agents import QAgent, Tracker
from .physics import Pong


BG = (12, 19, 29)
FIELD = (17, 28, 40)
LINE = (40, 56, 70)
TEXT = (233, 242, 244)
MUTED = (140, 163, 179)
TEAL = (86, 231, 196)
CORAL = (255, 145, 121)
W, H = 988, 680
OX, OY = 44, 110


class Scene(Enum):
    MENU = 0
    PLAY = 1
    PAUSE = 2
    FINISHED = 3


class Game:
    def __init__(self, model_path, demo=False, seed=2026):
        pygame.init()
        self.window = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        pygame.display.set_caption("PONG / Q-learning")
        self.canvas = pygame.Surface((W, H))
        self.fonts = {size: pygame.font.SysFont("Arial", size) for size in (14, 16, 18, 22, 28, 40, 64, 76)}
        self.agent = QAgent.load(model_path)
        self.env = Pong(replace(self.agent.cfg, max_steps=0), seed)
        self.tracker = Tracker()
        self.demo = demo
        self.scene = Scene.PLAY if demo else Scene.MENU
        self.score = [0, 0]
        self.trail = deque(maxlen=22)
        self.accumulator = 0.0
        self.point_delay = .6
        self.help = False

    def text(self, value, x, y, size=18, color=TEXT, center=False):
        surf = self.fonts[size].render(str(value), True, color)
        rect = surf.get_rect(midtop=(x, y)) if center else surf.get_rect(topleft=(x, y))
        self.canvas.blit(surf, rect)
        return rect

    def new_match(self, demo=None):
        if demo is not None:
            self.demo = demo
        self.score[:] = [0, 0]
        self.env.reset()
        self.trail.clear()
        self.scene = Scene.PLAY
        self.point_delay = .6
        self.accumulator = 0.0
        self.help = False

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type != pygame.KEYDOWN:
                continue
            key = event.key
            if key == pygame.K_ESCAPE:
                if self.help:
                    self.help = False
                elif self.scene == Scene.MENU:
                    return False
                else:
                    self.scene = Scene.MENU
            elif key == pygame.K_RETURN:
                if self.scene in (Scene.MENU, Scene.FINISHED):
                    self.new_match(False)
            elif key == pygame.K_d:
                self.new_match(not self.demo if self.scene != Scene.MENU else True)
            elif key == pygame.K_r:
                self.new_match()
            elif key == pygame.K_SPACE:
                if self.scene == Scene.PLAY:
                    self.scene = Scene.PAUSE
                elif self.scene == Scene.PAUSE:
                    self.scene = Scene.PLAY
            elif key == pygame.K_h:
                self.help = not self.help
        return True

    def update(self, dt):
        if self.scene != Scene.PLAY or self.help:
            return
        if self.point_delay > 0:
            self.point_delay -= dt
            return
        self.accumulator += min(dt, .1)
        keys = pygame.key.get_pressed()
        while self.accumulator >= self.env.cfg.decision_dt:
            self.accumulator -= self.env.cfg.decision_dt
            if self.demo:
                left = self.tracker.action(self.env)
            else:
                left = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
            obs = self.env.observe()
            action = self.agent.action(obs)
            result = self.env.step(action, left)
            self.trail.append((self.env.ball.x, self.env.ball.y))
            if result.done:
                if result.winner:
                    self.score[0 if result.winner == -1 else 1] += 1
                if max(self.score) >= 7:
                    self.scene = Scene.FINISHED
                else:
                    self.env.reset()
                    self.trail.clear()
                    self.point_delay = .8
                self.accumulator = 0.0
                break

    def draw(self):
        s = self.canvas
        s.fill(BG)
        self.text("Reguła" if self.demo else "Gracz", OX, 45, 22, CORAL)
        self.text(f"Q / {self.agent.cell} px", W - OX - 160, 45, 22, TEAL)
        self.text(f"{self.score[0]}    :    {self.score[1]}", W / 2, 27, 40, center=True)
        pygame.draw.rect(s, FIELD, (OX, OY, 900, 500), border_radius=4)
        pygame.draw.rect(s, LINE, (OX, OY, 900, 500), 1, border_radius=4)
        for y in range(OY + 14, OY + 490, 23):
            pygame.draw.line(s, LINE, (OX + 450, y), (OX + 450, y + 10), 2)
        c, b = self.env.cfg, self.env.ball
        for i, (x, y) in enumerate(self.trail):
            intensity = (i + 1) / max(1, len(self.trail))
            color = tuple(int(FIELD[j] + (TEAL[j] - FIELD[j]) * intensity * .3) for j in range(3))
            pygame.draw.circle(s, color, (OX + x, OY + y), max(2, int(5 * intensity)))
        for x, p, color in [(c.paddle_x, self.env.left, CORAL),
                             (c.width - c.paddle_x, self.env.right, TEAL)]:
            pygame.draw.rect(s, color, (OX + x - c.paddle_width / 2,
                             OY + p.y - c.paddle_height / 2, c.paddle_width,
                             c.paddle_height), border_radius=5)
        pygame.draw.circle(s, TEXT, (OX + b.x, OY + b.y), c.ball_radius)
        angle = self.env.elapsed * b.spin * 2
        pygame.draw.line(s, BG, (OX + b.x, OY + b.y),
                         (OX + b.x + 6 * math.cos(angle), OY + b.y + 6 * math.sin(angle)), 2)
        self.text("Esc  menu       H  sterowanie", W / 2, 640, 16, MUTED, True)
        if self.scene != Scene.PLAY or self.help:
            shade = pygame.Surface((900, 500), pygame.SRCALPHA)
            shade.fill((9, 17, 26, 235))
            s.blit(shade, (OX, OY))
            if self.help:
                self.text("Sterowanie", W / 2, OY + 55, 40, center=True)
                self.text("W / S lub strzałki   ruch", W / 2, OY + 145, 22, center=True)
                self.text("Spacja   pauza", W / 2, OY + 190, 22, center=True)
                self.text("D   demo", W / 2, OY + 235, 22, center=True)
                self.text("R   nowy mecz       Esc   menu", W / 2, OY + 280, 22, center=True)
                self.text("H   wróć", W / 2, OY + 385, 18, TEAL, True)
            elif self.scene == Scene.MENU:
                self.text("PONG", W / 2, OY + 85, 76, center=True)
                self.text("Enter   graj", W / 2, OY + 230, 22, center=True)
                self.text("D   demo", W / 2, OY + 280, 22, center=True)
                self.text("H   sterowanie", W / 2, OY + 330, 18, MUTED, True)
            elif self.scene == Scene.PAUSE:
                self.text("Pauza", W / 2, OY + 150, 64, center=True)
                self.text("Spacja   wznów", W / 2, OY + 255, 22, TEAL, True)
            else:
                winner = f"Q / {self.agent.cell} px" if self.score[1] >= 7 else "Reguła" if self.demo else "Gracz"
                self.text(f"Wygrywa: {winner}", W / 2, OY + 150, 40, TEAL, True)
                self.text("Enter   nowy mecz", W / 2, OY + 250, 22, center=True)
        size = self.window.get_size()
        self.window.fill(BG)
        scale = min(size[0] / W, size[1] / H)
        scaled = pygame.transform.smoothscale(s, (round(W * scale), round(H * scale)))
        self.window.blit(scaled, ((size[0] - scaled.get_width()) // 2,
                                  (size[1] - scaled.get_height()) // 2))
        pygame.display.flip()


def run(model_path, demo=False, seed=2026):
    game = Game(model_path, demo, seed)
    clock = pygame.time.Clock()
    try:
        while game.events():
            game.update(clock.tick(60) / 1000)
            game.draw()
    finally:
        pygame.quit()
