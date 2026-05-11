# ASTEROIDE MULTIPLAYER v2.0
# This file manages the application loop, scenes, input handling, and screen drawing.

import random
import sys
from dataclasses import dataclass

import pygame as pg

import config as C
from systems import World
from utils import text


@dataclass
class Scene:
    name: str


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
        self.scene  = Scene("menu")
        self.world  = World(self.font)
        self.go_fade      = 0.0
        self.final_score1 = 0
        self.final_score2 = 0

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

                if e.type == pg.KEYDOWN:
                    # ── Global ──
                    if e.key == pg.K_ESCAPE:
                        if self.scene.name == "game_over":
                            self.scene = Scene("menu")
                        else:
                            pg.quit()
                            sys.exit(0)

                    # ── Menu: any key starts game ──
                    elif self.scene.name == "menu":
                        self.world = World(self.font)
                        self.scene = Scene("play")

                    # ── Game over: restart ──
                    elif self.scene.name == "game_over":
                        if e.key in (pg.K_RETURN, pg.K_SPACE):
                            self.world   = World(self.font)
                            self.go_fade = 0.0
                            self.scene   = Scene("play")

                    # ── Play: event-based actions ──
                    elif self.scene.name == "play":
                        # P1: setas (movimento) + numpad 1-5 (ações)
                        # KP1 = tiro, KP2 = hyperspace, KP3 = shield
                        # KP4 = spread shot, KP5 = tether
                        if e.key == pg.K_KP1:
                            self.world.try_fire(1)
                        if e.key == pg.K_KP2:
                            self.world.hyperspace(1)
                        if e.key == pg.K_KP3:
                            self.world.try_shield(1)
                        if e.key == pg.K_KP4:
                            self.world.try_spread(1)
                        # P2
                        if e.key == pg.K_g:
                            self.world.try_fire(2)
                        if e.key == pg.K_q:
                            self.world.hyperspace(2)
                        if e.key == pg.K_h:
                            self.world.try_shield(2)
                        if e.key == pg.K_t:
                            self.world.try_spread(2)

            keys = pg.key.get_pressed()
            self.screen.fill(C.BLACK)

            if self.scene.name == "menu":
                self.draw_menu()
            elif self.scene.name == "play":
                self.world.update(dt, keys)
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
    #  Screens
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

        # score cards side by side
        gap = 60
        # P1
        p1_label = self.medium.render("JOGADOR 1", True, C.SHIP_P1_COLOR)
        p1_score = self.medium.render(f"{s1:06d}", True, C.SHIP_P1_COLOR)
        self.screen.blit(p1_label, (cx - gap - p1_label.get_width(), cy - 60))
        self.screen.blit(p1_score, (cx - gap - p1_score.get_width(), cy - 20))

        # divider
        pg.draw.line(self.screen, C.GRAY,
                     (cx, cy - 70), (cx, cy + 10), 1)

        # P2
        p2_label = self.medium.render("JOGADOR 2", True, C.SHIP_P2_COLOR)
        p2_score = self.medium.render(f"{s2:06d}", True, C.SHIP_P2_COLOR)
        self.screen.blit(p2_label, (cx + gap, cy - 60))
        self.screen.blit(p2_score, (cx + gap, cy - 20))

        text(self.screen, self.font,
             "Enter / Espaco: jogar novamente",
             cx - 150, cy + 50)
        text(self.screen, self.font,
             "ESC: menu principal",
             cx - 90, cy + 80)

    def draw_menu(self):
        cx = C.WIDTH  // 2
        cy = C.HEIGHT // 2

        # Title
        title = self.big.render("ASTEROIDS", True, C.WHITE)
        self.screen.blit(title, (cx - title.get_width() // 2, 80))

        sub = self.font.render("MULTIPLAYER LOCAL", True, C.GRAY)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 140))

        # Divider
        pg.draw.line(self.screen, (60, 60, 60),
                     (80, 170), (C.WIDTH - 80, 170), 1)

        # Column headers
        p1_h = self.font.render("JOGADOR 1", True, C.SHIP_P1_COLOR)
        p2_h = self.font.render("JOGADOR 2", True, C.SHIP_P2_COLOR)
        col1_x = cx - 300
        col2_x = cx + 60
        self.screen.blit(p1_h, (col1_x, 185))
        self.screen.blit(p2_h, (col2_x, 185))

        p1_controls = [
            ("← →",    "Virar"),
            ("↑",       "Acelerar"),
            ("KP 1",    "Tiro"),
            ("KP 2",    "Hyperspace"),
            ("KP 3",    "Shield"),
            ("KP 4",    "Spread shot"),
            ("KP 5",    "Tether ⚡"),
        ]
        p2_controls = [
            ("A D",   "Virar"),
            ("W",     "Acelerar"),
            ("G",     "Tiro"),
            ("Q",     "Hyperspace"),
            ("H",     "Shield"),
            ("T",     "Spread shot"),
            ("F",     "Tether ⚡"),
        ]

        for i, ((key1, act1), (key2, act2)) in enumerate(
                zip(p1_controls, p2_controls)):
            y = 215 + i * 22
            line1 = self.font.render(f"{key1:<10} {act1}", True, C.SHIP_P1_COLOR)
            line2 = self.font.render(f"{key2:<6} {act2}", True, C.SHIP_P2_COLOR)
            self.screen.blit(line1, (col1_x, y))
            self.screen.blit(line2, (col2_x, y))

        # Tether hint
        pg.draw.line(self.screen, (60, 60, 60),
                     (80, 380), (C.WIDTH - 80, 380), 1)

        mechs = [
            ("⚡ Tether",
             "Segurem Z+F ao mesmo tempo — a corda corta asteroides e pontua para os dois"),
            ("💀 Kill Steal",
             "Dar o kill final num asteroide trabalhado pelo adversario rende bonus de 30%"),
            ("👻 Ghost Rescue",
             "Sem vidas? Vira fantasma por 12s — o parceiro passa por cima para resgatar (-500pts)"),
        ]
        for j, (name, desc) in enumerate(mechs):
            y = 395 + j * 42
            n_surf = self.font.render(name, True, (255, 220, 80))
            d_surf = self.font.render(desc, True, C.GRAY)
            self.screen.blit(n_surf, (cx - n_surf.get_width() // 2, y))
            self.screen.blit(d_surf, (cx - d_surf.get_width() // 2, y + 18))

        pg.draw.line(self.screen, (60, 60, 60),
                     (80, 527), (C.WIDTH - 80, 527), 1)

        start = self.font.render("Pressione qualquer tecla para comecar",
                                 True, C.WHITE)
        self.screen.blit(start, (cx - start.get_width() // 2, 545))
