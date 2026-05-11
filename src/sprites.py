# ASTEROIDE MULTIPLAYER v2.0
# This file defines the interactive game entities and their local behaviors.

import math
from random import uniform

import pygame as pg

import config as C
from utils import Vec, angle_to_vec, draw_circle, draw_poly, wrap_pos


# ─────────────────────────────────────────────────────────────
#  Projectiles
# ─────────────────────────────────────────────────────────────

class Bullet(pg.sprite.Sprite):
    def __init__(self, pos: Vec, vel: Vec, color=None):
        super().__init__()
        self.pos  = Vec(pos)
        self.vel  = Vec(vel)
        self.ttl  = C.BULLET_TTL
        self.r    = C.BULLET_RADIUS
        self.color = color if color is not None else C.WHITE
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)

    def update(self, dt: float):
        self.pos += self.vel * dt
        self.pos  = wrap_pos(self.pos)
        self.ttl -= dt
        if self.ttl <= 0:
            self.kill()
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        draw_circle(surf, self.pos, self.r, self.color)


class UfoBullet(pg.sprite.Sprite):
    def __init__(self, pos: Vec, vel: Vec):
        super().__init__()
        self.pos  = Vec(pos)
        self.vel  = Vec(vel)
        self.ttl  = C.UFO_BULLET_TTL
        self.r    = C.BULLET_RADIUS
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)

    def update(self, dt: float):
        self.pos += self.vel * dt
        self.pos  = wrap_pos(self.pos)
        self.ttl -= dt
        if self.ttl <= 0:
            self.kill()
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        draw_circle(surf, self.pos, self.r)


class BossBullet(pg.sprite.Sprite):
    def __init__(self, pos: Vec, vel: Vec):
        super().__init__()
        self.pos  = Vec(pos)
        self.vel  = Vec(vel)
        self.ttl  = C.BOSS_BULLET_TTL
        self.r    = C.BOSS_BULLET_RADIUS
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)

    def update(self, dt: float):
        self.pos += self.vel * dt
        self.pos  = wrap_pos(self.pos)
        self.ttl -= dt
        if self.ttl <= 0:
            self.kill()
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        pg.draw.circle(surf, C.BOSS_BULLET_COLOR, self.pos, self.r)


# ─────────────────────────────────────────────────────────────
#  Asteroids
# ─────────────────────────────────────────────────────────────

class Asteroid(pg.sprite.Sprite):
    def __init__(self, pos: Vec, vel: Vec, size: str):
        super().__init__()
        self.pos  = Vec(pos)
        self.vel  = Vec(vel)
        self.size = size
        self.r    = C.AST_SIZES[size]["r"]
        self.poly = self._make_poly()
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)
        # Multiplayer: kill-steal tracking
        self.first_hit_player = 0   # primeiro a atingir (1 ou 2)
        self.last_hit_player  = 0   # último a atingir

    def _make_poly(self):
        steps = 12 if self.size == "L" else 10 if self.size == "M" else 8
        pts = []
        for i in range(steps):
            ang   = i * (360 / steps)
            jitter = uniform(0.75, 1.2)
            r = self.r * jitter
            v = Vec(math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            pts.append(v * r)
        return pts

    def update(self, dt: float):
        if getattr(self, "frozen", False):
            return
        self.pos += self.vel * dt
        self.pos  = wrap_pos(self.pos)
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        pts = [(self.pos + p) for p in self.poly]
        if getattr(self, "frozen", False):
            pg.draw.polygon(surf, C.ICY_BLUE, pts, width=0)
        pg.draw.polygon(surf, C.WHITE, pts, width=1)


class PowerAsteroid(Asteroid):
    def __init__(self, pos: Vec, vel: Vec):
        super().__init__(pos, vel, "S")
        self.pulse_timer = 0.0

    def update(self, dt: float):
        if getattr(self, "frozen", False):
            return
        super().update(dt)
        self.pulse_timer += dt

    def draw(self, surf: pg.Surface):
        glow_r = int(self.r + 6 + 3 * math.sin(self.pulse_timer * 4))
        glow_surf = pg.Surface((glow_r * 2, glow_r * 2), pg.SRCALPHA)
        pg.draw.circle(glow_surf, (*C.LIFE_COLOR, 60), (glow_r, glow_r), glow_r)
        surf.blit(glow_surf, (self.pos.x - glow_r, self.pos.y - glow_r))
        pts = [(self.pos + p) for p in self.poly]
        if getattr(self, "frozen", False):
            pg.draw.polygon(surf, C.ICY_BLUE, pts, width=0)
        pg.draw.polygon(surf, C.LIFE_COLOR, pts, width=2)


# ─────────────────────────────────────────────────────────────
#  Collectibles
# ─────────────────────────────────────────────────────────────

class ClockItem(pg.sprite.Sprite):
    def __init__(self, pos: Vec):
        super().__init__()
        self.pos  = Vec(pos)
        self.r    = C.CLOCK_RADIUS
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)
        self.ttl  = 15.0

    def update(self, dt: float):
        self.ttl -= dt
        if self.ttl <= 0:
            self.kill()
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        pg.draw.circle(surf, C.CLOCK_COLOR, self.pos, self.r, width=2)
        pg.draw.line(surf, C.CLOCK_COLOR, self.pos,
                     self.pos + Vec(0, -self.r * 0.8), 2)
        pg.draw.line(surf, C.CLOCK_COLOR, self.pos,
                     self.pos + Vec(self.r * 0.6, 0), 2)


class LifeItem(pg.sprite.Sprite):
    def __init__(self, pos: Vec):
        super().__init__()
        self.pos  = Vec(pos)
        self.r    = C.LIFE_ITEM_RADIUS
        self.rect = pg.Rect(0, 0, self.r * 2, self.r * 2)
        self.ttl  = C.LIFE_ITEM_TTL
        self.pulse_timer = 0.0

    def update(self, dt: float):
        self.ttl  -= dt
        self.pulse_timer += dt
        if self.ttl <= 0:
            self.kill()
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        scale = 1.0 + 0.15 * math.sin(self.pulse_timer * 4)
        r  = int(self.r * scale)
        cx, cy = int(self.pos.x), int(self.pos.y)
        pg.draw.circle(surf, C.LIFE_COLOR, (cx - r // 3, cy - r // 4), r // 2)
        pg.draw.circle(surf, C.LIFE_COLOR, (cx + r // 3, cy - r // 4), r // 2)
        pg.draw.polygon(surf, C.LIFE_COLOR, [
            (cx - r + 2, cy - r // 6),
            (cx + r - 2, cy - r // 6),
            (cx,         cy + r),
        ])


# ─────────────────────────────────────────────────────────────
#  Ship
# ─────────────────────────────────────────────────────────────

class Ship(pg.sprite.Sprite):
    def __init__(self, pos: Vec, player_id: int = 1):
        super().__init__()
        self.pos       = Vec(pos)
        self.vel       = Vec(0, 0)
        self.angle     = -90.0
        self.cool      = 0.0
        self.invuln    = 0.0
        self.alive     = True
        self.r         = C.SHIP_RADIUS
        self.rect      = pg.Rect(0, 0, self.r * 2, self.r * 2)
        self.player_id = player_id
        self.color     = C.SHIP_P1_COLOR if player_id == 1 else C.SHIP_P2_COLOR
        # abilities
        self.has_spread_shot = False
        self.shield_active   = False
        self.shield_timer    = 0.0
        self.shield_cooldown = 0.0
        self.spread_cool     = 0.0

    def activate_shield(self):
        if self.shield_active or self.shield_cooldown > 0:
            return
        self.shield_active   = True
        self.shield_timer    = C.SHIELD_DURATION
        self.shield_cooldown = C.SHIELD_COOLDOWN

    def control_p1(self, keys, dt: float):
        # movimento: setas apenas
        if keys[pg.K_LEFT]:
            self.angle -= C.SHIP_TURN_SPEED * dt
        if keys[pg.K_RIGHT]:
            self.angle += C.SHIP_TURN_SPEED * dt
        if keys[pg.K_UP]:
            self.vel += angle_to_vec(self.angle) * C.SHIP_THRUST * dt
        self.vel *= C.SHIP_FRICTION

    def control_p2(self, keys, dt: float):
        if keys[pg.K_a]:
            self.angle -= C.SHIP_TURN_SPEED * dt
        if keys[pg.K_d]:
            self.angle += C.SHIP_TURN_SPEED * dt
        if keys[pg.K_w]:
            self.vel += angle_to_vec(self.angle) * C.SHIP_THRUST * dt
        self.vel *= C.SHIP_FRICTION

    def fire(self):
        if self.cool > 0:
            return None
        self.cool = C.SHIP_FIRE_RATE
        dirv = angle_to_vec(self.angle)
        pos  = self.pos + dirv * (self.r + 6)
        vel  = self.vel + dirv * C.SHIP_BULLET_SPEED
        return Bullet(pos, vel, self.color)

    def spread_fire(self):
        if self.spread_cool > 0:
            return None
        self.spread_cool = C.SPREAD_COOLDOWN
        bullets = []
        for i in range(C.SPREAD_BULLET_COUNT):
            angle = (360 / C.SPREAD_BULLET_COUNT) * i
            rad   = math.radians(angle)
            direction = Vec(math.cos(rad), math.sin(rad))
            spawn_pos = self.pos + direction * (self.r + 6)
            vel = direction * C.SHIP_BULLET_SPEED
            bullets.append(Bullet(spawn_pos, vel, self.color))
        return bullets

    def hyperspace(self):
        from random import uniform as _u
        self.pos    = Vec(_u(0, C.WIDTH), _u(0, C.HEIGHT))
        self.vel.xy = (0, 0)
        self.invuln = 1.0

    def update(self, dt: float):
        if self.cool > 0:
            self.cool -= dt
        if self.invuln > 0:
            self.invuln -= dt
        if self.shield_active:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_timer  = 0.0
        elif self.shield_cooldown > 0:
            self.shield_cooldown -= dt
            if self.shield_cooldown < 0:
                self.shield_cooldown = 0.0
        if self.spread_cool > 0:
            self.spread_cool -= dt
            if self.spread_cool < 0:
                self.spread_cool = 0.0
        self.pos += self.vel * dt
        self.pos  = wrap_pos(self.pos)
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        dirv  = angle_to_vec(self.angle)
        left  = angle_to_vec(self.angle + 140)
        right = angle_to_vec(self.angle - 140)
        p1 = self.pos + dirv  * self.r
        p2 = self.pos + left  * self.r * 0.9
        p3 = self.pos + right * self.r * 0.9
        draw_poly(surf, [p1, p2, p3], self.color)
        if self.invuln > 0 and int(self.invuln * 10) % 2 == 0:
            draw_circle(surf, self.pos, self.r + 6, self.color)
        if self.shield_active:
            shield_r = self.r + C.SHIELD_RADIUS_OFFSET
            pulse    = int(self.shield_timer * 8) % 2
            alpha    = 200 if self.shield_timer > 0.5 or pulse == 0 else 80
            sh_surf  = pg.Surface((shield_r * 2 + 4, shield_r * 2 + 4), pg.SRCALPHA)
            pg.draw.circle(sh_surf, (*C.SHIELD_COLOR, alpha),
                           (shield_r + 2, shield_r + 2), shield_r, 3)
            surf.blit(sh_surf,
                      (self.pos.x - shield_r - 2, self.pos.y - shield_r - 2))


# ─────────────────────────────────────────────────────────────
#  Ghost Ship (ressurreição)
# ─────────────────────────────────────────────────────────────

class GhostShip(pg.sprite.Sprite):
    def __init__(self, pos: Vec, angle: float, player_id: int):
        super().__init__()
        self.pos       = Vec(pos)
        self.angle     = angle
        self.player_id = player_id
        self.color     = C.SHIP_P1_COLOR if player_id == 1 else C.SHIP_P2_COLOR
        self.timer     = C.GHOST_DURATION
        self.pulse     = 0.0
        self.r         = C.SHIP_RADIUS
        self.rect      = pg.Rect(0, 0, self.r * 2, self.r * 2)

    def update(self, dt: float):
        self.timer -= dt
        self.pulse += dt
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        alpha = int(80 + 60 * math.sin(self.pulse * 5))
        dirv  = angle_to_vec(self.angle)
        left  = angle_to_vec(self.angle + 140)
        right = angle_to_vec(self.angle - 140)
        p1 = self.pos + dirv  * self.r
        p2 = self.pos + left  * self.r * 0.9
        p3 = self.pos + right * self.r * 0.9
        ghost = pg.Surface((C.WIDTH, C.HEIGHT), pg.SRCALPHA)
        pg.draw.polygon(ghost, (*self.color, alpha), [p1, p2, p3], width=2)
        # halo
        pg.draw.circle(ghost, (*self.color, alpha // 2),
                       (int(self.pos.x), int(self.pos.y)), self.r + 8, 1)
        surf.blit(ghost, (0, 0))


# ─────────────────────────────────────────────────────────────
#  Tether Line
# ─────────────────────────────────────────────────────────────

class TetherLine(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.active = False
        self.p1     = Vec(0, 0)
        self.p2     = Vec(0, 0)
        self.anim   = 0.0
        self.rect   = pg.Rect(0, 0, 1, 1)

    def update(self, dt: float):
        self.anim += dt

    def draw(self, surf: pg.Surface):
        if not self.active:
            return
        dx     = self.p2.x - self.p1.x
        dy     = self.p2.y - self.p1.y
        length = math.hypot(dx, dy)
        if length < 1:
            return
        dash_len = 10
        gap_len  = 6
        total    = dash_len + gap_len
        offset   = (self.anim * 80) % total
        t = -offset / length
        while t < 1.0:
            t0 = max(0.0, t)
            t1 = min(1.0, t + dash_len / length)
            if t0 < t1:
                a = Vec(self.p1.x + dx * t0, self.p1.y + dy * t0)
                b = Vec(self.p1.x + dx * t1, self.p1.y + dy * t1)
                pg.draw.line(surf, (255, 220, 80), (int(a.x), int(a.y)),
                             (int(b.x), int(b.y)), 2)
            t += total / length


# ─────────────────────────────────────────────────────────────
#  Floating Text (feedback kill steal / rescue)
# ─────────────────────────────────────────────────────────────

class FloatingText(pg.sprite.Sprite):
    def __init__(self, pos: Vec, message: str, color, font: pg.font.Font):
        super().__init__()
        self.pos     = Vec(pos)
        self.message = message
        self.color   = color
        self.font    = font
        self.ttl     = C.FLOATING_TEXT_TTL
        self.vel     = Vec(0, -45)
        self.rect    = pg.Rect(0, 0, 1, 1)

    def update(self, dt: float):
        self.pos += self.vel * dt
        self.ttl -= dt
        if self.ttl <= 0:
            self.kill()

    def draw(self, surf: pg.Surface):
        alpha  = max(0, int(255 * (self.ttl / C.FLOATING_TEXT_TTL)))
        s      = self.font.render(self.message, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (int(self.pos.x) - s.get_width() // 2,
                      int(self.pos.y)))


# ─────────────────────────────────────────────────────────────
#  UFO
# ─────────────────────────────────────────────────────────────

class UFO(pg.sprite.Sprite):
    def __init__(self, pos: Vec, small: bool):
        super().__init__()
        self.pos   = Vec(pos)
        self.small = small
        profile    = C.UFO_SMALL if small else C.UFO_BIG
        self.r     = profile["r"]
        self.aim   = profile["aim"]
        self.speed = C.UFO_SPEED
        self.cool  = C.UFO_FIRE_EVERY
        self.rect  = pg.Rect(0, 0, self.r * 2, self.r * 2)
        self.dir   = Vec(1, 0) if uniform(0, 1) < 0.5 else Vec(-1, 0)

    def update(self, dt: float):
        self.pos   += self.dir * self.speed * dt
        self.cool  -= dt
        if self.pos.x < -self.r * 2 or self.pos.x > C.WIDTH + self.r * 2:
            self.kill()
        self.rect.center = self.pos

    def fire_at(self, target_pos: Vec) -> "UfoBullet | None":
        if self.cool > 0:
            return None
        aim_vec = Vec(target_pos) - self.pos
        if aim_vec.length_squared() == 0:
            aim_vec = self.dir.normalize()
        else:
            aim_vec = aim_vec.normalize()
        max_error = (1.0 - self.aim) * 60.0
        shot_dir  = aim_vec.rotate(uniform(-max_error, max_error))
        self.cool = C.UFO_FIRE_EVERY
        spawn_pos = self.pos + shot_dir * (self.r + 6)
        vel       = shot_dir * C.UFO_BULLET_SPEED
        return UfoBullet(spawn_pos, vel)

    def draw(self, surf: pg.Surface):
        w, h = self.r * 2, self.r
        rect = pg.Rect(0, 0, w, h)
        rect.center = self.pos
        pg.draw.ellipse(surf, C.WHITE, rect, width=1)
        cup = pg.Rect(0, 0, int(w * 0.5), int(h * 0.7))
        cup.center = (self.pos.x, self.pos.y - h * 0.3)
        pg.draw.ellipse(surf, C.WHITE, cup, width=1)


# ─────────────────────────────────────────────────────────────
#  Black Hole
# ─────────────────────────────────────────────────────────────

class BlackHole(pg.sprite.Sprite):
    def __init__(self, pos: Vec):
        super().__init__()
        self.pos      = Vec(pos)
        self.r        = C.BLACK_HOLE_RADIUS
        self.visual_r = C.BLACK_HOLE_VISUAL_RADIUS
        self.strength = C.BLACK_HOLE_STRENGTH
        self.rect     = pg.Rect(0, 0, self.visual_r * 2, self.visual_r * 2)

    def update(self, dt: float):
        self.rect.center = self.pos

    def draw(self, surf: pg.Surface):
        pg.draw.circle(surf, C.PURPLE, self.pos, self.visual_r)
        pg.draw.circle(surf, C.VIOLET, self.pos, self.visual_r - 4, 2)
        pg.draw.circle(surf, C.BLACK,  self.pos, self.r)
