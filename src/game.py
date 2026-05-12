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
        self.font = font
        self.big = big
        self.medium = medium
        self.stars = [Star() for _ in range(C.LOBBY_STAR_COUNT)]
        self.joined = [False, False, False, False]
        self.t = 0.0

    def join(self, player_idx: int):
        if 0 <= player_idx < 4:
            self.joined[player_idx] = True

    def update(self, dt: float):
        self.t += dt
        for s in self.stars: s.update(dt)

    def get_joined_count(self):
        return sum(self.joined)

    def draw(self, surf: pg.Surface):
        for s in self.stars: s.draw(surf)
        
        title = self.big.render("ASTEROIDS 4-PLAYERS", True, C.WHITE)
        surf.blit(title, (C.WIDTH // 2 - title.get_width() // 2, 50))

        for i in range(4):
            x = 60 + i * 220
            color = [C.SHIP_P1_COLOR, C.SHIP_P2_COLOR, C.SHIP_P3_COLOR, C.SHIP_P4_COLOR][i]
            rect = pg.Rect(x, 150, 200, 300)
            pg.draw.rect(surf, color, rect, 2 if self.joined[i] else 1, border_radius=10)
            
            lbl = self.font.render(f"P{i+1}", True, color)
            surf.blit(lbl, (x + 90, 160))
            
            status = "PRONTO!" if self.joined[i] else "PRESSIONE A"
            st_surf = self.font.render(status, True, color if self.joined[i] else C.GRAY)
            surf.blit(st_surf, (x + 100 - st_surf.get_width()//2, 280))

class Game:
    def __init__(self):
        pg.init()
        pg.joystick.init()
        # Inicializa e guarda a referência dos joysticks
        self.joysticks = [pg.joystick.Joystick(x) for x in range(pg.joystick.get_count())]
        
        if C.RANDOM_SEED is not None:
            random.seed(C.RANDOM_SEED)
            
        self.screen = pg.display.set_mode((C.WIDTH, C.HEIGHT))
        pg.display.set_caption("Asteroides Multiplayer")
        self.clock = pg.time.Clock()
        self.font = pg.font.SysFont("consolas", 18)
        self.big = pg.font.SysFont("consolas", 48)
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
            
            # 1. LIMPEZA DE TELA (Fundamental para evitar rastros)
            self.screen.fill(C.BLACK)

            # 2. PROCESSAMENTO DE EVENTOS
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
                    
                    # Teclado como backup para iniciar
                    if e.type == pg.KEYDOWN:
                        if e.key in (pg.K_RETURN, pg.K_SPACE) and self.lobby.get_joined_count() >= 2:
                            self.world = World(self.font, self.lobby.joined)
                            self.scene = Scene("play")
                
                elif self.scene.name == "play":
                    if e.type == pg.JOYBUTTONDOWN:
                        p_id = e.joy + 1
                        if e.button == 0: self.world.try_fire(p_id)
                        if e.button == 1: self.world.hyperspace(p_id)
                        if e.button == 2: self.world.try_shield(p_id)
                        if e.button == 3: self.world.try_spread(p_id)

                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()

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
            
            pg.display.flip()