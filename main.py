"""One More Scroll — one codebase for Windows and pygbag/WebAssembly."""
import asyncio
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import random
import sys

import pygame

W, H = 540, 820
NAVY = (9, 15, 31)
PANEL = (18, 29, 49)
LINE = (37, 54, 76)
WHITE = (230, 240, 247)
DIM = (139, 160, 183)
GREEN = (111, 249, 174)
PINK = (255, 112, 154)
BLUE = (113, 193, 255)
WEB = sys.platform == "emscripten"
PLAYER_Y = 664


class Storage:
    def __init__(self, path=None):
        self.available = True
        self.path = Path(path) if path else Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "OneMoreScroll" / "best.json"

    def load(self):
        try:
            if WEB:
                import platform
                raw = platform.window.localStorage.getItem("one-more-scroll-best")
                data = json.loads(str(raw)) if raw else {}
            else:
                data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            value = data.get("best", 0)
            return value if type(value) is int and 0 <= value <= 10000000 else 0
        except Exception:
            self.available = False
            return 0

    def save(self, best):
        try:
            raw = json.dumps({"best": best})
            if WEB:
                import platform
                platform.window.localStorage.setItem("one-more-scroll-best", raw)
            else:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text(raw, encoding="utf-8")
                temporary.replace(self.path)
        except Exception:
            self.available = False


@dataclass
class Drop:
    kind: str
    x: float
    y: float
    speed: float
    label: str

    @property
    def rect(self):
        width = 112 if self.kind == "hazard" else 82
        return pygame.Rect(round(self.x - width / 2), round(self.y - 20), width, 40)


class Round:
    """All timers advance only through update; rendering never mutates gameplay."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.x = W / 2
        self.elapsed = 0.0
        self.score = 0
        self.lives = 3
        self.combo = 1
        self.pickups = 0
        self.mute = 0.0
        self.invulnerable = 0.0
        self.spawn_in = 0.35
        self.power_in = 8.0
        self.drops = []
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.over = False
        self.paused = False

    @property
    def player_rect(self):
        return pygame.Rect(round(self.x - 23), PLAYER_Y - 19, 46, 38)

    def burst(self, x, y, color, message):
        for _ in range(10):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(35, 125)
            self.particles.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed, 0.5, color])
        self.popups.append([x, y - 25, message, color, 0.8])

    def collect(self, item):
        if item.kind == "focus":
            points = 10 * self.combo
            self.score += points
            self.pickups += 1
            self.burst(item.x, item.y, GREEN, f"+{points}")
            self.combo = min(5, self.combo + 1)
        elif item.kind == "mute":
            self.mute = 3.0
            self.burst(item.x, item.y, BLUE, "MUTED / 3s")
        elif self.mute <= 0 and self.invulnerable <= 0:
            self.lives -= 1
            self.combo = 1
            self.invulnerable = 1.3
            self.shake = 0.22
            self.burst(self.x, PLAYER_Y, PINK, "DISTRACTED")

    def update(self, dt, direction=0):
        if self.paused or self.over:
            return
        dt = min(max(dt, 0), 0.05)
        self.elapsed = min(45.0, round(self.elapsed + dt, 10))
        self.x = max(31, min(W - 31, self.x + direction * 360 * dt))
        self.mute = max(0, round(self.mute - dt, 10))
        self.invulnerable = max(0, round(self.invulnerable - dt, 10))
        self.shake = max(0, self.shake - dt)
        self.spawn_in -= dt
        self.power_in -= dt
        progress = self.elapsed / 45
        if self.spawn_in <= 0:
            kind = "focus" if self.rng.random() < 0.44 else "hazard"
            self.drops.append(Drop(kind, self.rng.uniform(66, W - 66), -28, 155 + 135 * progress, "FOCUS" if kind == "focus" else self.rng.choice(["SPAM", "REELS", "PING!", "CLICKBAIT"])))
            self.spawn_in += 0.70 - 0.32 * progress
        if self.power_in <= 0:
            self.drops.append(Drop("mute", self.rng.uniform(66, W - 66), -28, 150 + 80 * progress, "MUTE"))
            self.power_in = self.rng.uniform(9, 12)
        for item in self.drops[:]:
            item.y += item.speed * dt
            if item.rect.colliderect(self.player_rect):
                self.collect(item)
                self.drops.remove(item)
            elif item.y > H + 30:
                self.drops.remove(item)
        for p in self.particles[:]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0:
                self.particles.remove(p)
        for p in self.popups[:]:
            p[1] -= 34 * dt
            p[4] -= dt
            if p[4] <= 0:
                self.popups.remove(p)
        self.over = self.lives <= 0 or self.elapsed >= 45


class Game:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        pygame.display.set_caption("One More Scroll")
        self.canvas = pygame.Surface((W, H))
        self.fonts = {size: pygame.font.Font(None, size) for size in (19, 22, 25, 28, 34, 42, 62, 76)}
        self.storage = Storage()
        self.best = self.storage.load()
        self.round = Round()
        self.state = "menu"
        self.keys = set()
        self.pointers = {}
        self.shake_enabled = True
        self.running = True
        self.focused = True
        self.buttons = {}
        self.viewport = pygame.Rect(0, 0, W, H)
        if WEB:
            import platform
            platform.window.canvas.style.touchAction = "none"

    def text(self, value, x, y, size=25, color=WHITE, center=False):
        rendered = self.fonts[size].render(str(value), True, color)
        rect = rendered.get_rect(center=(x, y)) if center else rendered.get_rect(topleft=(x, y))
        self.canvas.blit(rendered, rect)

    def panel(self, rect, color=PANEL, border=LINE):
        pygame.draw.rect(self.canvas, color, rect, border_radius=14)
        pygame.draw.rect(self.canvas, border, rect, width=1, border_radius=14)

    def button(self, name, label, rect, primary=False):
        rect = pygame.Rect(rect)
        self.buttons[name] = rect
        self.panel(rect, GREEN if primary else PANEL, GREEN if primary else LINE)
        self.text(label, rect.centerx, rect.centery, 28, NAVY if primary else WHITE, True)

    def clear_input(self):
        self.keys.clear()
        self.pointers.clear()

    def start(self):
        self.round.reset()
        self.state = "play"
        self.clear_input()

    def pause(self):
        if self.state == "play":
            self.round.paused = True
            self.clear_input()

    def action(self, name):
        if name in ("play", "again"):
            self.start()
        elif name == "pause":
            self.pause()
        elif name == "resume" and self.focused:
            self.round.paused = False
            self.clear_input()
        elif name == "menu":
            self.state = "menu"
            self.clear_input()
        elif name == "shake":
            self.shake_enabled = not self.shake_enabled
        elif name == "quit":
            self.running = False

    def logical(self, pos):
        rect = self.viewport
        return ((pos[0] - rect.x) * W / rect.w, (pos[1] - rect.y) * H / rect.h)

    def pointer_down(self, identifier, position):
        if not (0 <= position[0] < W and 0 <= position[1] < H):
            return
        for name, rect in list(self.buttons.items()):
            if rect.collidepoint(position):
                self.action(name)
                return
        if self.state == "play" and not self.round.paused and position[1] >= 717:
            self.pointers[identifier] = -1 if position[0] < W / 2 else 1

    def event(self, event):
        if event.type == pygame.QUIT:
            if WEB:
                self.action("menu")
            else:
                self.running = False
        elif event.type == pygame.WINDOWFOCUSLOST or (event.type == pygame.ACTIVEEVENT and event.gain == 0 and event.state & 2):
            self.focused = False
            self.pause()
            self.clear_input()
        elif event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.action("resume" if self.round.paused else "pause")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state in ("menu", "over"):
                self.start()
            elif self.focused and self.state == "play" and not self.round.paused:
                self.keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self.keys.discard(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not getattr(event, "touch", False):
            self.pointer_down("mouse", self.logical(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP:
            self.pointers.pop("mouse", None)
        elif event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            pos = self.logical((event.x * self.screen.get_width(), event.y * self.screen.get_height()))
            if event.type == pygame.FINGERDOWN:
                self.pointer_down(event.finger_id, pos)
            elif event.finger_id in self.pointers:
                self.pointers[event.finger_id] = -1 if pos[0] < W / 2 else 1
        elif event.type == pygame.FINGERUP:
            self.pointers.pop(event.finger_id, None)

    def update(self, dt):
        if self.state != "play":
            return
        direction = int(bool(self.keys & {pygame.K_RIGHT, pygame.K_d})) - int(bool(self.keys & {pygame.K_LEFT, pygame.K_a}))
        direction = max(-1, min(1, direction + sum(self.pointers.values())))
        self.round.update(dt, direction)
        if self.round.over:
            self.state = "over"
            self.clear_input()
            if self.round.score > self.best:
                self.best = self.round.score
                self.storage.save(self.best)

    def background(self):
        self.canvas.fill(NAVY)
        for y in range(0, H, 40):
            pygame.draw.line(self.canvas, (14, 23, 40), (0, y), (W, y))
        for x in range(0, W, 40):
            pygame.draw.line(self.canvas, (14, 23, 40), (x, 0), (x, H))

    def draw_drop(self, item):
        color = GREEN if item.kind == "focus" else BLUE if item.kind == "mute" else PINK
        rect = item.rect
        self.panel(rect, PANEL, color)
        if item.kind == "hazard":
            self.text("!", rect.x + 12, rect.y + 9, 25, color)
            self.text(item.label, rect.centerx + 6, rect.centery, 19, color, True)
        else:
            self.text("+" if item.kind == "focus" else "~", rect.x + 8, rect.y + 9, 25, color)
            self.text(item.label, rect.centerx + 9, rect.centery, 19, color, True)

    def draw_play(self):
        r = self.round
        # Clip falling objects to the arena so the HUD and controls stay readable.
        self.canvas.set_clip((0, 142, W, 568))
        for item in r.drops:
            self.draw_drop(item)
        pygame.draw.line(self.canvas, LINE, (24, 698), (W - 24, 698))
        color = BLUE if r.mute > 0 else GREEN
        if r.mute > 0 or r.invulnerable > 0:
            pygame.draw.circle(self.canvas, color if r.mute > 0 else PINK, (round(r.x), PLAYER_Y), 36, 2)
        self.panel((r.x - 26, PLAYER_Y - 21, 52, 42), PANEL, color)
        pygame.draw.polygon(self.canvas, color, [(r.x, PLAYER_Y - 12), (r.x - 12, PLAYER_Y + 8), (r.x, PLAYER_Y + 3), (r.x + 12, PLAYER_Y + 8)])
        for p in r.particles:
            pygame.draw.circle(self.canvas, p[5], (round(p[0]), round(p[1])), max(1, round(3 * p[4] / 0.5)))
        for p in r.popups:
            self.text(p[2], p[0], p[1], 22, p[3], True)
        self.canvas.set_clip(None)
        self.text("ONE MORE SCROLL", 24, 20, 22, DIM)
        self.button("pause", "II", (466, 14, 50, 42))
        self.text(f"{r.score:04d}", 24, 52, 42)
        self.text(f"{math.ceil(45 - r.elapsed):02d}s", 276, 56, 34, BLUE)
        for i in range(3):
            pygame.draw.circle(self.canvas, PINK if i < r.lives else LINE, (394 + i * 22, 71), 7)
        self.text(f"{r.combo}x COMBO", 24, 109, 22, GREEN)
        status = f"MUTED  {r.mute:.1f}s" if r.mute > 0 else "STAY IN THE MOMENT"
        self.text(status, 370, 119, 19, BLUE if r.mute > 0 else DIM, True)
        pygame.draw.rect(self.canvas, LINE, (24, 140, 492, 3), border_radius=1)
        pygame.draw.rect(self.canvas, BLUE, (24, 140, round(492 * (1 - r.elapsed / 45)), 3), border_radius=1)
        self.panel((24, 726, 238, 65))
        self.panel((278, 726, 238, 65))
        self.text("<    LEFT / A", 143, 759, 25, DIM, True)
        self.text("RIGHT / D    >", 397, 759, 25, DIM, True)
        if r.paused:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((5, 10, 23, 225))
            self.canvas.blit(overlay, (0, 0))
            self.buttons.clear()
            self.text("TAKE A BREATH.", W / 2, 250, 42, WHITE, True)
            self.text("Everything can wait.", W / 2, 295, 25, DIM, True)
            self.button("resume", "Resume", (90, 349, 360, 62), True)
            self.button("menu", "Return to menu", (90, 427, 360, 55))
            self.button("shake", f"Screen shake: {'ON' if self.shake_enabled else 'OFF'}", (90, 498, 360, 55))

    def draw_menu(self):
        self.text("A SMALL ESCAPE FROM THE FEED", W / 2, 96, 22, BLUE, True)
        self.text("ONE MORE", W / 2, 177, 62, WHITE, True)
        self.text("SCROLL", W / 2, 237, 76, GREEN, True)
        self.text("Less scrolling. More living.", W / 2, 302, 28, DIM, True)
        self.panel((38, 350, 464, 184))
        self.text("01", 58, 375, 25, GREEN)
        self.text("Collect + FOCUS. Build a 5x combo.", 104, 375, 25)
        self.text("02", 58, 422, 25, PINK)
        self.text("Dodge ! distractions. Three lives.", 104, 422, 25)
        self.text("03", 58, 469, 25, BLUE)
        self.text("Catch ~ MUTE for 3s of immunity.", 104, 469, 25)
        self.button("play", "Find your focus   >", (70, 562, 400, 66), True)
        self.text("45 SECONDS  /  ARROWS OR A + D", W / 2, 658, 22, DIM, True)
        self.text("On a phone: hold the left / right pads", W / 2, 687, 22, DIM, True)
        self.button("shake", f"Screen shake: {'ON' if self.shake_enabled else 'OFF'}", (70, 718, 290, 48))
        if not WEB:
            self.button("quit", "Quit", (376, 718, 94, 48))
        self.text(f"PERSONAL BEST  {self.best}", W / 2, 794, 19, BLUE, True)

    def draw_over(self):
        r = self.round
        self.text("SESSION COMPLETE", W / 2, 132, 22, BLUE, True)
        self.text("YOU LOGGED OFF." if r.lives > 0 else "THE FEED GOT YOU.", W / 2, 199, 42, WHITE, True)
        self.text("A fresh start is one tap away.", W / 2, 249, 25, DIM, True)
        self.panel((65, 304, 410, 226))
        self.text("FOCUS SCORE", W / 2, 338, 22, DIM, True)
        self.text(r.score, W / 2, 396, 76, GREEN, True)
        self.text(f"PERSONAL BEST  {self.best}", W / 2, 461, 25, BLUE, True)
        self.text(f"{r.pickups} pickups  /  {r.elapsed:.1f}s focused", W / 2, 499, 22, DIM, True)
        self.button("again", "Play again   >", (70, 570, 400, 66), True)
        self.button("menu", "Return to menu", (70, 653, 400, 55))
        if not self.storage.available:
            self.text("Storage unavailable: best kept this session.", W / 2, 754, 22, DIM, True)

    def draw(self):
        self.buttons.clear()
        self.background()
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "over":
            self.draw_over()
        else:
            self.draw_play()
        sw, sh = self.screen.get_size()
        scale = min(sw / W, sh / H)
        size = (max(1, round(W * scale)), max(1, round(H * scale)))
        self.viewport = pygame.Rect((sw - size[0]) // 2, (sh - size[1]) // 2, *size)
        self.screen.fill((4, 8, 18))
        offset = (0, 0)
        if self.state == "play" and not self.round.paused and self.round.shake > 0 and self.shake_enabled:
            offset = (round(math.sin(self.round.shake * 110) * 3 * scale), 0)
        self.screen.blit(pygame.transform.smoothscale(self.canvas, size), self.viewport.move(*offset))
        pygame.display.flip()


async def main():
    game = Game()
    clock = pygame.time.Clock()
    game.draw()
    smoke_frames = int(os.environ.get("OMS_SMOKE_FRAMES", "0")) if not WEB else 0
    frames = 0
    while game.running:
        frame_start = asyncio.get_running_loop().time()
        dt = min(clock.tick(60) / 1000, 0.05) if not WEB else min(clock.tick(0) / 1000, 0.05)
        if WEB:
            import platform
            if platform.document.hidden:
                game.pause()
                game.clear_input()
        for event in pygame.event.get():
            game.event(event)
        game.update(dt)
        game.draw()
        frames += 1
        if smoke_frames and frames >= smoke_frames:
            game.running = False
        if WEB:
            # Yield rather than blocking the browser thread to cap at 60 FPS.
            await asyncio.sleep(max(0, 1 / 60 - (asyncio.get_running_loop().time() - frame_start)))
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
