# ASTEROIDE MULTIPLAYER v2.0
# This file stores the gameplay, rendering, and balancing constants.

WIDTH = 960
HEIGHT = 720
FPS = 60

START_LIVES = 3
SAFE_SPAWN_TIME = 2.0
WAVE_DELAY = 2.0

SHIP_RADIUS = 15
SHIP_TURN_SPEED = 220.0
SHIP_THRUST = 220.0
SHIP_FRICTION = 0.995
SHIP_FIRE_RATE = 0.2
SHIP_BULLET_SPEED = 420.0
HYPERSPACE_COST = 250

SPREAD_COOLDOWN = 15.0

AST_VEL_MIN = 30.0
AST_VEL_MAX = 90.0
AST_SIZES = {
    "L": {"r": 46, "score": 20, "split": ["M", "M"]},
    "M": {"r": 24, "score": 50, "split": ["S", "S"]},
    "S": {"r": 12, "score": 100, "split": []},
}

BULLET_RADIUS = 2
BULLET_TTL = 1.0
MAX_BULLETS = 4

UFO_SPAWN_EVERY = 15.0
UFO_SPEED = 80.0
UFO_FIRE_EVERY = 1.2
UFO_BULLET_SPEED = 260.0
UFO_BULLET_TTL = 1.8
UFO_BIG = {"r": 18, "score": 200, "aim": 0.2}
UFO_SMALL = {"r": 12, "score": 1000, "aim": 0.6}

BLACK_HOLE_RADIUS = 18
BLACK_HOLE_VISUAL_RADIUS = 28
BLACK_HOLE_STRENGTH = 450
BH_TIMER_MIN = 15
BH_TIMER_MAX = 20
BH_DURATION_MIN = 5
BH_DURATION_MAX = 10

WHITE  = (240, 240, 240)
GRAY   = (120, 120, 120)
BLACK  = (0,   0,   0)
PURPLE = (40,  0,   80)
VIOLET = (120, 120, 255)
GREEN  = (0,   255, 100)
DARKER_GREEN = (0, 200, 100)

RANDOM_SEED = None

GAME_OVER_FADE_DURATION = 1.5

BOSS_BULLET_RADIUS = 5
BOSS_BULLET_TTL    = 7
BOSS_BULLET_COLOR  = (255, 60, 60)

SPREAD_BULLET_COUNT    = 8
SPREAD_ASTEROID_CHANCE = 0.15
SPREAD_COLOR = (255, 200, 50)
SPREAD_GLOW  = (255, 160,  0)
SPREAD_BOSS_INTERVAL = 20.0

LIFE_ITEM_RADIUS = 12
LIFE_ITEM_TTL    = 15.0
LIFE_COLOR = (255, 80, 120)

FREEZE_DURATION = 10.0

SHIELD_DURATION      = 2.5
SHIELD_COOLDOWN      = 40.0
SHIELD_COLOR         = (80, 160, 255)
SHIELD_RADIUS_OFFSET = 10
FREEZE_ITEM_CHANCE   = 0.08
CLOCK_COLOR  = (100, 200, 255)
CLOCK_RADIUS = 10
ICY_BLUE = (150, 220, 255)

# ── Multiplayer ────────────────────────────────────────────────
# Cores dos jogadores
SHIP_P1_COLOR = (175, 169, 236)   # roxo claro
SHIP_P2_COLOR = (93,  202, 165)   # verde claro

# Spawn
SHIP1_START = (WIDTH // 3,       HEIGHT // 2)
SHIP2_START = (2 * WIDTH // 3,   HEIGHT // 2)

# Tether
TETHER_DURATION   = 5.0
TETHER_COOLDOWN   = 20.0
TETHER_PULL_FORCE = 55.0

# Ghost Rescue
GHOST_DURATION     = 12.0
GHOST_RESCUE_COST  = 500

# Kill Steal
KILL_STEAL_BONUS = 0.30   # 30 % do score base vai para o ladrão

# Floating text
FLOATING_TEXT_TTL = 1.5

# ── Charge Shot ────────────────────────────────────────────────
CHARGE_TIME          = 1.8
CHARGE_COOLDOWN      = 14.0
CHARGE_BEAM_LIFETIME = 0.35
CHARGE_BEAM_LENGTH   = 1400
CHARGE_BEAM_CORE     = (255, 255, 220)
CHARGE_BEAM_GLOW     = (255, 180,  60)
CHARGE_BEAM_AURA     = (255, 120,  20)
CHARGE_BEAM_WIDTH    = 10

# ── Cursed Crown ───────────────────────────────────────────────
CROWN_SPAWN_FIRST    = 18.0
CROWN_SPAWN_EVERY    = 35.0
CROWN_TTL            = 22.0
CROWN_SCORE_MULT     = 1.5
CROWN_DAMAGE_MULT    = 2
CROWN_COLOR          = (255, 215,  60)
CROWN_GEM_COLOR      = (255,  80, 120)
CROWN_STEAL_COOLDOWN = 1.2

# ── Sabotage / Drunk ───────────────────────────────────────────
SABOTAGE_SPAWN_FIRST = 14.0
SABOTAGE_SPAWN_EVERY = 28.0
SABOTAGE_TTL         = 18.0
SABOTAGE_DURATION    = 5.5
SABOTAGE_COLOR       = (200, 110, 255)
SABOTAGE_GLOW        = (140,  60, 200)

# ── Lobby ──────────────────────────────────────────────────────
LOBBY_STAR_COUNT     = 90
LOBBY_BG_TOP         = (8, 4, 22)
LOBBY_BG_BOTTOM      = (2, 2, 8)
