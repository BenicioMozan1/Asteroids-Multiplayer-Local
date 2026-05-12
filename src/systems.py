# ASTEROIDE MULTIPLAYER v2.0 - 4 JOGADORES (SISTEMAS DINÂMICOS)
# This file coordinates world state, spawning, collisions, scoring, and progression.

import math
from random import uniform
import pygame as pg

import config as C
from sprites import (
    Asteroid, BossBullet, PowerAsteroid,
    Ship, GhostShip, TetherLine, FloatingText,
    UFO, BlackHole, ClockItem, LifeItem,
    ChargeBeam, CrownItem, SabotageItem,
)
from utils import (
    Vec, angle_to_vec, rand_edge_pos, rand_unit_vec,
    segment_circle_collision,
)

class World:
    def __init__(self, font: pg.font.Font, joined_list):
        self.font = font
        
        # ── Dicionários Dinâmicos (Para 2 a 4 Jogadores) ───────────
        self.ships_dict = {}
        self.bullets_dict = {}
        self.scores = {}
        self.lives = {}
        self.ghosts = {}
        self.tether_cool = {}
        
        self.all_sprites = pg.sprite.Group()
        
        # ── Tether Dinâmico ────────────────────────────────────────
        self.tether = TetherLine()
        self.all_sprites.add(self.tether)
        self.tether_active = False
        self.tether_timer  = 0.0
        self.tether_p1_id  = None
        self.tether_p2_id  = None

        # ── Criação das Naves Ativas ───────────────────────────────
        spawn_pos = [C.SHIP1_START, C.SHIP2_START, C.SHIP3_START, C.SHIP4_START]
        start_angles = [45.0, 135.0, -45.0, -135.0]

        for i, joined in enumerate(joined_list):
            if joined:
                p_id = i + 1
                ship = Ship(Vec(spawn_pos[i]), player_id=p_id)
                ship.angle = start_angles[i]
                
                self.ships_dict[p_id] = ship
                self.all_sprites.add(ship)
                self.scores[p_id] = 0
                self.lives[p_id] = C.START_LIVES
                self.bullets_dict[p_id] = pg.sprite.Group()
                self.tether_cool[p_id] = 0.0

        # ── Grupos de Inimigos e Itens ─────────────────────────────
        self.ufo_bullets = pg.sprite.Group()
        self.asteroids = pg.sprite.Group()
        self.power_asteroids = pg.sprite.Group()
        self.ufos = pg.sprite.Group()
        self.black_hole = None
        
        self.clock_items = pg.sprite.Group()
        self.life_items = pg.sprite.Group()
        self.crown_items = pg.sprite.Group()
        self.sabotage_items = pg.sprite.Group()
        self.beams = pg.sprite.Group()

        # ── Timers Globais ─────────────────────────────────────────
        self.crown_spawn_timer = C.CROWN_SPAWN_FIRST
        self.sabotage_spawn_timer = C.SABOTAGE_SPAWN_FIRST
        self.bh_timer = uniform(C.BH_TIMER_MIN, C.BH_TIMER_MAX)
        self.bh_duration = 0.0
        self.ufo_timer = C.UFO_SPAWN_EVERY
        self.freeze_timer = 0.0
        self.wave = 0
        self.wave_cool = C.WAVE_DELAY
        self.safe = C.SAFE_SPAWN_TIME
        self.boss_defeated_timer = 0.0
        
        self.game_over = False

    # ── Retrocompatibilidade com o game.py antigo caso precises ──
    @property
    def score1(self): return self.scores.get(1, 0)
    
    @property
    def score2(self): return self.scores.get(2, 0)

    # ─────────────────────────────────────────────────────────
    #  Spawning
    # ─────────────────────────────────────────────────────────

    def start_wave(self):
        self.wave += 1
        count = 3 + self.wave
        for _ in range(count):
            pos = self._spawn_pos_away_from_ships(150.0)
            ang = uniform(0, math.tau)
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
            vel = Vec(math.cos(ang), math.sin(ang)) * speed
            self.spawn_asteroid(pos, vel, "L")
        if uniform(0, 1) < C.SPREAD_ASTEROID_CHANCE:
            self.spawn_power_asteroid()

    def spawn_asteroid(self, pos: Vec, vel: Vec, size: str):
        a = Asteroid(pos, vel, size)
        a.frozen = self.freeze_timer > 0
        self.asteroids.add(a)
        self.all_sprites.add(a)

    def spawn_power_asteroid(self):
        pos = self._spawn_pos_away_from_ships(150.0)
        ang = uniform(0, math.tau)
        speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
        vel = Vec(math.cos(ang), math.sin(ang)) * speed
        pa = PowerAsteroid(pos, vel)
        pa.frozen = self.freeze_timer > 0
        self.power_asteroids.add(pa)
        self.asteroids.add(pa)
        self.all_sprites.add(pa)

    def spawn_ufo(self):
        if self.ufos: return
        small = uniform(0, 1) < 0.5
        y = uniform(0, C.HEIGHT)
        x = 0 if uniform(0, 1) < 0.5 else C.WIDTH
        ufo = UFO(Vec(x, y), small)
        ufo.dir.xy = (1, 0) if x == 0 else (-1, 0)
        self.ufos.add(ufo)
        self.all_sprites.add(ufo)

    def spawn_black_hole(self):
        pos = self._spawn_pos_away_from_ships(200.0)
        bh = BlackHole(pos)
        self.black_hole = bh
        self.all_sprites.add(bh)
        self.bh_duration = uniform(C.BH_DURATION_MIN, C.BH_DURATION_MAX)

    def _spawn_pos_away_from_ships(self, min_dist: float = 120.0) -> Vec:
        for _ in range(20):
            pos = Vec(uniform(40, C.WIDTH - 40), uniform(80, C.HEIGHT - 40))
            safe = True
            for ship in self.ships_dict.values():
                if ship.alive and (pos - ship.pos).length() < min_dist:
                    safe = False
                    break
            if safe: return pos
        return Vec(C.WIDTH // 2, C.HEIGHT // 2)

    # ─────────────────────────────────────────────────────────
    #  Ações do Jogador
    # ─────────────────────────────────────────────────────────

    def _add_score(self, player: int, amount: int) -> int:
        if player not in self.ships_dict: return 0
        ship = self.ships_dict[player]
        if getattr(ship, "has_crown", False):
            amount = int(amount * C.CROWN_SCORE_MULT)
        self.scores[player] += amount
        return amount

    def _sub_score(self, player: int, amount: int):
        if player in self.scores:
            self.scores[player] = max(0, self.scores[player] - amount)

    def try_fire(self, p_id: int):
        if p_id not in self.ships_dict: return
        ship = self.ships_dict[p_id]
        bullets = self.bullets_dict[p_id]
        if not ship.alive or len(bullets) >= C.MAX_BULLETS: return
        b = ship.fire()
        if b:
            bullets.add(b)
            self.all_sprites.add(b)

    def try_spread(self, p_id: int):
        if p_id not in self.ships_dict: return
        ship = self.ships_dict[p_id]
        bullets = self.bullets_dict[p_id]
        if not ship.alive: return
        result = ship.spread_fire()
        if result:
            for b in result:
                bullets.add(b)
                self.all_sprites.add(b)

    def hyperspace(self, p_id: int):
        if p_id not in self.ships_dict: return
        ship = self.ships_dict[p_id]
        if not ship.alive: return
        ship.hyperspace()
        self.scores[p_id] = max(0, self.scores[p_id] - C.HYPERSPACE_COST)

    def try_shield(self, p_id: int):
        if p_id in self.ships_dict and self.ships_dict[p_id].alive:
            self.ships_dict[p_id].activate_shield()

    def try_tether(self, id1: int, id2: int):
        if self.tether_active: return
        if self.tether_cool[id1] > 0 or self.tether_cool[id2] > 0: return
        s1, s2 = self.ships_dict[id1], self.ships_dict[id2]
        if not s1.alive or not s2.alive: return
        self.tether_active = True
        self.tether_timer = C.TETHER_DURATION
        self.tether.active = True
        self.tether_p1_id = id1
        self.tether_p2_id = id2

    # ─────────────────────────────────────────────────────────
    #  Charge Shot
    # ─────────────────────────────────────────────────────────

    def _update_charge(self, ship: Ship, p_id: int, held: bool, dt: float):
        if not ship.alive:
            ship.charging = False
            ship.charge_timer = 0.0
            return
        if ship.charge_cooldown > 0:
            ship.charge_cooldown -= dt
            if ship.charge_cooldown < 0: ship.charge_cooldown = 0.0
            ship.charging = False
            ship.charge_timer = 0.0
            return
        if held:
            ship.charging = True
            ship.charge_timer = min(ship.charge_timer + dt, C.CHARGE_TIME * 1.5)
        else:
            if ship.charging and ship.charge_timer >= C.CHARGE_TIME:
                self._fire_beam(p_id)
                ship.charge_cooldown = C.CHARGE_COOLDOWN
            ship.charging = False
            ship.charge_timer = 0.0

    def _fire_beam(self, p_id: int):
        ship = self.ships_dict[p_id]
        start = Vec(ship.pos)
        dirv = angle_to_vec(ship.angle)
        end = start + dirv * C.CHARGE_BEAM_LENGTH
        beam = ChargeBeam(start, end, p_id, ship.color)
        self.beams.add(beam)
        self.all_sprites.add(beam)
        ft = FloatingText(Vec(ship.pos + dirv * 24), "CHARGE!", ship.color, self.font)
        self.all_sprites.add(ft)

    # ─────────────────────────────────────────────────────────
    #  Update Loop Principal
    # ─────────────────────────────────────────────────────────

    def update(self, dt: float):
        # ── Freeze ──
        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.freeze_timer = 0
                for a in self.asteroids: a.frozen = False

        # ── Controlos Contínuos (Movimento, Charge, Tether) ──
        tether_requests = []
        for p_id, ship in self.ships_dict.items():
            if ship.alive:
                ship.control_ship(dt)
            
            # Leitura direta do joystick para botões contínuos
            joy_id = p_id - 1
            is_charging = False
            if pg.joystick.get_count() > joy_id:
                joy = pg.joystick.Joystick(joy_id)
                if joy.get_button(4): tether_requests.append(p_id)  # LB = Tether
                if joy.get_button(5): is_charging = True            # RB = Charge
            
            self._update_charge(ship, p_id, is_charging, dt)

        # Inicia tether entre os dois primeiros que apertarem
        if len(tether_requests) >= 2:
            self.try_tether(tether_requests[0], tether_requests[1])

        # ── Powerups ──
        any_crown = len(self.crown_items) > 0 or any(s.has_crown for s in self.ships_dict.values())
        if not any_crown:
            self.crown_spawn_timer -= dt
            if self.crown_spawn_timer <= 0:
                crown = CrownItem(self._spawn_pos_away_from_ships())
                self.crown_items.add(crown)
                self.all_sprites.add(crown)
                self.crown_spawn_timer = C.CROWN_SPAWN_EVERY
                ft = FloatingText(Vec(C.WIDTH//2, 64), "COROA AMALDIÇOADA APARECEU!", C.CROWN_COLOR, self.font)
                self.all_sprites.add(ft)

        if not self.sabotage_items:
            self.sabotage_spawn_timer -= dt
            if self.sabotage_spawn_timer <= 0:
                item = SabotageItem(self._spawn_pos_away_from_ships())
                self.sabotage_items.add(item)
                self.all_sprites.add(item)
                self.sabotage_spawn_timer = C.SABOTAGE_SPAWN_EVERY

        self.all_sprites.update(dt)

        # ── Lógica do Tether ──
        for p_id in self.tether_cool:
            if self.tether_cool[p_id] > 0:
                self.tether_cool[p_id] = max(0.0, self.tether_cool[p_id] - dt)

        if self.tether_active:
            self.tether_timer -= dt
            s1 = self.ships_dict[self.tether_p1_id]
            s2 = self.ships_dict[self.tether_p2_id]
            self.tether.p1 = Vec(s1.pos)
            self.tether.p2 = Vec(s2.pos)

            if s1.alive and s2.alive:
                pull = s2.pos - s1.pos
                dist = pull.length()
                if dist > 1:
                    pull_n = pull.normalize() * C.TETHER_PULL_FORCE * dt
                    s1.vel += pull_n
                    s2.vel -= pull_n

            for ast in list(self.asteroids):
                if segment_circle_collision(s1.pos, s2.pos, ast.pos, ast.r):
                    score = C.AST_SIZES[ast.size]["score"]
                    a1 = self._add_score(self.tether_p1_id, score // 2)
                    a2 = self._add_score(self.tether_p2_id, score - (score // 2))
                    ft = FloatingText(Vec(ast.pos), f"TETHER! +{a1}/{a2}", (255, 220, 80), self.font)
                    self.all_sprites.add(ft)
                    ast.kill()

            if self.tether_timer <= 0:
                self.tether_active = False
                self.tether.active = False
                self.tether_cool[self.tether_p1_id] = C.TETHER_COOLDOWN
                self.tether_cool[self.tether_p2_id] = C.TETHER_COOLDOWN

        # ── Fantasmas (Rescue Decay) ──
        for p_id, ghost in list(self.ghosts.items()):
            if ghost.timer <= 0:
                ghost.kill()
                del self.ghosts[p_id]

        # Check Global Game Over
        alive_count = sum(1 for s in self.ships_dict.values() if s.alive)
        if alive_count == 0:
            self.game_over = True

        # ── Black Hole ──
        if self.black_hole:
            self.bh_duration -= dt
            if self.bh_duration <= 0:
                self.black_hole.kill()
                self.black_hole = None
                self.bh_timer = uniform(10, 20)
            else:
                for ship in self.ships_dict.values():
                    if ship.alive:
                        dir_vec = self.black_hole.pos - ship.pos
                        dist = dir_vec.length()
                        if dist > 0:
                            force = self.black_hole.strength / (dist + 1)
                            ship.vel += dir_vec.normalize() * force * dt * 50
        else:
            self.bh_timer -= dt
            if self.bh_timer <= 0: self.spawn_black_hole()

        # ── Safe Spawn ──
        if self.safe > 0:
            self.safe -= dt
            for ship in self.ships_dict.values():
                if ship.alive: ship.invuln = 0.5

        # ── UFO ──
        if self.ufos:
            for ufo in self.ufos:
                target = self._nearest_ship_pos(ufo.pos)
                bullet = ufo.fire_at(target)
                if bullet:
                    self.ufo_bullets.add(bullet)
                    self.all_sprites.add(bullet)
        else:
            self.ufo_timer -= dt
            if self.ufo_timer <= 0:
                self.spawn_ufo()
                self.ufo_timer = C.UFO_SPAWN_EVERY

        self.handle_collisions()

        # ── Wave Progression ──
        if self.boss_defeated_timer > 0:
            self.boss_defeated_timer -= dt
            if self.boss_defeated_timer <= 0: self.start_wave()
            return

        if self.freeze_timer <= 0:
            if not self.asteroids and self.wave_cool <= 0:
                self.start_wave()
                self.wave_cool = C.WAVE_DELAY
            elif not self.asteroids:
                self.wave_cool -= dt

    def _nearest_ship_pos(self, ref_pos: Vec) -> Vec:
        best_pos = Vec(C.WIDTH//2, C.HEIGHT//2)
        min_d = float("inf")
        for ship in self.ships_dict.values():
            if ship.alive:
                d = (ref_pos - ship.pos).length()
                if d < min_d:
                    min_d = d
                    best_pos = ship.pos
        return best_pos

    # ─────────────────────────────────────────────────────────
    #  Colisões
    # ─────────────────────────────────────────────────────────

    def handle_collisions(self):
        all_hits = {}
        for p_id, bullets in self.bullets_dict.items():
            hits = pg.sprite.groupcollide(
                self.asteroids, bullets, False, True,
                collided=lambda a, b: (a.pos - b.pos).length() < a.r
            )
            for ast in hits:
                if ast.first_hit_player == 0: ast.first_hit_player = p_id
                ast.last_hit_player = p_id
                all_hits[ast] = hits[ast]

        for ast in list(all_hits.keys()):
            if not ast.alive(): continue
            killer = ast.last_hit_player if ast.last_hit_player != 0 else 1
            if isinstance(ast, PowerAsteroid):
                self._award_score(ast.size, killer, ast)
                item = LifeItem(Vec(ast.pos))
                self.life_items.add(item)
                self.all_sprites.add(item)
                ast.kill()
            else:
                self.split_asteroid(ast, killer)

        ufo_hits = pg.sprite.groupcollide(
            self.asteroids, self.ufo_bullets, False, True,
            collided=lambda a, b: (a.pos - b.pos).length() < a.r
        )
        for ast in ufo_hits:
            if ast.alive(): self.split_asteroid(ast, killer=0)

        # ── Itens Globais ──
        for ship in self.ships_dict.values():
            if not ship.alive: continue
            
            for item in list(self.clock_items):
                if (item.pos - ship.pos).length() < (item.r + ship.r):
                    item.kill()
                    self.freeze_timer = C.FREEZE_DURATION
                    for a in self.asteroids: a.frozen = True

            for item in list(self.life_items):
                if (item.pos - ship.pos).length() < (item.r + ship.r):
                    item.kill()
                    self.lives[ship.player_id] += 1

            if not ship.has_crown:
                for item in list(self.crown_items):
                    if (item.pos - ship.pos).length() < (item.r + ship.r):
                        item.kill()
                        if not any(s.has_crown for s in self.ships_dict.values()):
                            ship.has_crown = True
                            ship.steal_cooldown = C.CROWN_STEAL_COOLDOWN
                            ft = FloatingText(Vec(ship.pos), "COROA! +50% / 2x DANO", C.CROWN_COLOR, self.font)
                            self.all_sprites.add(ft)
                        break

            for item in list(self.sabotage_items):
                if (item.pos - ship.pos).length() < (item.r + ship.r):
                    item.kill()
                    for other in self.ships_dict.values():
                        if other != ship and other.alive:
                            other.drunk_timer = C.SABOTAGE_DURATION
                            other.drunk_phase = 0.0
                            ft2 = FloatingText(Vec(other.pos), "BÊBADO!", C.SABOTAGE_COLOR, self.font)
                            self.all_sprites.add(ft2)
                    ft = FloatingText(Vec(ship.pos), "SABOTAGEM!", C.SABOTAGE_COLOR, self.font)
                    self.all_sprites.add(ft)
                    break

        # ── Roubo de Coroa ──
        ships_list = list(self.ships_dict.values())
        for i in range(len(ships_list)):
            for j in range(i + 1, len(ships_list)):
                s1, s2 = ships_list[i], ships_list[j]
                if s1.alive and s2.alive and (s1.has_crown ^ s2.has_crown):
                    if (s1.pos - s2.pos).length() < (s1.r + s2.r):
                        wearer = s1 if s1.has_crown else s2
                        thief  = s2 if s1.has_crown else s1
                        if wearer.steal_cooldown <= 0 and thief.steal_cooldown <= 0:
                            wearer.has_crown = False
                            thief.has_crown = True
                            wearer.steal_cooldown = C.CROWN_STEAL_COOLDOWN
                            thief.steal_cooldown = C.CROWN_STEAL_COOLDOWN
                            ft = FloatingText(Vec(thief.pos), "ROUBOU A COROA!", C.CROWN_COLOR, self.font)
                            self.all_sprites.add(ft)

        # ── Feixes de Carga (Charge Beam) ──
        for beam in list(self.beams):
            if beam.processed: continue
            beam.processed = True
            for ast in list(self.asteroids):
                if not ast.alive(): continue
                if segment_circle_collision(beam.start, beam.end, ast.pos, ast.r):
                    ast.last_hit_player = beam.player_id
                    if isinstance(ast, PowerAsteroid):
                        self._award_score(ast.size, beam.player_id, ast)
                        item = LifeItem(Vec(ast.pos))
                        self.life_items.add(item)
                        self.all_sprites.add(item)
                        ast.kill()
                    else:
                        self.split_asteroid(ast, beam.player_id)
            for ufo in list(self.ufos):
                if segment_circle_collision(beam.start, beam.end, ufo.pos, ufo.r):
                    self._add_score(beam.player_id, C.UFO_SMALL["score"] if ufo.small else C.UFO_BIG["score"])
                    ufo.kill()
            for b in list(self.ufo_bullets):
                if segment_circle_collision(beam.start, beam.end, b.pos, b.r): b.kill()
            
            # Fogo amigo
            for other in self.ships_dict.values():
                if other.player_id != beam.player_id and other.alive and self.safe <= 0:
                    if segment_circle_collision(beam.start, beam.end, other.pos, other.r):
                        self.lives[other.player_id] = 0
                        ft = FloatingText(Vec(other.pos), "VAPORIZADO!", (255, 80, 80), self.font)
                        self.all_sprites.add(ft)
                        self.ship_die(other.player_id)

        # ── Resgate de Fantasmas ──
        for ghost_id, ghost in list(self.ghosts.items()):
            for rescuer_id, ship in self.ships_dict.items():
                if ship.alive and rescuer_id != ghost_id:
                    if (ship.pos - ghost.pos).length() < (ship.r + ghost.r + 10):
                        if self.scores[rescuer_id] >= C.GHOST_RESCUE_COST:
                            self.scores[rescuer_id] -= C.GHOST_RESCUE_COST
                            ghost.kill()
                            del self.ghosts[ghost_id]
                            
                            dead_ship = self.ships_dict[ghost_id]
                            spawn_pos = [C.SHIP1_START, C.SHIP2_START, C.SHIP3_START, C.SHIP4_START][ghost_id - 1]
                            self._respawn(dead_ship, Vec(spawn_pos))
                            self.lives[ghost_id] = 1
                            ft = FloatingText(Vec(dead_ship.pos), "RESGATADO! -500pts", ship.color, self.font)
                            self.all_sprites.add(ft)
                            break

        # ── Naves colidindo com perigos ──
        for ship in self.ships_dict.values():
            if not ship.alive or ship.invuln > 0 or self.safe > 0 or ship.shield_active:
                continue
            
            crashed = False
            for ast in self.asteroids:
                if (ast.pos - ship.pos).length() < (ast.r + ship.r):
                    crashed = True
                    break
            if not crashed:
                for ufo in self.ufos:
                    if (ufo.pos - ship.pos).length() < (ufo.r + ship.r):
                        crashed = True
                        break
            if not crashed:
                for bullet in list(self.ufo_bullets):
                    if (bullet.pos - ship.pos).length() < (bullet.r + ship.r):
                        bullet.kill()
                        crashed = True
                        break
            
            if self.black_hole:
                if (self.black_hole.pos - ship.pos).length() < (self.black_hole.r + ship.r):
                    self.lives[ship.player_id] = 0 # Morte instantânea
                    crashed = True

            if crashed:
                self.ship_die(ship.player_id)

        # ── Tiros vs UFO ──
        for p_id, bullets in self.bullets_dict.items():
            for ufo in list(self.ufos):
                for b in list(bullets):
                    if (ufo.pos - b.pos).length() < (ufo.r + b.r):
                        self._add_score(p_id, C.UFO_SMALL["score"] if ufo.small else C.UFO_BIG["score"])
                        ufo.kill()
                        b.kill()
                        break

    # ─────────────────────────────────────────────────────────
    #  Morte, Divisão e Pontuação
    # ─────────────────────────────────────────────────────────

    def _award_score(self, size: str, killer: int, ast: Asteroid):
        base = C.AST_SIZES[size]["score"]
        if killer == 0: return

        first = ast.first_hit_player
        if first != 0 and first != killer:
            steal = int(base * C.KILL_STEAL_BONUS)
            awarded = self._add_score(killer, base + steal)
            self._sub_score(first, steal)
            color = self.ships_dict[killer].color
            ft = FloatingText(Vec(ast.pos), f"STEAL! +{awarded}", color, self.font)
            self.all_sprites.add(ft)
        else:
            self._add_score(killer, base)

    def split_asteroid(self, ast: Asteroid, killer: int):
        self._award_score(ast.size, killer, ast)
        pos = Vec(ast.pos)
        split = C.AST_SIZES[ast.size]["split"]

        if not isinstance(ast, PowerAsteroid) and uniform(0, 1) < C.FREEZE_ITEM_CHANCE:
            item = ClockItem(pos)
            self.clock_items.add(item)
            self.all_sprites.add(item)

        ast.kill()
        for s in split:
            dirv = rand_unit_vec()
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX) * 1.2
            self.spawn_asteroid(pos, dirv * speed, s)

    def ship_die(self, p_id: int):
        ship = self.ships_dict[p_id]
        damage = C.CROWN_DAMAGE_MULT if getattr(ship, 'has_crown', False) else 1
        
        if getattr(ship, 'has_crown', False):
            ship.has_crown = False
            crown = CrownItem(Vec(ship.pos))
            self.crown_items.add(crown)
            self.all_sprites.add(crown)
            ft = FloatingText(Vec(ship.pos), "COROA CAIU!", C.CROWN_COLOR, self.font)
            self.all_sprites.add(ft)

        self.lives[p_id] -= damage
        if self.lives[p_id] <= 0:
            self.lives[p_id] = 0
            ship.alive = False
            ship.kill()
            ghost = GhostShip(ship.pos, ship.angle, p_id)
            self.ghosts[p_id] = ghost
            self.all_sprites.add(ghost)
            
            # Jogo acaba se não restar ninguém vivo
            alive_count = sum(1 for s in self.ships_dict.values() if s.alive)
            if alive_count == 0:
                self.game_over = True
        else:
            spawn_pos = [C.SHIP1_START, C.SHIP2_START, C.SHIP3_START, C.SHIP4_START][p_id - 1]
            self._respawn(ship, Vec(spawn_pos))

    def _respawn(self, ship: Ship, start_pos: Vec):
        ship.alive = True
        ship.pos.xy = start_pos
        ship.vel.xy = (0, 0)
        ship.angle = -90.0
        ship.invuln = C.SAFE_SPAWN_TIME
        self.safe = C.SAFE_SPAWN_TIME
        if ship not in self.all_sprites:
            self.all_sprites.add(ship)

    # ─────────────────────────────────────────────────────────
    #  Draw Dinâmico (HUD)
    # ─────────────────────────────────────────────────────────

    def draw(self, surf: pg.Surface, font: pg.font.Font):
        # REMOVA A LINHA: self.all_sprites.draw(surf)
        # COLOQUE ESTAS DUAS LINHAS NO LUGAR:
        for sprite in self.all_sprites:
            sprite.draw(surf)
            
        for ghost in self.ghosts.values():
            ghost.draw(surf)

        # ── HUD para N Jogadores ──
        y_pos = 10
        
        for p_id, score in self.scores.items():
            ship = self.ships_dict[p_id]
            hearts = "♥" * max(0, self.lives[p_id])
            txt = font.render(f"P{p_id} {hearts} {score:06d}", True, ship.color)
            surf.blit(txt, (10, y_pos))
            
            # Cooldowns alinhados à direita do score
            x_st = 200
            
            if ship.spread_cool <= 0:
                surf.blit(font.render("SPREAD OK", True, C.SPREAD_COLOR), (x_st, y_pos))
            else:
                surf.blit(font.render(f"SPREAD {ship.spread_cool:.1f}", True, C.GRAY), (x_st, y_pos))
            x_st += 120
            
            if ship.shield_active:
                surf.blit(font.render(f"SHIELD {ship.shield_timer:.1f}s", True, C.SHIELD_COLOR), (x_st, y_pos))
            elif ship.shield_cooldown <= 0:
                surf.blit(font.render("SHIELD OK", True, C.SHIELD_COLOR), (x_st, y_pos))
            else:
                surf.blit(font.render(f"SHIELD {ship.shield_cooldown:.0f}s", True, C.GRAY), (x_st, y_pos))
            x_st += 140
            
            if ship.charging:
                pct = min(100, int(100 * ship.charge_timer / C.CHARGE_TIME))
                surf.blit(font.render(f"CHARGE {pct}%", True, C.CHARGE_BEAM_GLOW), (x_st, y_pos))
            elif ship.charge_cooldown <= 0:
                surf.blit(font.render("CHARGE OK", True, C.CHARGE_BEAM_GLOW), (x_st, y_pos))
            else:
                surf.blit(font.render(f"CHARGE {ship.charge_cooldown:.0f}s", True, C.GRAY), (x_st, y_pos))
            x_st += 130
            
            if getattr(ship, 'has_crown', False):
                surf.blit(font.render("👑 COROA", True, C.CROWN_COLOR), (x_st, y_pos))
            x_st += 110
            
            if ship.drunk_timer > 0:
                surf.blit(font.render(f"🍷 BÊBADO {ship.drunk_timer:.1f}s", True, C.SABOTAGE_COLOR), (x_st, y_pos))
                
            y_pos += 22

        # ── Central HUD ──
        w_surf = font.render(f"WAVE {self.wave}", True, C.WHITE)
        surf.blit(w_surf, (C.WIDTH // 2 - w_surf.get_width() // 2, 10))

        if self.freeze_timer > 0:
            fl = font.render(f"FREEZE {self.freeze_timer:.1f}s", True, C.ICY_BLUE)
            surf.blit(fl, (C.WIDTH // 2 - fl.get_width() // 2, 30))

        if self.tether_active:
            tl = font.render(f"⚡ TETHER {self.tether_timer:.1f}s", True, (255, 220, 80))
            surf.blit(tl, (C.WIDTH // 2 - tl.get_width() // 2, 50))
            
        y_ghost = C.HEIGHT - 30
        for p_id, ghost in self.ghosts.items():
            g_txt = font.render(f"P{p_id} FANTASMA {ghost.timer:.0f}s - Passe por cima para resgatar", True, self.ships_dict[p_id].color)
            surf.blit(g_txt, (C.WIDTH // 2 - g_txt.get_width() // 2, y_ghost))
            y_ghost -= 20