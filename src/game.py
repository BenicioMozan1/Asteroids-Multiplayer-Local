# ASTEROIDE MULTIPLAYER v2.0
# This file manages the application loop, scenes, input handling, and screen drawing.

import math
import random
import sys
from dataclasses import dataclass

import pygame as pg

import config as C
from systems import World
from utils import Vec, angle_to_vec, text


P1_JOIN_KEYS = (
    pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN,
    pg.K_KP1, pg.K_KP2, pg.K_KP3, pg.K_KP4, pg.K_KP5, pg.K_KP6,
)
P2_JOIN_KEYS = (
    pg.K_w, pg.K_a, pg.K_s, pg.K_d,
    pg.K_g, pg.K_q, pg.K_h, pg.K_t, pg.K_f, pg.K_r,
)


@dataclass
class Scene:
    name: str


class Star:
    __slots__ = ("x", "y", "speed", "brightness", "size")

    def __init__(self):
        self.x = random.uniform(0, C.WIDTH)
        self.y = random.uniform(0, C.HEIGHT)
        self.speed = random.uniform(8, 38)
        self.brightness = random.randint(60, 230)
        self.size = 1 if self.brightness < 150 else 2

    def update(self, dt: float):
        self.x -= self.speed * dt
        if self.x < 0:
            self.x = C.WIDTH
            self.y = random.uniform(0, C.HEIGHT)

    def draw(self, surf: pg.Surface):
        c = (self.brightness, self.brightness, min(255, self.brightness + 25))
        if self.size == 1:
            surf.set_at((int(self.x), int(self.y)), c)
        else:
            pg.draw.circle(surf, c, (int(self.x), int(self.y)), 1)


class Lobby:
    def __init__(self, font, big, medium):
        self.font   = font
        self.big    = big
        self.medium = medium
        self.stars  = [Star() for _ in range(C.LOBBY_STAR_COUNT)]
        self.p1_joined = False
        self.p2_joined = False
        self.p1_anim   = 0.0
        self.p2_anim   = 0.0
        self.t         = 0.0
        self.ready_pulse = 0.0

    def join(self, player: int):
        if player == 1 and not self.p1_joined:
            self.p1_joined = True
            self.p1_anim   = 1.0
        elif player == 2 and not self.p2_joined:
            self.p2_joined = True
            self.p2_anim   = 1.0

    def update(self, dt: float):
        self.t += dt
        for s in self.stars:
            s.update(dt)
        if self.p1_anim > 0:
            self.p1_anim -= dt * 1.6
            if self.p1_anim < 0:
                self.p1_anim = 0
        if self.p2_anim > 0:
            self.p2_anim -= dt * 1.6
            if self.p2_anim < 0:
                self.p2_anim = 0
        if self.both_joined():
            self.ready_pulse += dt

    def both_joined(self) -> bool:
        return self.p1_joined and self.p2_joined

    def _draw_bg(self, surf: pg.Surface):
        h = C.HEIGHT
        top    = C.LOBBY_BG_TOP
        bottom = C.LOBBY_BG_BOTTOM
        bands = 40
        band_h = h // bands + 1
        for i in range(bands):
            t = i / (bands - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            pg.draw.rect(surf, (r, g, b),
                         (0, i * band_h, C.WIDTH, band_h))
        for s in self.stars:
            s.draw(surf)

    def _draw_ship_avatar(self, surf, cx, cy, angle, color, scale=1.0, alpha=255):
        r = int(C.SHIP_RADIUS * 1.8 * scale)
        dirv  = angle_to_vec(angle)
        left  = angle_to_vec(angle + 140)
        right = angle_to_vec(angle - 140)
        center = Vec(cx, cy)
        p1 = center + dirv  * r
        p2 = center + left  * r * 0.9
        p3 = center + right * r * 0.9
        layer = pg.Surface((r * 4, r * 4), pg.SRCALPHA)
        ox = r * 2 - cx
        oy = r * 2 - cy
        pts = [(p1.x + ox, p1.y + oy),
               (p2.x + ox, p2.y + oy),
               (p3.x + ox, p3.y + oy)]
        pg.draw.polygon(layer, (*color, alpha), pts, 2)
        # thruster glow
        flame = center + angle_to_vec(angle + 180) * (r * 0.8)
        pg.draw.circle(layer, (*color, alpha // 3),
                       (int(flame.x + ox), int(flame.y + oy)),
                       int(6 + 3 * math.sin(self.t * 10)))
        surf.blit(layer, (cx - r * 2, cy - r * 2))

    def _draw_slot(self, surf, x_center, joined, anim, color, label, controls):
        card_w = 340
        card_h = 360
        card_x = x_center - card_w // 2
        card_y = 200
        card = pg.Surface((card_w, card_h), pg.SRCALPHA)
        bg_alpha = 30 + (10 if joined else 0)
        pg.draw.rect(card, (*color, bg_alpha),
                     (0, 0, card_w, card_h), border_radius=12)
        border_alpha = 220 if joined else 80
        pg.draw.rect(card, (*color, border_alpha),
                     (0, 0, card_w, card_h), 2, border_radius=12)
        surf.blit(card, (card_x, card_y))

        # label
        lbl = self.medium.render(label, True, color)
        surf.blit(lbl, (x_center - lbl.get_width() // 2, card_y + 16))

        # ship avatar in center
        ship_cy = card_y + 110
        if joined:
            wobble = math.sin(self.t * 2) * 4
            scale = 1.0 + 0.25 * max(0, anim)
            self._draw_ship_avatar(surf, x_center, int(ship_cy + wobble),
                                   -90, color, scale=scale)
        else:
            self._draw_ship_avatar(surf, x_center, ship_cy,
                                   -90, color, scale=0.85, alpha=80)

        # status
        if joined:
            pulse = 0.5 + 0.5 * math.sin(self.t * 5)
            shade = (int(color[0] * (0.6 + 0.4 * pulse)),
                     int(color[1] * (0.6 + 0.4 * pulse)),
                     int(color[2] * (0.6 + 0.4 * pulse)))
            status = self.medium.render("PRONTO!", True, shade)
        else:
            blink = int(self.t * 2) % 2 == 0
            col   = (200, 200, 200) if blink else (110, 110, 110)
            status = self.font.render("PRESSIONE QUALQUER TECLA", True, col)
        surf.blit(status,
                  (x_center - status.get_width() // 2, card_y + 180))

        # controls (only if joined)
        y_ctrl = card_y + 215
        if joined:
            for key, action in controls:
                line = self.font.render(f"{key:<10} {action}", True,
                                        (200, 200, 200))
                surf.blit(line, (card_x + 24, y_ctrl))
                y_ctrl += 18

    def draw(self, surf: pg.Surface):
        self._draw_bg(surf)

        # title
        title = self.big.render("ASTEROIDS", True, C.WHITE)
        glow  = pg.Surface((title.get_width() + 40, title.get_height() + 40),
                           pg.SRCALPHA)
        for i in range(6):
            a = 20 - i * 3
            pg.draw.rect(glow, (120, 120, 255, a),
                         (i * 2, i * 2, title.get_width() + 40 - i * 4,
                          title.get_height() + 40 - i * 4), border_radius=8)
        cx = C.WIDTH // 2
        surf.blit(glow, (cx - glow.get_width() // 2, 60))
        surf.blit(title, (cx - title.get_width() // 2, 78))

        sub = self.font.render("— LOBBY MULTIPLAYER LOCAL —",
                               True, (180, 180, 220))
        surf.blit(sub, (cx - sub.get_width() // 2, 148))

        # divider
        pg.draw.line(surf, (60, 60, 90),
                     (80, 180), (C.WIDTH - 80, 180), 1)

        p1_controls = [
            ("← →",  "Virar"),
            ("↑",    "Acelerar"),
            ("KP1",  "Tiro"),
            ("KP2",  "Hyperspace"),
            ("KP3",  "Shield"),
            ("KP4",  "Spread"),
            ("KP5",  "Tether"),
            ("KP6",  "Charge ⚡"),
        ]
        p2_controls = [
            ("A D",  "Virar"),
            ("W",    "Acelerar"),
            ("G",    "Tiro"),
            ("Q",    "Hyperspace"),
            ("H",    "Shield"),
            ("T",    "Spread"),
            ("F",    "Tether"),
            ("R",    "Charge ⚡"),
        ]

        self._draw_slot(surf, cx - 200, self.p1_joined, self.p1_anim,
                        C.SHIP_P1_COLOR, "JOGADOR 1", p1_controls)
        self._draw_slot(surf, cx + 200, self.p2_joined, self.p2_anim,
                        C.SHIP_P2_COLOR, "JOGADOR 2", p2_controls)

        # bottom hint
        y_btm = 580
        if self.both_joined():
            pulse = 0.5 + 0.5 * math.sin(self.ready_pulse * 4)
            col   = (int(255 * (0.5 + 0.5 * pulse)),
                     int(255 * (0.5 + 0.5 * pulse)),
                     int(120 + 80 * pulse))
            ready = self.medium.render("PRESSIONE ENTER PARA COMEÇAR",
                                       True, col)
            surf.blit(ready, (cx - ready.get_width() // 2, y_btm))
        else:
            wait = self.font.render(
                "Aguardando jogadores... cada um pressiona suas teclas",
                True, (160, 160, 200))
            surf.blit(wait, (cx - wait.get_width() // 2, y_btm + 6))

        # mechanics teaser
        pg.draw.line(surf, (60, 60, 90),
                     (80, 625), (C.WIDTH - 80, 625), 1)
        mechs = [
            ("⚡ Charge Shot", "Segure KP6 / R — beam mortal", C.CHARGE_BEAM_GLOW),
            ("👑 Cursed Crown", "+50% score / dano dobrado / roubável", C.CROWN_COLOR),
            ("🍷 Sabotagem",   "Vire o oponente bêbado", C.SABOTAGE_COLOR),
        ]
        x = 100
        for name, desc, col in mechs:
            n = self.font.render(name, True, col)
            d = self.font.render(desc, True, (150, 150, 170))
            surf.blit(n, (x, 640))
            surf.blit(d, (x, 660))
            x += 260


class Game:
    def __init__(self):
        pg.init()
        if C.RANDOM_SEED is not None:
            random.seed(C.RANDOM_SEED)
        self.screen = pg.display.set_mode((C.WIDTH, C.HEIGHT))
        pg.display.set_caption("Asteroides Multiplayer")
        self.clock  = pg.time.Clock()
        self.font   = pg.font.SysFont("consolas", 18)
        self.big    = pg.font.SysFont("consolas", 48)
        self.medium = pg.font.SysFont("consolas", 28)
        self.scene  = Scene("lobby")
        self.lobby  = Lobby(self.font, self.big, self.medium)
        self.world  = World(self.font)
        self.go_fade      = 0.0
        self.final_score1 = 0
        self.final_score2 = 0
        
        pg.joystick.init()
        self.joysticks = {}
        for i in range(pg.joystick.get_count()):
            joy = pg.joystick.Joystick(i)
            joy.init()
            self.joysticks[joy.get_instance_id()] = joy

    # ─────────────────────────────────────────────────────────
    #  Main loop
    # ─────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(C.FPS) / 1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    pg.quit()
                    sys.exit(0)

                if e.type == pg.JOYDEVICEADDED:
                    joy = pg.joystick.Joystick(e.device_index)
                    joy.init()
                    self.joysticks[joy.get_instance_id()] = joy

                if e.type == pg.JOYDEVICEREMOVED:
                    if e.instance_id in self.joysticks:
                        del self.joysticks[e.instance_id]

                if e.type == pg.KEYDOWN:
                    if e.key == pg.K_ESCAPE:
                        if self.scene.name in ("game_over", "play"):
                            self.scene = Scene("lobby")
                            self.lobby = Lobby(self.font, self.big, self.medium)
                        else:
                            pg.quit()
                            sys.exit(0)

                    elif self.scene.name == "lobby":
                        if e.key in P1_JOIN_KEYS:
                            self.lobby.join(1)
                        if e.key in P2_JOIN_KEYS:
                            self.lobby.join(2)
                        if self.lobby.both_joined() and e.key in (
                                pg.K_RETURN, pg.K_SPACE, pg.K_KP_ENTER):
                            self.world = World(self.font)
                            self.scene = Scene("play")

                    elif self.scene.name == "game_over":
                        if e.key in (pg.K_RETURN, pg.K_SPACE):
                            self.world   = World(self.font)
                            self.go_fade = 0.0
                            self.scene   = Scene("play")

                    elif self.scene.name == "play":
                        if e.key == pg.K_KP1:
                            self.world.try_fire(1)
                        if e.key == pg.K_KP2:
                            self.world.hyperspace(1)
                        if e.key == pg.K_KP3:
                            self.world.try_shield(1)
                        if e.key == pg.K_KP4:
                            self.world.try_spread(1)
                        if e.key == pg.K_g:
                            self.world.try_fire(2)
                        if e.key == pg.K_q:
                            self.world.hyperspace(2)
                        if e.key == pg.K_h:
                            self.world.try_shield(2)
                        if e.key == pg.K_t:
                            self.world.try_spread(2)

                if e.type == pg.JOYBUTTONDOWN:
                    joy_list = list(self.joysticks.values())
                    player = None
                    if len(joy_list) > 0 and e.instance_id == joy_list[0].get_instance_id():
                        player = 1
                    elif len(joy_list) > 1 and e.instance_id == joy_list[1].get_instance_id():
                        player = 2

                    if player is not None:
                        if self.scene.name == "lobby":
                            if e.button == 0:  # A button to join
                                self.lobby.join(player)
                            if self.lobby.both_joined() and e.button == 7:  # Start button
                                self.world = World(self.font)
                                self.scene = Scene("play")
                        
                        elif self.scene.name == "game_over":
                            if e.button == 7:  # Start button
                                self.world   = World(self.font)
                                self.go_fade = 0.0
                                self.scene   = Scene("play")

                        elif self.scene.name == "play":
                            if e.button == 2:  # X
                                self.world.try_fire(player)
                            if e.button == 1:  # B
                                self.world.hyperspace(player)
                            if e.button == 3:  # Y
                                self.world.try_shield(player)
                            if e.button == 5:  # RB
                                self.world.try_spread(player)

            keys = pg.key.get_pressed()
            self.screen.fill(C.BLACK)

            if self.scene.name == "lobby":
                self.lobby.update(dt)
                self.lobby.draw(self.screen)
            elif self.scene.name == "play":
                self.world.update(dt, keys, self.joysticks)
                self.world.draw(self.screen, self.font)
                if self.world.game_over:
                    self.final_score1 = self.world.score1
                    self.final_score2 = self.world.score2
                    self.go_fade      = 0.0
                    self.scene        = Scene("game_over")
            elif self.scene.name == "game_over":
                self.go_fade += dt
                self.draw_game_over()

            pg.display.flip()

    # ─────────────────────────────────────────────────────────
    #  Game-over screen
    # ─────────────────────────────────────────────────────────

    def draw_game_over(self):
        alpha   = min(255, int(255 * self.go_fade / C.GAME_OVER_FADE_DURATION))
        overlay = pg.Surface((C.WIDTH, C.HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))
        if alpha < 60:
            return

        cx = C.WIDTH  // 2
        cy = C.HEIGHT // 2

        s1, s2 = self.final_score1, self.final_score2
        diff    = abs(s1 - s2)

        if diff < 100:
            result_surf = self.big.render("EMPATE!", True, C.WHITE)
            self.screen.blit(result_surf,
                             (cx - result_surf.get_width() // 2, cy - 140))
        else:
            winner    = 1 if s1 > s2 else 2
            w_color   = C.SHIP_P1_COLOR if winner == 1 else C.SHIP_P2_COLOR
            w_str     = f"JOGADOR {winner} VENCEU!"
            w_surf    = self.big.render(w_str, True, w_color)
            self.screen.blit(w_surf, (cx - w_surf.get_width() // 2, cy - 140))

        gap = 60
        p1_label = self.medium.render("JOGADOR 1", True, C.SHIP_P1_COLOR)
        p1_score = self.medium.render(f"{s1:06d}", True, C.SHIP_P1_COLOR)
        self.screen.blit(p1_label, (cx - gap - p1_label.get_width(), cy - 60))
        self.screen.blit(p1_score, (cx - gap - p1_score.get_width(), cy - 20))

        pg.draw.line(self.screen, C.GRAY,
                     (cx, cy - 70), (cx, cy + 10), 1)

        p2_label = self.medium.render("JOGADOR 2", True, C.SHIP_P2_COLOR)
        p2_score = self.medium.render(f"{s2:06d}", True, C.SHIP_P2_COLOR)
        self.screen.blit(p2_label, (cx + gap, cy - 60))
        self.screen.blit(p2_score, (cx + gap, cy - 20))

        text(self.screen, self.font,
             "Enter / Espaco: jogar novamente",
             cx - 150, cy + 50)
        text(self.screen, self.font,
             "ESC: lobby principal",
             cx - 90, cy + 80)
