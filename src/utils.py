# ASTEROIDE MULTIPLAYER v2.0
# This file provides shared math, drawing, and random helper utilities.

import math
from random import random, uniform
from typing import Iterable, Tuple

import pygame as pg

import config as C

Vec = pg.math.Vector2


def wrap_pos(pos: Vec) -> Vec:
    return Vec(pos.x % C.WIDTH, pos.y % C.HEIGHT)


def angle_to_vec(deg: float) -> Vec:
    rad = math.radians(deg)
    return Vec(math.cos(rad), math.sin(rad))


def rand_unit_vec() -> Vec:
    a = uniform(0, math.tau)
    return Vec(math.cos(a), math.sin(a))


def rand_edge_pos() -> Vec:
    if random() < 0.5:
        x = uniform(0, C.WIDTH)
        y = 0 if random() < 0.5 else C.HEIGHT
    else:
        x = 0 if random() < 0.5 else C.WIDTH
        y = uniform(0, C.HEIGHT)
    return Vec(x, y)


def draw_poly(surface: pg.Surface, pts: Iterable[Tuple[int, int]],
              color=None, width: int = 1):
    c = color if color is not None else C.WHITE
    pg.draw.polygon(surface, c, list(pts), width=width)


def draw_circle(surface: pg.Surface, pos: Vec, r: int, color=None, width: int = 1):
    c = color if color is not None else C.WHITE
    pg.draw.circle(surface, c, pos, r, width=width)


def text(surface: pg.Surface, font: pg.font.Font, s: str,
         x: int, y: int, color=None):
    c = color if color is not None else C.WHITE
    surf = font.render(s, True, c)
    rect = surf.get_rect(topleft=(x, y))
    surface.blit(surf, rect)


def segment_circle_collision(p1: Vec, p2: Vec, center: Vec, r: float) -> bool:
    """True se o círculo (center, r) intersecta o segmento p1→p2."""
    d = p2 - p1
    f = p1 - center
    a = d.dot(d)
    if a == 0:
        return False
    b = 2 * f.dot(d)
    c = f.dot(f) - r * r
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return False
    sq = math.sqrt(discriminant)
    t1 = (-b - sq) / (2 * a)
    t2 = (-b + sq) / (2 * a)
    return (0.0 <= t1 <= 1.0) or (0.0 <= t2 <= 1.0)
