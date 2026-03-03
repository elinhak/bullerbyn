"""
game.py — Main Game Class
===========================
This is the "conductor" of the whole game.
It manages:
  - Game states (title screen, playing, paused, game over)
  - Routing keyboard/mouse events to the right place
  - Calling update() and draw() on the active state
  - Save and load functionality

States:
  STATE_TITLE   — the title / start screen (press ENTER to play)
  STATE_PLAYING — the main gameplay loop
  STATE_PAUSED  — pause menu (ESC key)

The actual game logic lives in world.py and its children.
This file just decides WHICH state is active and what to do in it.
"""

import pygame
import json
import os

from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TILE_SIZE,
    C_HOUSE_RED, C_HOUSE_TRIM, C_UI_TEXT, C_UI_GOLD,
    C_FLAG_BLUE, C_FLAG_YELLOW, C_UI_BG, C_UI_BORDER,
    C_SKY_DAY, SAVE_FILE,
)
from src.world import (
    World,
    _draw_sky_gradient, _draw_farmhouse, _draw_flagpole,
    _draw_tree, _draw_tree_shadow, _draw_bush, _draw_bush_shadow,
)
from src.tilemap import _draw_tile, T_GRASS, T_GRASS_FLOWER, T_PATH
from src.ui    import UI, _draw_panel, _blit_text

# Game state constants
STATE_TITLE   = "title"
STATE_PLAYING = "playing"
STATE_PAUSED  = "paused"


class Game:
    """
    The top-level game object.

    main.py creates one instance of Game and calls handle_events(),
    update(), and draw() every frame.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.state  = STATE_TITLE

        # The world is created once and reused (reset on new game)
        self.world  = None
        self.ui     = UI()

        # Clock for delta-time — we keep one here and pass dt to world.update
        self._clock = pygame.time.Clock()

        # Load font for the title screen
        pygame.font.init()
        self.title_font = pygame.font.SysFont("Georgia", 52, bold=True)
        self.sub_font   = pygame.font.SysFont("Georgia", 22)
        self.hint_font  = pygame.font.SysFont("Courier New", 14)

        # Animated decorations on the title screen
        self._title_timer = 0.0

    # ------------------------------------------------------------------
    # Public interface called by main.py
    # ------------------------------------------------------------------

    def handle_events(self):
        """Process all queued pygame events (keyboard, mouse, quit)."""
        for event in pygame.event.get():

            # Closing the window always quits immediately
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            elif event.type == pygame.KEYDOWN:
                self._on_keydown(event.key)

    def update(self, dt: float):
        """Advance the game state by dt seconds."""
        self._title_timer += dt

        if self.state == STATE_PLAYING and self.world is not None:
            self.world.update(dt)

    def draw(self):
        """Render the current game state to the screen."""
        if self.state == STATE_TITLE:
            self._draw_title()

        elif self.state == STATE_PLAYING and self.world is not None:
            self.world.draw(self.screen)
            self.ui.draw(self.screen, self.world.player, self.world)

        elif self.state == STATE_PAUSED:
            # Draw the world dimmed, then the pause overlay
            if self.world:
                self.world.draw(self.screen)
                self.ui.draw(self.screen, self.world.player, self.world)
            self._draw_pause_overlay()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_keydown(self, key: int):
        """Handle a key-press event according to the current state."""

        if self.state == STATE_TITLE:
            if key == pygame.K_RETURN or key == pygame.K_SPACE:
                self._start_new_game()
            elif key == pygame.K_l:
                self._try_load_game()

        elif self.state == STATE_PLAYING:
            if key == pygame.K_ESCAPE:
                self.state = STATE_PAUSED
            elif key == pygame.K_F5:
                self._save_game()
                self.world._add_notification("Game saved! (F5)")

        elif self.state == STATE_PAUSED:
            if key == pygame.K_ESCAPE or key == pygame.K_p:
                self.state = STATE_PLAYING
            elif key == pygame.K_s:
                self._save_game()
                self.state = STATE_PLAYING
                self.world._add_notification("Game saved!")
            elif key == pygame.K_q:
                # Quit to title
                self.state = STATE_TITLE

    def _start_new_game(self):
        """Create a fresh world and switch to the playing state."""
        self.world = World()
        self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def _save_game(self):
        """
        Save the current game state to a JSON file.

        We save:
          - Player position, inventory, tool
          - Current day number and time of day
          - All crop states

        JSON is a text format that's easy to read and edit — handy
        for debugging and modding!
        """
        if self.world is None:
            return

        w = self.world
        p = w.player

        data = {
            "day":       w.day_number,
            "time":      w._day_timer,
            "player": {
                "x":        p.x,
                "y":        p.y,
                "tool":     p.tool,
                "seeds":    p.seeds,
                "gold":     p.gold,
                "potatoes": p.potatoes,
            },
            "crops": w.crop_mgr.to_dict(),
            "farm":  _serialize_farm(w.tilemap.farm),
        }

        os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"[Bullerbyn] Game saved to {SAVE_FILE}")

    def _try_load_game(self):
        """
        Attempt to load a save file.
        If no save exists, start a new game instead.
        """
        if not os.path.exists(SAVE_FILE):
            self._start_new_game()
            if self.world:
                self.world._add_notification("No save found — starting fresh!")
            return

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.world = World()
            w = self.world
            p = w.player

            w.day_number   = data.get("day",  1)
            w._day_timer   = data.get("time", 0.0)
            w.time_of_day  = (w._day_timer % 240) / 240

            pd = data.get("player", {})
            p.x        = float(pd.get("x",        p.x))
            p.y        = float(pd.get("y",        p.y))
            p.tool     = int(  pd.get("tool",     p.tool))
            p.seeds    = int(  pd.get("seeds",    p.seeds))
            p.gold     = int(  pd.get("gold",     p.gold))
            p.potatoes = int(  pd.get("potatoes", p.potatoes))
            p.rect.x   = int(p.x)
            p.rect.y   = int(p.y)

            w.crop_mgr.from_dict(data.get("crops", {}))
            _deserialize_farm(w.tilemap.farm, data.get("farm", {}))

            self.state = STATE_PLAYING
            w._add_notification(f"Welcome back! Day {w.day_number}")
            print(f"[Bullerbyn] Game loaded from {SAVE_FILE}")

        except Exception as e:
            print(f"[Bullerbyn] Load failed: {e}")
            self._start_new_game()
            if self.world:
                self.world._add_notification("Save file corrupted — new game started.")

    # ------------------------------------------------------------------
    # Title Screen
    # ------------------------------------------------------------------

    def _draw_title(self):
        """
        Draw the title screen using the same drawing functions as the game world,
        so the scene looks like a real snapshot of Bullerbyn.
        """
        import math

        screen = self.screen
        t      = self._title_timer
        T      = TILE_SIZE

        # ---- Sky (same gradient as in-game) ----
        _draw_sky_gradient(screen, C_SKY_DAY)

        # ---- Ground: grass tiles below the horizon line ----
        horizon_y = 400
        cols = SCREEN_WIDTH  // T + 2
        rows = (SCREEN_HEIGHT - horizon_y) // T + 2
        for row_i in range(rows):
            for col_i in range(cols):
                sx_ = col_i * T
                sy_ = horizon_y + row_i * T
                # Path strip at the very top of the ground
                if row_i == 0:
                    tile_id = T_PATH
                else:
                    h = (col_i * 2654435761 + (row_i + 50) * 2246822519) & 0xFFFFFFFF
                    tile_id = T_GRASS_FLOWER if h % 100 < 8 else T_GRASS
                _draw_tile(screen, pygame.Rect(sx_, sy_, T, T), tile_id, col_i, row_i + 50)

        # ---- Scene layout ----
        # Farmhouse — left side, sits on the horizon
        hw, hh = 300, 200
        hx = 70
        hy = horizon_y - hh + T // 3

        # Flagpole — just to the right of the house
        # _draw_flagpole expects sy such that pole base = sy + T*5
        fp_sx = hx + hw + 14
        fp_sy = horizon_y - T * 5

        # Trees — right side and far edges
        scene_trees = [
            (SCREEN_WIDTH - 130, horizon_y - T),
            (SCREEN_WIDTH - 230, horizon_y - T),
            (SCREEN_WIDTH - 50,  horizon_y - T),
            (14,                 horizon_y - T),
        ]
        # Bushes — near the house and path
        scene_bushes = [
            (hx + hw,            horizon_y + T // 3),
            (hx - T // 2,        horizon_y + T // 2),
            (fp_sx + T * 3,      horizon_y + T // 4),
        ]

        # Draw shadows first (behind everything)
        for tx_, ty_ in scene_trees:
            _draw_tree_shadow(screen, tx_, ty_)
        for bx_, by_ in scene_bushes:
            _draw_bush_shadow(screen, bx_, by_)

        # Farmhouse
        _draw_farmhouse(screen, hx, hy, hw, hh)

        # Flagpole
        _draw_flagpole(screen, fp_sx, fp_sy, t / 240.0)

        # Trees and bushes
        for tx_, ty_ in scene_trees:
            _draw_tree(screen, tx_, ty_)
        for bx_, by_ in scene_bushes:
            _draw_bush(screen, bx_, by_)

        # ---- Animated fireflies on the grass ----
        for i in range(6):
            angle = t * 0.6 + i * 1.05
            fx = int(SCREEN_WIDTH * 0.55 + math.sin(angle + i * 0.9) * 200 + i * 40)
            fy = int(horizon_y + T + math.cos(angle * 0.8 + i) * 20 + i * 14)
            brightness = int(180 + math.sin(t * 3 + i) * 70)
            brightness = max(0, min(255, brightness))
            glow = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (brightness, brightness, 50, brightness // 2), (4, 4), 4)
            pygame.draw.circle(glow, (brightness, brightness, 80, brightness),      (4, 4), 2)
            screen.blit(glow, (fx % SCREEN_WIDTH - 4, fy))

        # ---- Title panel (centred, right half of screen) ----
        panel_w = 500
        panel_h = 230
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2 + 160
        panel_y = 80
        _draw_panel(screen, panel_x, panel_y, panel_w, panel_h, alpha=225)

        # Game title
        title_surf  = self.title_font.render("Bullerbyn", True, (255, 245, 205))
        shadow_surf = self.title_font.render("Bullerbyn", True, (28, 18, 8))
        tx = panel_x + panel_w // 2 - title_surf.get_width() // 2
        ty = panel_y + 22
        screen.blit(shadow_surf, (tx + 3, ty + 3))
        screen.blit(title_surf,  (tx, ty))

        # Subtitle
        sub = self.sub_font.render("A farming simulator", True, (200, 175, 118))
        screen.blit(sub, (panel_x + panel_w // 2 - sub.get_width() // 2, ty + 64))

        # Decorative divider line
        line_y = ty + 100
        pygame.draw.line(screen, (150, 120, 60),
                         (panel_x + 40, line_y), (panel_x + panel_w - 40, line_y), 2)
        pygame.draw.line(screen, (100, 76, 38),
                         (panel_x + 40, line_y + 3), (panel_x + panel_w - 40, line_y + 3), 1)

        # "Press enter" prompt
        start = self.sub_font.render("Press ENTER to begin", True, (225, 205, 140))
        screen.blit(start, (panel_x + panel_w // 2 - start.get_width() // 2,
                            line_y + 14))

        # Load hint
        load_txt = self.hint_font.render("Press L to load saved game",
                                         True, (165, 145, 95))
        screen.blit(load_txt, (panel_x + panel_w // 2 - load_txt.get_width() // 2,
                                line_y + 48))

        # ---- How-to-play hints at the bottom ----
        hints = [
            "Farm potatoes | Sell for gold",
            "WASD to walk  |  1-4 select tool  |  SPACE use tool",
            "F5 to save    |  ESC to pause",
        ]
        for i, hint in enumerate(hints):
            hs = self.hint_font.render(hint, True, (65, 50, 32))
            screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2,
                             SCREEN_HEIGHT - 68 + i * 18))

    # ------------------------------------------------------------------
    # Pause Overlay
    # ------------------------------------------------------------------

    def _draw_pause_overlay(self):
        """Draw a semi-transparent pause menu over the frozen game world."""
        # Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 280, 200
        px = SCREEN_WIDTH  // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        _draw_panel(self.screen, px, py, pw, ph, alpha=240)

        # Title
        _blit_text(self.screen, self.sub_font, "— Paused —",
                   px + pw // 2 - 55, py + 16, C_UI_GOLD)

        # Options
        options = [
            "ESC / P  — Resume",
            "S        — Save game",
            "Q        — Quit to title",
        ]
        for i, opt in enumerate(options):
            _blit_text(self.screen, self.hint_font, opt,
                       px + 24, py + 60 + i * 36, C_UI_TEXT)


# ---------------------------------------------------------------------------
# Save/load helpers for the tilemap farm layer
# ---------------------------------------------------------------------------

def _serialize_farm(farm: list) -> dict:
    """Convert the 2D farm grid to a compact JSON-friendly dict."""
    result = {}
    for row_i, row in enumerate(farm):
        for col_i, state in enumerate(row):
            if state != 0:   # only save non-zero states
                result[f"{col_i},{row_i}"] = state
    return result


def _deserialize_farm(farm: list, data: dict):
    """Restore the farm grid from the serialized dict."""
    for key, state in data.items():
        col, row = map(int, key.split(","))
        if 0 <= row < len(farm) and 0 <= col < len(farm[row]):
            farm[row][col] = state
