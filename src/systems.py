# ASTEROIDE MULTIPLAYER v2.0
# This file coordinates world state, spawning, collisions, scoring, and progression.

import math
from random import uniform

import pygame as pg

import config as C
from sprites import (
    Asteroid, BossBullet, PowerAsteroid,
    Ship, GhostShip, TetherLine, FloatingText,
    UFO, BlackHole, ClockItem, LifeItem,
)
from utils import Vec, rand_edge_pos, rand_unit_vec, segment_circle_collision


class World:
    def __init__(self, font: pg.font.Font):
        # ── ships ──────────────────────────────────────────────
        self.ship1 = Ship(Vec(C.SHIP1_START), player_id=1)
        self.ship2 = Ship(Vec(C.SHIP2_START), player_id=2)
        # point noses toward center
        self.ship1.angle = 0.0
        self.ship2.angle = 180.0

        # ── bullets (separate groups for kill-steal tracking) ──
        self.bullets1   = pg.sprite.Group()
        self.bullets2   = pg.sprite.Group()
        self.ufo_bullets = pg.sprite.Group()

        # ── enemies & world ────────────────────────────────────
        self.asteroids     = pg.sprite.Group()
        self.power_asteroids = pg.sprite.Group()
        self.ufos          = pg.sprite.Group()
        self.black_hole    = None
        self.clock_items   = pg.sprite.Group()
        self.life_items    = pg.sprite.Group()

        # ── scores / lives ─────────────────────────────────────
        self.score1 = 0
        self.score2 = 0
        self.lives1 = C.START_LIVES
        self.lives2 = C.START_LIVES

        # ── ghost rescue ───────────────────────────────────────
        self.ghost1: GhostShip | None = None
        self.ghost2: GhostShip | None = None

        # ── tether ─────────────────────────────────────────────
        self.tether        = TetherLine()
        self.tether_active = False
        self.tether_timer  = 0.0
        self.tether_cool1  = 0.0
        self.tether_cool2  = 0.0

        # ── timers ─────────────────────────────────────────────
        self.bh_timer    = uniform(C.BH_TIMER_MIN, C.BH_TIMER_MAX)
        self.bh_duration = 0.0
        self.ufo_timer   = C.UFO_SPAWN_EVERY
        self.freeze_timer = 0.0
        self.wave         = 0
        self.wave_cool    = C.WAVE_DELAY
        self.safe         = C.SAFE_SPAWN_TIME
        self.boss_defeated_timer = 0.0
        self.spread_boss_timer   = C.SPREAD_BOSS_INTERVAL

        # ── state ──────────────────────────────────────────────
        self.game_over = False
        self.font      = font   # needed for FloatingText

        # ── all_sprites (draw order) ───────────────────────────
        self.all_sprites = pg.sprite.Group(
            self.ship1, self.ship2, self.tether
        )

    # ─────────────────────────────────────────────────────────
    #  Spawning
    # ─────────────────────────────────────────────────────────

    def start_wave(self):
        self.wave += 1
        count = 3 + self.wave
        for _ in range(count):
            pos = rand_edge_pos()
            # keep away from both ships
            while ((pos - self.ship1.pos).length() < 150 or
                   (pos - self.ship2.pos).length() < 150):
                pos = rand_edge_pos()
            ang   = uniform(0, math.tau)
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
            vel   = Vec(math.cos(ang), math.sin(ang)) * speed
            self.spawn_asteroid(pos, vel, "L")
        if uniform(0, 1) < C.SPREAD_ASTEROID_CHANCE:
            self.spawn_power_asteroid()

    def spawn_asteroid(self, pos: Vec, vel: Vec, size: str):
        a = Asteroid(pos, vel, size)
        a.frozen = self.freeze_timer > 0
        self.asteroids.add(a)
        self.all_sprites.add(a)

    def spawn_power_asteroid(self):
        pos = rand_edge_pos()
        while ((pos - self.ship1.pos).length() < 150 or
               (pos - self.ship2.pos).length() < 150):
            pos = rand_edge_pos()
        ang   = uniform(0, math.tau)
        speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
        vel   = Vec(math.cos(ang), math.sin(ang)) * speed
        pa = PowerAsteroid(pos, vel)
        pa.frozen = self.freeze_timer > 0
        self.power_asteroids.add(pa)
        self.asteroids.add(pa)
        self.all_sprites.add(pa)

    def spawn_ufo(self):
        if self.ufos:
            return
        small = uniform(0, 1) < 0.5
        y = uniform(0, C.HEIGHT)
        x = 0 if uniform(0, 1) < 0.5 else C.WIDTH
        ufo = UFO(Vec(x, y), small)
        ufo.dir.xy = (1, 0) if x == 0 else (-1, 0)
        self.ufos.add(ufo)
        self.all_sprites.add(ufo)

    def spawn_black_hole(self):
        pos = Vec(uniform(0, C.WIDTH), uniform(0, C.HEIGHT))
        while ((pos - self.ship1.pos).length() < 200 or
               (pos - self.ship2.pos).length() < 200):
            pos = Vec(uniform(0, C.WIDTH), uniform(0, C.HEIGHT))
        bh = BlackHole(pos)
        self.black_hole = bh
        self.all_sprites.add(bh)
        self.bh_duration = uniform(C.BH_DURATION_MIN, C.BH_DURATION_MAX)

    # ─────────────────────────────────────────────────────────
    #  Player actions
    # ─────────────────────────────────────────────────────────

    def _ship(self, player: int) -> Ship:
        return self.ship1 if player == 1 else self.ship2

    def _bullets(self, player: int) -> pg.sprite.Group:
        return self.bullets1 if player == 1 else self.bullets2

    def try_fire(self, player: int):
        ship    = self._ship(player)
        bullets = self._bullets(player)
        if not ship.alive:
            return
        if len(bullets) >= C.MAX_BULLETS:
            return
        b = ship.fire()
        if b:
            bullets.add(b)
            self.all_sprites.add(b)

    def try_spread(self, player: int):
        ship    = self._ship(player)
        bullets = self._bullets(player)
        if not ship.alive:
            return
        result = ship.spread_fire()
        if result is None:
            return
        for b in result:
            bullets.add(b)
            self.all_sprites.add(b)

    def hyperspace(self, player: int):
        ship = self._ship(player)
        if not ship.alive:
            return
        ship.hyperspace()
        if player == 1:
            self.score1 = max(0, self.score1 - C.HYPERSPACE_COST)
        else:
            self.score2 = max(0, self.score2 - C.HYPERSPACE_COST)

    def try_shield(self, player: int):
        ship = self._ship(player)
        if not ship.alive:
            return
        ship.activate_shield()

    def try_tether(self):
        """Called when both tether keys are held simultaneously."""
        if self.tether_active:
            return
        if self.tether_cool1 > 0 or self.tether_cool2 > 0:
            return
        if not self.ship1.alive or not self.ship2.alive:
            return
        self.tether_active = True
        self.tether_timer  = C.TETHER_DURATION
        self.tether.active = True

    # ─────────────────────────────────────────────────────────
    #  UFO targeting
    # ─────────────────────────────────────────────────────────

    def _nearest_ship_pos(self, ref_pos: Vec) -> Vec:
        d1 = (ref_pos - self.ship1.pos).length() if self.ship1.alive else float("inf")
        d2 = (ref_pos - self.ship2.pos).length() if self.ship2.alive else float("inf")
        return self.ship1.pos if d1 <= d2 else self.ship2.pos

    def ufo_try_fire(self):
        for ufo in self.ufos:
            target = self._nearest_ship_pos(ufo.pos)
            bullet = ufo.fire_at(target)
            if bullet:
                self.ufo_bullets.add(bullet)
                self.all_sprites.add(bullet)

    # ─────────────────────────────────────────────────────────
    #  Update
    # ─────────────────────────────────────────────────────────

    def update(self, dt: float, keys):
        # ── freeze ──
        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.freeze_timer = 0
                for a in self.asteroids:
                    a.frozen = False

        # ── ship control ──
        if self.ship1.alive:
            self.ship1.control_p1(keys, dt)
        if self.ship2.alive:
            self.ship2.control_p2(keys, dt)

        # ── tether key check (ambos devem segurar) ──
        # P1: KP5  |  P2: F
        p1_tether = keys[pg.K_KP5]
        p2_tether = keys[pg.K_f]
        if p1_tether and p2_tether:
            self.try_tether()

        # ── update all sprites ──
        self.all_sprites.update(dt)

        # ── tether logic ──
        if self.tether_cool1 > 0:
            self.tether_cool1 -= dt
            if self.tether_cool1 < 0:
                self.tether_cool1 = 0.0
        if self.tether_cool2 > 0:
            self.tether_cool2 -= dt
            if self.tether_cool2 < 0:
                self.tether_cool2 = 0.0

        if self.tether_active:
            self.tether_timer -= dt
            self.tether.p1 = Vec(self.ship1.pos)
            self.tether.p2 = Vec(self.ship2.pos)

            # mutual pull force
            if self.ship1.alive and self.ship2.alive:
                pull = self.ship2.pos - self.ship1.pos
                dist = pull.length()
                if dist > 1:
                    pull_n = pull.normalize() * C.TETHER_PULL_FORCE * dt
                    self.ship1.vel += pull_n
                    self.ship2.vel -= pull_n

            # tether cuts asteroids
            for ast in list(self.asteroids):
                if segment_circle_collision(
                        self.ship1.pos, self.ship2.pos, ast.pos, ast.r):
                    score = C.AST_SIZES[ast.size]["score"]
                    half  = score // 2
                    self.score1 += half
                    self.score2 += score - half
                    # visual feedback
                    ft = FloatingText(Vec(ast.pos), f"TETHER! +{half}/{score - half}",
                                      (255, 220, 80), self.font)
                    self.all_sprites.add(ft)
                    ast.kill()

            if self.tether_timer <= 0:
                self.tether_active = False
                self.tether.active = False
                self.tether_cool1  = C.TETHER_COOLDOWN
                self.tether_cool2  = C.TETHER_COOLDOWN

        # ── ghost timers ──
        for player in (1, 2):
            ghost = self.ghost1 if player == 1 else self.ghost2
            if ghost is None:
                continue
            if ghost.timer <= 0:
                ghost.kill()
                if player == 1:
                    self.ghost1 = None
                else:
                    self.ghost2 = None
                # if other is also dead → game over
                other_alive = self.ship2.alive if player == 1 else self.ship1.alive
                if not other_alive:
                    self.game_over = True

        # ── black hole ──
        if self.black_hole:
            self.bh_duration -= dt
            if self.bh_duration <= 0:
                self.black_hole.kill()
                self.black_hole = None
                self.bh_timer   = uniform(10, 20)
            else:
                for ship in (self.ship1, self.ship2):
                    if not ship.alive:
                        continue
                    dir_vec = self.black_hole.pos - ship.pos
                    dist    = dir_vec.length()
                    if dist > 0:
                        force = self.black_hole.strength / (dist + 1)
                        ship.vel += dir_vec.normalize() * force * dt * 50
        else:
            self.bh_timer -= dt
            if self.bh_timer <= 0:
                self.spawn_black_hole()

        # ── safe period ──
        if self.safe > 0:
            self.safe -= dt
            if self.ship1.alive:
                self.ship1.invuln = 0.5
            if self.ship2.alive:
                self.ship2.invuln = 0.5

        # ── UFO ──
        if self.ufos:
            self.ufo_try_fire()
        else:
            self.ufo_timer -= dt
        if not self.ufos and self.ufo_timer <= 0:
            self.spawn_ufo()
            self.ufo_timer = C.UFO_SPAWN_EVERY

        self.handle_collisions()

        # ── wave progression ──
        if self.boss_defeated_timer > 0:
            self.boss_defeated_timer -= dt
            if self.boss_defeated_timer <= 0:
                self.start_wave()
            return

        if self.freeze_timer <= 0:
            if not self.asteroids and self.wave_cool <= 0:
                self.start_wave()
                self.wave_cool = C.WAVE_DELAY
            elif not self.asteroids:
                self.wave_cool -= dt

    # ─────────────────────────────────────────────────────────
    #  Collisions
    # ─────────────────────────────────────────────────────────

    def _register_hit(self, ast: Asteroid, player: int):
        """Track which player hit this asteroid for kill-steal logic."""
        if ast.first_hit_player == 0:
            ast.first_hit_player = player
        ast.last_hit_player = player

    def handle_collisions(self):
        # ── bullets1 vs asteroids ──
        hits1 = pg.sprite.groupcollide(
            self.asteroids, self.bullets1, False, True,
            collided=lambda a, b: (a.pos - b.pos).length() < a.r,
        )
        for ast in hits1:
            self._register_hit(ast, 1)

        # ── bullets2 vs asteroids ──
        hits2 = pg.sprite.groupcollide(
            self.asteroids, self.bullets2, False, True,
            collided=lambda a, b: (a.pos - b.pos).length() < a.r,
        )
        for ast in hits2:
            self._register_hit(ast, 2)

        # ── determine kills: asteroids with no bullets left ──
        # We track kills by checking which asteroids were just hit.
        # "last_hit_player" at this point is the killer.
        all_hits: dict = {}
        all_hits.update(hits1)
        all_hits.update(hits2)
        for ast in all_hits:
            if ast.alive():
                # still alive (only some bullets hit, not kill shot yet? no —
                # groupcollide removes bullets but not the asteroid automatically)
                # We defer actual split to after both groups processed.
                pass

        # Collect asteroids to split (those in all_hits)
        to_split = list(all_hits.keys())
        for ast in to_split:
            if not ast.alive():
                continue  # already killed by tether this frame
            killer = ast.last_hit_player if ast.last_hit_player != 0 else 1
            if isinstance(ast, PowerAsteroid):
                self._award_score(ast.size, killer, ast)
                item = LifeItem(Vec(ast.pos))
                self.life_items.add(item)
                self.all_sprites.add(item)
                ast.kill()
            else:
                self.split_asteroid(ast, killer)

        # ── UFO bullets vs asteroids ──
        ufo_hits = pg.sprite.groupcollide(
            self.asteroids, self.ufo_bullets, False, True,
            collided=lambda a, b: (a.pos - b.pos).length() < a.r,
        )
        for ast in ufo_hits:
            if ast.alive():
                self.split_asteroid(ast, killer=0)  # UFO kill, no player scores

        # ── clock items (both ships can pick) ──
        for ship in (self.ship1, self.ship2):
            if not ship.alive:
                continue
            for item in list(self.clock_items):
                if (item.pos - ship.pos).length() < (item.r + ship.r):
                    item.kill()
                    self.freeze_timer = C.FREEZE_DURATION
                    for a in self.asteroids:
                        a.frozen = True

        # ── life items ──
        for ship, player in ((self.ship1, 1), (self.ship2, 2)):
            if not ship.alive:
                continue
            for item in list(self.life_items):
                if (item.pos - ship.pos).length() < (item.r + ship.r):
                    item.kill()
                    if player == 1:
                        self.lives1 += 1
                    else:
                        self.lives2 += 1

        # ── ghost rescue ──
        if self.ghost2 is not None and self.ship1.alive:
            if (self.ship1.pos - self.ghost2.pos).length() < (self.ship1.r + self.ghost2.r + 10):
                if self.score1 >= C.GHOST_RESCUE_COST:
                    self.score1 -= C.GHOST_RESCUE_COST
                    self.ghost2.kill()
                    self.ghost2 = None
                    self._respawn(self.ship2, Vec(C.SHIP2_START))
                    self.lives2 = 1
                    ft = FloatingText(Vec(self.ship2.pos),
                                      "RESGATADO! -500pts", C.SHIP_P2_COLOR, self.font)
                    self.all_sprites.add(ft)

        if self.ghost1 is not None and self.ship2.alive:
            if (self.ship2.pos - self.ghost1.pos).length() < (self.ship2.r + self.ghost1.r + 10):
                if self.score2 >= C.GHOST_RESCUE_COST:
                    self.score2 -= C.GHOST_RESCUE_COST
                    self.ghost1.kill()
                    self.ghost1 = None
                    self._respawn(self.ship1, Vec(C.SHIP1_START))
                    self.lives1 = 1
                    ft = FloatingText(Vec(self.ship1.pos),
                                      "RESGATADO! -500pts", C.SHIP_P1_COLOR, self.font)
                    self.all_sprites.add(ft)

        # ── ship vs asteroids / ufos / ufo_bullets ──
        for ship, player in ((self.ship1, 1), (self.ship2, 2)):
            if not ship.alive or ship.invuln > 0 or self.safe > 0:
                continue
            if ship.shield_active:
                continue
            for ast in self.asteroids:
                if (ast.pos - ship.pos).length() < (ast.r + ship.r):
                    self.ship_die(player)
                    break
            else:
                for ufo in self.ufos:
                    if (ufo.pos - ship.pos).length() < (ufo.r + ship.r):
                        self.ship_die(player)
                        break
                else:
                    for bullet in self.ufo_bullets:
                        if (bullet.pos - ship.pos).length() < (bullet.r + ship.r):
                            bullet.kill()
                            self.ship_die(player)
                            break

        # ── player bullets vs UFOs (each player gets their own kill) ──
        for bullets, player in ((self.bullets1, 1), (self.bullets2, 2)):
            for ufo in list(self.ufos):
                for b in list(bullets):
                    if (ufo.pos - b.pos).length() < (ufo.r + b.r):
                        score = (C.UFO_SMALL["score"] if ufo.small
                                 else C.UFO_BIG["score"])
                        if player == 1:
                            self.score1 += score
                        else:
                            self.score2 += score
                        ufo.kill()
                        b.kill()
                        break

        # ── black hole ──
        if self.black_hole:
            for ship, player in ((self.ship1, 1), (self.ship2, 2)):
                if not ship.alive:
                    continue
                dist = (self.black_hole.pos - ship.pos).length()
                if dist < self.black_hole.r + ship.r:
                    # instant death — remove all lives
                    if player == 1:
                        self.lives1 = 0
                    else:
                        self.lives2 = 0
                    self.ship_die(player)

    # ─────────────────────────────────────────────────────────
    #  Score awarding with kill-steal logic
    # ─────────────────────────────────────────────────────────

    def _award_score(self, size: str, killer: int, ast: Asteroid):
        """Award points for destroying an asteroid, applying kill-steal bonus."""
        base = C.AST_SIZES[size]["score"]
        if killer == 0:
            # UFO kill or tether — no player score here
            return

        first = ast.first_hit_player
        victim = 3 - killer  # the other player

        if first != 0 and first != killer:
            # Kill steal! killer takes base + bonus, victim loses bonus
            steal = int(base * C.KILL_STEAL_BONUS)
            total = base + steal
            if player := killer:
                if player == 1:
                    self.score1 += total
                    self.score2  = max(0, self.score2 - steal)
                else:
                    self.score2 += total
                    self.score1  = max(0, self.score1 - steal)
            color = C.SHIP_P1_COLOR if killer == 1 else C.SHIP_P2_COLOR
            ft = FloatingText(Vec(ast.pos),
                              f"STEAL! +{total}", color, self.font)
            self.all_sprites.add(ft)
        else:
            if killer == 1:
                self.score1 += base
            else:
                self.score2 += base

    def split_asteroid(self, ast: Asteroid, killer: int):
        self._award_score(ast.size, killer, ast)

        pos   = Vec(ast.pos)
        split = C.AST_SIZES[ast.size]["split"]

        if not isinstance(ast, PowerAsteroid) and uniform(0, 1) < C.FREEZE_ITEM_CHANCE:
            item = ClockItem(pos)
            self.clock_items.add(item)
            self.all_sprites.add(item)

        ast.kill()
        for s in split:
            dirv  = rand_unit_vec()
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX) * 1.2
            self.spawn_asteroid(pos, dirv * speed, s)

    # ─────────────────────────────────────────────────────────
    #  Ship death & respawn
    # ─────────────────────────────────────────────────────────

    def ship_die(self, player: int):
        if player == 1:
            self.lives1 -= 1
            if self.lives1 <= 0:
                self.ship1.alive = False
                self.ship1.kill()
                self.ghost1 = GhostShip(self.ship1.pos, self.ship1.angle, 1)
                self.all_sprites.add(self.ghost1)
                # check immediate game over (other also dead)
                if not self.ship2.alive and self.ghost2 is None:
                    self.game_over = True
            else:
                self._respawn(self.ship1, Vec(C.SHIP1_START))
        else:
            self.lives2 -= 1
            if self.lives2 <= 0:
                self.ship2.alive = False
                self.ship2.kill()
                self.ghost2 = GhostShip(self.ship2.pos, self.ship2.angle, 2)
                self.all_sprites.add(self.ghost2)
                if not self.ship1.alive and self.ghost1 is None:
                    self.game_over = True
            else:
                self._respawn(self.ship2, Vec(C.SHIP2_START))

    def _respawn(self, ship: Ship, start_pos: Vec):
        ship.alive  = True
        ship.pos.xy = start_pos
        ship.vel.xy = (0, 0)
        ship.angle  = -90.0
        ship.invuln = C.SAFE_SPAWN_TIME
        self.safe   = C.SAFE_SPAWN_TIME
        if ship not in self.all_sprites:
            self.all_sprites.add(ship)

    # ─────────────────────────────────────────────────────────
    #  Draw
    # ─────────────────────────────────────────────────────────

    def draw(self, surf: pg.Surface, font: pg.font.Font):
        for spr in self.all_sprites:
            spr.draw(surf)

        # ghost ships are in all_sprites; draw ghosts explicitly if alive
        if self.ghost1:
            self.ghost1.draw(surf)
        if self.ghost2:
            self.ghost2.draw(surf)

        # ── HUD line ──
        pg.draw.line(surf, (60, 60, 60), (0, 50), (C.WIDTH, 50), width=1)

        # ── P1 HUD (left) ──
        hearts1 = "♥" * max(0, self.lives1)
        p1_str  = f"P1 {hearts1}  {self.score1:06d}"
        p1_surf = font.render(p1_str, True, C.SHIP_P1_COLOR)
        surf.blit(p1_surf, (10, 10))

        # P1 cooldowns (row 2 left)
        if self.ship1.spread_cool > 0:
            sl = font.render(f"SPREAD {self.ship1.spread_cool:.1f}s", True, C.GRAY)
        else:
            sl = font.render("SPREAD OK", True, C.SPREAD_COLOR)
        surf.blit(sl, (10, 30))

        if self.ship1.shield_active:
            sh = font.render(f"SHIELD {self.ship1.shield_timer:.1f}s",
                             True, C.SHIELD_COLOR)
            surf.blit(sh, (140, 30))
        elif self.ship1.shield_cooldown > 0:
            sh = font.render(f"SHIELD {self.ship1.shield_cooldown:.0f}s",
                             True, C.GRAY)
            surf.blit(sh, (140, 30))
        else:
            sh = font.render("SHIELD OK", True, C.SHIELD_COLOR)
            surf.blit(sh, (140, 30))

        # ── P2 HUD (right) ──
        hearts2 = "♥" * max(0, self.lives2)
        p2_str  = f"{self.score2:06d}  {hearts2} P2"
        p2_surf = font.render(p2_str, True, C.SHIP_P2_COLOR)
        surf.blit(p2_surf, (C.WIDTH - p2_surf.get_width() - 10, 10))

        # P2 cooldowns (row 2 right, aligned)
        if self.ship2.spread_cool > 0:
            sl2 = font.render(f"SPREAD {self.ship2.spread_cool:.1f}s", True, C.GRAY)
        else:
            sl2 = font.render("SPREAD OK", True, C.SPREAD_COLOR)
        surf.blit(sl2, (C.WIDTH - sl2.get_width() - 10, 30))

        if self.ship2.shield_active:
            sh2 = font.render(f"SHIELD {self.ship2.shield_timer:.1f}s",
                              True, C.SHIELD_COLOR)
            surf.blit(sh2, (C.WIDTH - sl2.get_width() - sh2.get_width() - 20, 30))
        elif self.ship2.shield_cooldown > 0:
            sh2 = font.render(f"SHIELD {self.ship2.shield_cooldown:.0f}s",
                              True, C.GRAY)
            surf.blit(sh2, (C.WIDTH - sl2.get_width() - sh2.get_width() - 20, 30))
        else:
            sh2 = font.render("SHIELD OK", True, C.SHIELD_COLOR)
            surf.blit(sh2, (C.WIDTH - sl2.get_width() - sh2.get_width() - 20, 30))

        # ── Centre: WAVE ──
        w_surf = font.render(f"WAVE {self.wave}", True, C.WHITE)
        surf.blit(w_surf, (C.WIDTH // 2 - w_surf.get_width() // 2, 10))

        # ── Freeze ──
        if self.freeze_timer > 0:
            fl = font.render(f"FREEZE {self.freeze_timer:.1f}s", True, C.ICY_BLUE)
            surf.blit(fl, (C.WIDTH // 2 - fl.get_width() // 2, 30))

        # ── Tether cooldown (centre, below wave) ──
        if self.tether_active:
            tl = font.render(f"⚡ TETHER {self.tether_timer:.1f}s",
                             True, (255, 220, 80))
            surf.blit(tl, (C.WIDTH // 2 - tl.get_width() // 2, 30))
        elif self.tether_cool1 > 0 or self.tether_cool2 > 0:
            cd = max(self.tether_cool1, self.tether_cool2)
            tl = font.render(f"TETHER CD {cd:.0f}s", True, C.GRAY)
            surf.blit(tl, (C.WIDTH // 2 - tl.get_width() // 2, 30))

        # ── Ghost rescue timers ──
        if self.ghost1:
            gt = font.render(
                f"P1 FANTASMA {self.ghost1.timer:.0f}s — P2 passe por cima p/ resgatar",
                True, C.SHIP_P1_COLOR)
            surf.blit(gt, (C.WIDTH // 2 - gt.get_width() // 2, C.HEIGHT - 36))
        if self.ghost2:
            gt = font.render(
                f"P2 FANTASMA {self.ghost2.timer:.0f}s — P1 passe por cima p/ resgatar",
                True, C.SHIP_P2_COLOR)
            surf.blit(gt, (C.WIDTH // 2 - gt.get_width() // 2, C.HEIGHT - 56))
