# ASTEROIDE MULTIPLAYER v2.0
# This file manages the application loop, scenes, input handling, and screen drawing.

import math
import random
import sys
from dataclasses import dataclass, field
import pygame as pg
import config as C
from systems import World
from utils import Vec, angle_to_vec, text


# ─────────────────────────────────────────────────────────────
#  Input Binding
# ─────────────────────────────────────────────────────────────

@dataclass
class InputBinding:
    """Descreve como um jogador controla sua nave."""
    input_type: str            # C.INPUT_KEYBOARD_WASD, C.INPUT_KEYBOARD_ARROWS, C.INPUT_GAMEPAD
    joy_instance_id: int = -1  # Só usado se input_type == C.INPUT_GAMEPAD


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
    COLORS = [C.SHIP_P1_COLOR, C.SHIP_P2_COLOR, C.SHIP_P3_COLOR, C.SHIP_P4_COLOR]

    # Teclas que identificam cada tipo de teclado
    WASD_KEYS = {pg.K_w, pg.K_a, pg.K_s, pg.K_d,
                 pg.K_g, pg.K_q, pg.K_h, pg.K_t, pg.K_f, pg.K_r}
    ARROW_KEYS = {pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT,
                  pg.K_KP1, pg.K_KP2, pg.K_KP3, pg.K_KP4, pg.K_KP5, pg.K_KP6}

    def __init__(self, font, big, medium):
        self.font = font
        self.big = big
        self.medium = medium
        self.small = pg.font.SysFont("consolas", 14)
        self.stars = [Star() for _ in range(C.LOBBY_STAR_COUNT)]
        self.t = 0.0

        # ── Bindings dinâmicos ──
        # Dicionário {player_id (1-4): InputBinding}
        self.bindings: dict[int, InputBinding] = {}

        # Rastrear quais inputs já foram pegos
        self.keyboard_wasd_taken = False
        self.keyboard_arrows_taken = False
        self.joy_taken: set[int] = set()  # set de joy instance_ids já atribuídos

    def _next_player_id(self) -> int:
        """Retorna o próximo player_id livre (1-4), ou -1 se cheio."""
        for pid in range(1, C.MAX_TOTAL_PLAYERS + 1):
            if pid not in self.bindings:
                return pid
        return -1

    def try_join_keyboard_wasd(self) -> bool:
        """Tenta registrar um jogador com teclado WASD."""
        if self.keyboard_wasd_taken:
            return False  # Já tem alguém no WASD
        if len(self.bindings) >= C.MAX_TOTAL_PLAYERS:
            return False
        pid = self._next_player_id()
        if pid == -1:
            return False
        self.bindings[pid] = InputBinding(input_type=C.INPUT_KEYBOARD_WASD)
        self.keyboard_wasd_taken = True
        return True

    def try_join_keyboard_arrows(self) -> bool:
        """Tenta registrar um jogador com teclado Setas."""
        if self.keyboard_arrows_taken:
            return False
        if len(self.bindings) >= C.MAX_TOTAL_PLAYERS:
            return False
        pid = self._next_player_id()
        if pid == -1:
            return False
        self.bindings[pid] = InputBinding(input_type=C.INPUT_KEYBOARD_ARROWS)
        self.keyboard_arrows_taken = True
        return True

    def try_join_gamepad(self, instance_id: int) -> bool:
        """Tenta registrar um jogador com controle (instance_id)."""
        if instance_id in self.joy_taken:
            return False  # Esse controle já está sendo usado
        if len(self.bindings) >= C.MAX_TOTAL_PLAYERS:
            return False
        pid = self._next_player_id()
        if pid == -1:
            return False
        self.bindings[pid] = InputBinding(input_type=C.INPUT_GAMEPAD, joy_instance_id=instance_id)
        self.joy_taken.add(instance_id)
        return True

    def get_player_for_joy(self, instance_id: int) -> "int | None":
        """Retorna o player_id que está usando esse controle, ou None."""
        for pid, binding in self.bindings.items():
            if binding.input_type == C.INPUT_GAMEPAD and binding.joy_instance_id == instance_id:
                return pid
        return None

    def get_player_for_keyboard(self, key: int) -> "int | None":
        """Retorna o player_id que usa o teclado correspondente a essa tecla, ou None."""
        if key in self.WASD_KEYS:
            target = C.INPUT_KEYBOARD_WASD
        elif key in self.ARROW_KEYS:
            target = C.INPUT_KEYBOARD_ARROWS
        else:
            return None
        for pid, binding in self.bindings.items():
            if binding.input_type == target:
                return pid
        return None

    def update(self, dt: float):
        self.t += dt
        for s in self.stars: s.update(dt)

    def get_joined_count(self):
        return len(self.bindings)

    def _input_label(self, binding: InputBinding) -> str:
        if binding.input_type == C.INPUT_KEYBOARD_WASD:
            return "TECLADO (WASD)"
        elif binding.input_type == C.INPUT_KEYBOARD_ARROWS:
            return "TECLADO (SETAS)"
        else:
            return "CONTROLE"

    def _control_lines(self, binding: InputBinding) -> list[str]:
        if binding.input_type == C.INPUT_KEYBOARD_WASD:
            return [
                "WASD mover | G tiro | Q hyper",
                "H escudo | T spread | F+R coop",
            ]
        elif binding.input_type == C.INPUT_KEYBOARD_ARROWS:
            return [
                "Setas mover | Num1 tiro | Num2 hyper",
                "Num3 escudo | Num4 spread | Num5+6 coop",
            ]
        else:
            return [
                "Stick mover | X tiro | B hyper",
                "Y escudo | RB spread | LB+RT coop",
            ]

    def draw(self, surf: pg.Surface):
        for s in self.stars: s.draw(surf)
        
        title = self.big.render("ASTEROIDS", True, C.WHITE)
        surf.blit(title, (C.WIDTH // 2 - title.get_width() // 2, 15))

        subtitle = self.font.render(f"MULTIPLAYER LOCAL  |  META: {C.WIN_SCORE} pts", True, C.GRAY)
        surf.blit(subtitle, (C.WIDTH // 2 - subtitle.get_width() // 2, 62))

        # ── Layout 2x2 ──
        margin_x = 20
        margin_y = 90
        gap = 14
        slot_w = (C.WIDTH - margin_x * 2 - gap) // 2     # ~463px cada
        slot_h = (C.HEIGHT - margin_y - 80 - gap) // 2    # ~268px cada

        positions = [
            (margin_x,               margin_y),                    # P1 top-left
            (margin_x + slot_w + gap, margin_y),                   # P2 top-right
            (margin_x,               margin_y + slot_h + gap),     # P3 bottom-left
            (margin_x + slot_w + gap, margin_y + slot_h + gap),    # P4 bottom-right
        ]

        for i in range(4):
            pid = i + 1
            x, y = positions[i]
            color = self.COLORS[i]
            rect = pg.Rect(x, y, slot_w, slot_h)
            is_joined = pid in self.bindings
            thickness = 3 if is_joined else 1
            pg.draw.rect(surf, color, rect, thickness, border_radius=10)
            
            # Nome do player
            lbl = self.medium.render(f"P{pid}", True, color)
            surf.blit(lbl, (x + 14, y + 8))
            
            # Status ao lado do nome
            if is_joined:
                binding = self.bindings[pid]
                status_text = self._input_label(binding)
                status = self.font.render(status_text, True, color)
            else:
                status = self.font.render("Aguardando...", True, C.GRAY)
            surf.blit(status, (x + 14 + lbl.get_width() + 12, y + 14))

            # Controles (fonte pequena, dentro da caixa)
            cy = y + 50
            if is_joined:
                lines = self._control_lines(self.bindings[pid])
                for line in lines:
                    ctrl_surf = self.small.render(line, True, color)
                    surf.blit(ctrl_surf, (x + 14, cy))
                    cy += 20
            else:
                hint_lines = [
                    "Pressione WASD, Setas, ou",
                    "botão A no controle para entrar"
                ]
                for line in hint_lines:
                    ctrl_surf = self.small.render(line, True, C.GRAY)
                    surf.blit(ctrl_surf, (x + 14, cy))
                    cy += 20

        # Instrução para iniciar
        y_bottom = C.HEIGHT - 40
        if self.get_joined_count() >= 2:
            pulse = int(180 + 75 * math.sin(self.t * 4))
            start_txt = self.medium.render("ENTER / START para iniciar!", True, (pulse, pulse, pulse))
            surf.blit(start_txt, (C.WIDTH // 2 - start_txt.get_width() // 2, y_bottom))
        else:
            hint = self.font.render("Min. 2 jogadores | Pressione teclas ou A no controle", True, C.GRAY)
            surf.blit(hint, (C.WIDTH // 2 - hint.get_width() // 2, y_bottom))

class Game:
    def __init__(self):
        pg.init()
        pg.joystick.init()
        
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
        self.world  = World(self.font, {})
        self.go_fade      = 0.0
        self.go_stars = [Star() for _ in range(C.LOBBY_STAR_COUNT)]
        
        self.joysticks = {}
        for i in range(pg.joystick.get_count()):
            joy = pg.joystick.Joystick(i)
            joy.init()
            self.joysticks[joy.get_instance_id()] = joy

    # ─────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────

    def _get_player_for_joy_event(self, instance_id: int) -> "int | None":
        """Encontra o player_id atribuído ao joystick com esse instance_id."""
        bindings = self.lobby.bindings
        for pid, binding in bindings.items():
            if binding.input_type == C.INPUT_GAMEPAD and binding.joy_instance_id == instance_id:
                return pid
        return None

    def _get_player_for_key(self, key: int) -> "int | None":
        """Encontra o player_id atribuído ao teclado correspondente a essa tecla."""
        return self.lobby.get_player_for_keyboard(key)

    def _start_game(self):
        """Inicia a partida com os bindings atuais do lobby."""
        self.world = World(self.font, self.lobby.bindings)
        self.scene = Scene("play")

    # ─────────────────────────────────────────────────────────
    #  Teclas de ação para teclado
    # ─────────────────────────────────────────────────────────

    # WASD side action keys
    WASD_FIRE   = pg.K_g
    WASD_HYPER  = pg.K_q
    WASD_SHIELD = pg.K_h
    WASD_SPREAD = pg.K_t
    WASD_TETHER = pg.K_f
    WASD_CHARGE = pg.K_r

    # Arrow/Numpad side action keys
    ARROW_FIRE   = pg.K_KP1
    ARROW_HYPER  = pg.K_KP2
    ARROW_SHIELD = pg.K_KP3
    ARROW_SPREAD = pg.K_KP4
    ARROW_TETHER = pg.K_KP5
    ARROW_CHARGE = pg.K_KP6

    # ─────────────────────────────────────────────────────────
    #  Main loop
    # ─────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(C.FPS) / 1000.0
            
            self.screen.fill(C.BLACK)

            # ── PROCESSAMENTO DE EVENTOS ──
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
                        # Tentar registrar jogador baseado na tecla
                        if e.key in Lobby.WASD_KEYS:
                            self.lobby.try_join_keyboard_wasd()
                        elif e.key in Lobby.ARROW_KEYS:
                            self.lobby.try_join_keyboard_arrows()

                        # Iniciar jogo
                        if e.key in (pg.K_RETURN, pg.K_SPACE) and self.lobby.get_joined_count() >= 2:
                            self._start_game()

                    elif self.scene.name == "game_over":
                        if e.key in (pg.K_RETURN, pg.K_SPACE):
                            self._start_game()
                            self.go_fade = 0.0

                    elif self.scene.name == "play":
                        # Ações de teclado WASD
                        player_wasd = self._get_player_for_key(pg.K_w)  # qualquer tecla WASD
                        if player_wasd is not None:
                            if e.key == self.WASD_FIRE:    self.world.try_fire(player_wasd)
                            if e.key == self.WASD_HYPER:   self.world.hyperspace(player_wasd)
                            if e.key == self.WASD_SHIELD:  self.world.try_shield(player_wasd)
                            if e.key == self.WASD_SPREAD:  self.world.try_spread(player_wasd)

                        # Ações de teclado Setas
                        player_arrows = self._get_player_for_key(pg.K_UP)  # qualquer tecla Setas
                        if player_arrows is not None:
                            if e.key == self.ARROW_FIRE:   self.world.try_fire(player_arrows)
                            if e.key == self.ARROW_HYPER:  self.world.hyperspace(player_arrows)
                            if e.key == self.ARROW_SHIELD: self.world.try_shield(player_arrows)
                            if e.key == self.ARROW_SPREAD: self.world.try_spread(player_arrows)

                if e.type == pg.JOYBUTTONDOWN:
                    player = self._get_player_for_joy_event(e.instance_id)

                    if self.scene.name == "lobby":
                        # Xbox A (0) ou PS5 Cross (1) ou PS5 Square (0)
                        if e.button in (0, 1):
                            self.lobby.try_join_gamepad(e.instance_id)
                        # Xbox Start (7) ou PS5 Options (6)
                        if self.lobby.get_joined_count() >= 2 and e.button in (6, 7):
                            self._start_game()
                    
                    elif self.scene.name == "game_over":
                        if e.button in (0, 1, 6, 7):
                            self._start_game()
                            self.go_fade = 0.0

                    elif self.scene.name == "play" and player is not None:
                        # Xbox X ou PS5 Quadrado (2)
                        if e.button == 2:       self.world.try_fire(player)
                        # Xbox B ou PS5 Bolinha (1)
                        if e.button == 1:       self.world.hyperspace(player)
                        # Xbox Y ou PS5 Triângulo (3)
                        if e.button == 3:       self.world.try_shield(player)
                        # Xbox RB (5) ou PS5 R1 (10)
                        if e.button in (5, 10): self.world.try_spread(player)

            keys = pg.key.get_pressed()
            self.screen.fill(C.BLACK)

            if self.scene.name == "lobby":
                self.lobby.update(dt)
                self.lobby.draw(self.screen)

            elif self.scene.name == "play":
                self.world.update(dt, keys, self.joysticks)
                self.world.draw(self.screen, self.font)
                if self.world.game_over:
                    self.go_fade = 0.0
                    self.scene = Scene("game_over")

            elif self.scene.name == "game_over":
                self.go_fade = min(self.go_fade + dt, 1.0)
                self._draw_game_over(dt)
            
            pg.display.flip()

    # ─────────────────────────────────────────────────────────
    #  Tela de Game Over
    # ─────────────────────────────────────────────────────────

    def _draw_game_over(self, dt: float):
        for s in self.go_stars:
            s.update(dt)
            s.draw(self.screen)

        alpha = min(255, int(self.go_fade * 255))

        overlay = pg.Surface((C.WIDTH, C.HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, min(180, alpha)))
        self.screen.blit(overlay, (0, 0))

        scores = self.world.scores
        winner_id = self.world.winner_id

        # Título depende do tipo de vitória
        if winner_id is not None:
            # Vitória por pontuação
            go_surf = self.big.render("VITORIA!", True, (255, 220, 60))
        else:
            go_surf = self.big.render("GAME OVER", True, (255, 80, 80))
        go_surf.set_alpha(alpha)
        self.screen.blit(go_surf, (C.WIDTH // 2 - go_surf.get_width() // 2, 100))

        # Determinar vencedor
        if winner_id is None:
            # Todos morreram — vencedor é quem tem mais pontos
            max_score = max(scores.values()) if scores else 0
            winners = [pid for pid, s in scores.items() if s == max_score]
            if len(winners) == 1:
                winner_id = winners[0]

        if winner_id is not None:
            color = [C.SHIP_P1_COLOR, C.SHIP_P2_COLOR, C.SHIP_P3_COLOR, C.SHIP_P4_COLOR][winner_id - 1]
            winner_text = f"PLAYER {winner_id} VENCEU!"
        else:
            color = C.WHITE
            winner_text = "EMPATE!"

        w_surf = self.big.render(winner_text, True, color)
        w_surf.set_alpha(alpha)
        self.screen.blit(w_surf, (C.WIDTH // 2 - w_surf.get_width() // 2, 180))

        # Placar de todos os jogadores (ordenado por score)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        y = 280
        rank = 1
        for p_id, score in sorted_scores:
            p_color = [C.SHIP_P1_COLOR, C.SHIP_P2_COLOR, C.SHIP_P3_COLOR, C.SHIP_P4_COLOR][p_id - 1]
            medal = ["🥇", "🥈", "🥉", " "][min(rank - 1, 3)]
            score_txt = self.medium.render(f"{medal} P{p_id}: {score:06d} pts", True, p_color)
            score_txt.set_alpha(alpha)
            self.screen.blit(score_txt, (C.WIDTH // 2 - score_txt.get_width() // 2, y))
            y += 36
            rank += 1

        # Wave alcançada e meta
        wave_txt = self.font.render(f"Wave: {self.world.wave}  |  Meta: {C.WIN_SCORE} pts", True, C.GRAY)
        wave_txt.set_alpha(alpha)
        self.screen.blit(wave_txt, (C.WIDTH // 2 - wave_txt.get_width() // 2, y + 20))

        # Instrução para reiniciar
        if self.go_fade >= 0.8:
            pulse = int(150 + 105 * math.sin(self.go_fade * 8))
            restart = self.font.render("ENTER / START para jogar novamente   |   ESC para voltar ao lobby", True, (pulse, pulse, pulse))
            self.screen.blit(restart, (C.WIDTH // 2 - restart.get_width() // 2, C.HEIGHT - 50))