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
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    C_HOUSE_RED, C_HOUSE_TRIM, C_UI_TEXT, C_UI_GOLD,
    C_FLAG_BLUE, C_FLAG_YELLOW, C_UI_BG, C_UI_BORDER,
    C_SKY_DAY, SAVE_FILE,
)
from src.world import World
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
        Draw a charming title screen with the game logo and instructions.
        Features a simple animated sky and Swedish farmhouse silhouette.
        """
        import math

        screen = self.screen
        t      = self._title_timer

        # -- Animated sky gradient (top half) --
        for y in range(SCREEN_HEIGHT // 2):
            # Blend from light golden-yellow to sky blue as y increases
            f = y / (SCREEN_HEIGHT // 2)
            r = int(200 - f * 90)
            g = int(170 + f * 10)
            b = int(90  + f * 140)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # -- Rolling green hills (bottom half) --
        for y in range(SCREEN_HEIGHT // 2, SCREEN_HEIGHT):
            f = (y - SCREEN_HEIGHT // 2) / (SCREEN_HEIGHT // 2)
            g_val = int(130 + f * 40)
            pygame.draw.line(screen, (40, g_val, 50),
                             (0, y), (SCREEN_WIDTH, y))

        # -- Silhouette of a farmhouse (simple dark shape) --
        house_x = SCREEN_WIDTH // 2 - 200
        house_y = SCREEN_HEIGHT // 2 - 60
        house_w = 160
        house_h = 100
        dark_red = (60, 15, 18)

        # Roof triangle
        roof_pts = [
            (house_x - 10, house_y + 40),
            (house_x + house_w // 2, house_y),
            (house_x + house_w + 10, house_y + 40),
        ]
        pygame.draw.polygon(screen, dark_red, roof_pts)
        # House body
        pygame.draw.rect(screen, (50, 15, 18),
                         (house_x, house_y + 35, house_w, house_h - 35))
        # Windows (lit yellow at night)
        for wx in [house_x + 20, house_x + 65, house_x + 110]:
            pygame.draw.rect(screen, (220, 190, 80),
                             (wx, house_y + 55, 22, 20))

        # -- Flagpole silhouette --
        fp_x = house_x + house_w + 30
        pygame.draw.line(screen, dark_red,
                         (fp_x, house_y + house_h - 10),
                         (fp_x, house_y - 40), 4)
        # Waving flag
        for i in range(12):
            wave = int(math.sin(i / 12 * math.pi + t * 2) * 3)
            pygame.draw.rect(screen, (0, 60, 130),
                             (fp_x + 4 + i * 4, house_y - 38 + wave, 5, 18))

        # -- Animated floating particles (fireflies / dust motes) --
        for i in range(8):
            angle = t * 0.5 + i * 0.8
            px = int(SCREEN_WIDTH * 0.3 + math.sin(angle + i) * 150 + i * 60)
            py = int(SCREEN_HEIGHT * 0.4 + math.cos(angle * 0.7) * 40 + i * 8)
            alpha = int(128 + math.sin(t * 2 + i) * 90)
            c = max(0, min(255, alpha))
            pygame.draw.circle(screen, (c, c, 60), (px % SCREEN_WIDTH, py), 2)

        # -- Game title --
        title_surf = self.title_font.render("Bullerbyn", True, (255, 245, 210))
        shadow_surf = self.title_font.render("Bullerbyn", True, (30, 20, 10))
        tx = SCREEN_WIDTH // 2 - title_surf.get_width() // 2
        ty = 100
        # Drop shadow
        screen.blit(shadow_surf, (tx + 3, ty + 3))
        screen.blit(title_surf,  (tx, ty))

        # Subtitle
        sub = self.sub_font.render("A Swedish Farm — 1920s", True, (200, 175, 120))
        sx_ = SCREEN_WIDTH // 2 - sub.get_width() // 2
        screen.blit(sub, (sx_, ty + 68))

        # Decorative line
        line_y = ty + 102
        pygame.draw.line(screen, (150, 120, 60),
                         (SCREEN_WIDTH // 2 - 160, line_y),
                         (SCREEN_WIDTH // 2 + 160, line_y), 2)

        # -- Instructions --
        blink = abs(math.sin(t * 2)) > 0.3   # blink on/off
        if blink:
            start = self.sub_font.render("Press ENTER to begin", True,
                                         (220, 200, 140))
            screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2,
                                SCREEN_HEIGHT // 2 + 60))

        load_col = (170, 150, 100)
        load_txt = self.hint_font.render("Press L to load saved game",
                                         True, load_col)
        screen.blit(load_txt, (SCREEN_WIDTH // 2 - load_txt.get_width() // 2,
                                SCREEN_HEIGHT // 2 + 100))

        # -- How-to-play hint --
        hints = [
            "Farm potatoes | Sell for gold",
            "WASD to walk  |  1-4 select tool  |  SPACE use tool",
            "F5 to save    |  ESC to pause",
        ]
        for i, hint in enumerate(hints):
            hs = self.hint_font.render(hint, True, (130, 110, 80))
            screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2,
                             SCREEN_HEIGHT - 80 + i * 18))

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
