"""
world.py — The Game World
===========================
This is the main "scene" of the game.  It owns and coordinates:
  - The TileMap  (the ground grid)
  - The CropManager (potato plants)
  - The Player character
  - The Camera (viewport)
  - The day/night timer

It also draws all the large visual elements that aren't individual tiles:
  - The red Swedish farmhouse
  - The flagpole with the Swedish flag
  - Trees and bushes
  - The night-time darkness overlay

Think of World as the director that tells all the actors what to do
and in what order to appear on stage.
"""

import pygame
import math
from src.settings import (
    TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
    HOUSE_COL, HOUSE_ROW, HOUSE_COLS, HOUSE_ROWS,
    FLAG_COL, FLAG_ROW,
    FARM_COL, FARM_ROW, FARM_COLS, FARM_ROWS,
    DAY_LENGTH, START_TIME_FRACTION,
    TIME_DAWN, TIME_DAY, TIME_DUSK, TIME_NIGHT,
    C_HOUSE_RED, C_HOUSE_TRIM, C_ROOF, C_ROOF_EDGE,
    C_CHIMNEY, C_FOUNDATION, C_WINDOW, C_DOOR, C_DOOR_FRAME,
    C_TREE_TRUNK, C_TREE_DARK, C_TREE_MID, C_TREE_LIGHT,
    C_BUSH, C_FLOWERS_R, C_FLOWERS_Y,
    C_FLAG_BLUE, C_FLAG_YELLOW, C_POLE,
    C_SKY_NIGHT, C_SKY_DAWN, C_SKY_DAY, C_SKY_DUSK,
    C_NIGHT_OVERLAY,
    POTATO_SELL_PRICE,
)
from src.tilemap import TileMap
from src.crops   import CropManager
from src.player  import Player
from src.camera  import Camera


class World:
    """
    Holds and manages the entire game world.

    Call update(dt) each frame to advance game logic.
    Call draw(surface) each frame to render everything.
    """

    # Five zoom levels: (world pixels wide, world pixels tall) rendered before
    # being scaled up to the 1280×720 display.  Level 0 is the default (no
    # scaling).  Level 4 is the closest view: exactly 20 tiles wide.
    _ZOOM_VIEWS = [
        (1280, 720),   # level 0 — default, ~26.7 × 15 tiles
        (1200, 675),   # level 1
        (1120, 630),   # level 2
        (1040, 585),   # level 3
        ( 960, 540),   # level 4 — closest, 20 × 11.25 tiles
    ]

    def __init__(self, char_config=None):
        self.tilemap    = TileMap()
        self.crop_mgr   = CropManager()
        self.player     = Player(char_config=char_config)
        self.camera     = Camera()

        # Zoom: 0 = furthest (default), 4 = closest
        self.zoom_level = 0
        self._zoom_surf = None   # allocated on first zoomed draw

        # Day counter (starts on Day 1)
        self.day_number = 1

        # Time fraction within the current day (0.0 = midnight, 0.25 = 6 AM)
        self.time_of_day = START_TIME_FRACTION

        # Accumulates real seconds for the day timer
        self._day_timer = START_TIME_FRACTION * DAY_LENGTH

        # Notification messages shown at the top of the screen
        # Each entry is [message_string, time_remaining]
        self.notifications = []

        # Pre-build the list of tree positions so they don't change
        self._trees = _build_tree_list()

        # Pre-build the sell-zone rectangle (a small market stall near the house)
        # Player walks on it with potatoes to sell them
        self._sell_zone_col = HOUSE_COL + HOUSE_COLS + 1
        self._sell_zone_row = HOUSE_ROW + HOUSE_ROWS - 2

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        """Advance all game systems by dt seconds."""

        # -- Day/Night cycle --
        self._day_timer += dt
        self.time_of_day = (self._day_timer % DAY_LENGTH) / DAY_LENGTH

        # Detect day rollover (midnight)
        if self._day_timer >= DAY_LENGTH:
            self._day_timer -= DAY_LENGTH
            self._on_new_day()

        # -- Notification timers --
        # Decay each notification; remove expired ones
        self.notifications = [
            [msg, ttl - dt]
            for msg, ttl in self.notifications
            if ttl - dt > 0
        ]

        # -- Player (passes notification list so player can add messages) --
        msg_list = []   # temp list for this frame's messages
        self.player.update(dt, self.tilemap, self.crop_mgr, msg_list)
        for msg in msg_list:
            self._add_notification(msg)

        # -- Check sell zone --
        self._check_sell_zone()

        # -- Camera follows player --
        # Keep camera viewport in sync with current zoom level
        vis_w, vis_h = self._ZOOM_VIEWS[self.zoom_level]
        self.camera.view_w = vis_w
        self.camera.view_h = vis_h
        px = self.player.x + self.player.rect.width  // 2
        py = self.player.y + self.player.rect.height // 2
        self.camera.center_on(px, py)

    def _on_new_day(self):
        """Called once each time the in-game clock rolls past midnight."""
        self.day_number += 1
        self.crop_mgr.new_day()   # all crops age by one day

        # Reset watered tiles back to tilled (water evaporates overnight)
        from src.tilemap import FS_WATERED, FS_TILLED
        for row in range(len(self.tilemap.farm)):
            for col in range(len(self.tilemap.farm[row])):
                if self.tilemap.farm[row][col] == FS_WATERED:
                    self.tilemap.farm[row][col] = FS_TILLED

        self._add_notification(f"Day {self.day_number} begins!")

    def _check_sell_zone(self):
        """
        If the player is standing adjacent to the market stall with potatoes,
        automatically sell them.  The stall tiles are solid so the player stops
        in front; we use a one-tile proximity border to detect that position.
        """
        if self.player.potatoes <= 0:
            return

        sz_x = self._sell_zone_col * TILE_SIZE
        sz_y = self._sell_zone_row * TILE_SIZE
        # Expand the stall footprint by one tile on every side so the sell
        # triggers when the player is standing right next to the stall.
        trigger_rect = pygame.Rect(
            sz_x - TILE_SIZE,
            sz_y - TILE_SIZE,
            TILE_SIZE * 4,
            TILE_SIZE * 4,
        )

        if self.player.rect.colliderect(trigger_rect):
            earned = self.player.potatoes * POTATO_SELL_PRICE
            self.player.gold     += earned
            msg = f"Sold {self.player.potatoes} potatoes for {earned} gold!"
            self.player.potatoes  = 0
            self._add_notification(msg)

    def _add_notification(self, message: str, duration: float = 3.0):
        """Add a message to the on-screen notification queue (shown for 3 s)."""
        # Avoid duplicate messages stacking up
        if self.notifications and self.notifications[-1][0] == message:
            self.notifications[-1][1] = duration   # reset timer
            return
        self.notifications.append([message, duration])

    def zoom_in(self):
        """Step one zoom level closer (scroll up)."""
        self.zoom_level = min(len(self._ZOOM_VIEWS) - 1, self.zoom_level + 1)

    def zoom_out(self):
        """Step one zoom level further away (scroll down)."""
        self.zoom_level = max(0, self.zoom_level - 1)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        """
        Render the complete scene in the correct layer order:
          1. Sky background
          2. Ground tiles (tilemap)
          3. Farm soil overlays
          4. Crops (potato plants)
          5. Trees and bushes
          6. Farmhouse
          7. Flagpole + flag
          8. Sell-zone marker
          9. Player character
         10. Night darkness overlay

        When zoomed in (zoom_level > 0) the scene is rendered into a smaller
        surface then scaled up to the full screen, giving a pixel-perfect
        magnification without touching any of the individual draw routines.
        """
        vis_w, vis_h = self._ZOOM_VIEWS[self.zoom_level]

        if self.zoom_level == 0:
            # No zoom — draw straight to screen as before
            target = screen
        else:
            # Allocate / reuse a surface the size of the visible world area
            if self._zoom_surf is None or self._zoom_surf.get_size() != (vis_w, vis_h):
                self._zoom_surf = pygame.Surface((vis_w, vis_h))
            target = self._zoom_surf

        # 1. Sky gradient (darker at zenith, lighter at horizon)
        sky_colour = self._get_sky_colour()
        _draw_sky_gradient(target, sky_colour)

        # 2 & 3. Tilemap (ground + farm soil)
        self.tilemap.draw(target, self.camera)

        # 4. Crops
        self.crop_mgr.draw(target, self.camera)

        # 5a. Tree/bush drop shadows (drawn before canopy so they appear on ground)
        for (col, row, kind) in self._trees:
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE
            if self.camera.is_visible(wx, wy, TILE_SIZE * 2, TILE_SIZE * 3):
                sx, sy = self.camera.apply(wx, wy)
                if kind == "tree":
                    _draw_tree_shadow(target, int(sx), int(sy))
                elif kind == "bush":
                    _draw_bush_shadow(target, int(sx), int(sy))

        # 5b. Trees and bushes
        for (col, row, kind) in self._trees:
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE
            if self.camera.is_visible(wx, wy, TILE_SIZE * 2, TILE_SIZE * 3):
                sx, sy = self.camera.apply(wx, wy)
                if kind == "tree":
                    _draw_tree(target, int(sx), int(sy))
                elif kind == "bush":
                    _draw_bush(target, int(sx), int(sy))

        # 6. Farmhouse (drawn over the T_HOUSE_FLOOR tiles)
        hx = HOUSE_COL * TILE_SIZE
        hy = HOUSE_ROW * TILE_SIZE
        hw = HOUSE_COLS * TILE_SIZE
        hh = HOUSE_ROWS * TILE_SIZE
        if self.camera.is_visible(hx, hy, hw, hh):
            sx, sy = self.camera.apply(hx, hy)
            _draw_farmhouse(target, int(sx), int(sy), hw, hh)

        # 7. Flagpole
        fx = FLAG_COL * TILE_SIZE
        fy = FLAG_ROW * TILE_SIZE
        if self.camera.is_visible(fx, fy, TILE_SIZE * 2, TILE_SIZE * 6):
            sx, sy = self.camera.apply(fx, fy)
            _draw_flagpole(target, int(sx), int(sy), self.time_of_day)

        # 8. Sell-zone marker
        szx = self._sell_zone_col * TILE_SIZE
        szy = self._sell_zone_row * TILE_SIZE
        if self.camera.is_visible(szx, szy, TILE_SIZE * 2, TILE_SIZE * 2):
            sx, sy = self.camera.apply(szx, szy)
            _draw_sell_zone(target, int(sx), int(sy))

        # 9. Player
        self.player.draw(target, self.camera)

        # 10. Ambient colour tint (warm at dawn/dusk, cool at night)
        self._draw_ambient_tint(target)

        # 11. Night darkness overlay
        self._draw_night_overlay(target)

        # Scale the rendered frame up to the full screen when zoomed in
        if self.zoom_level != 0:
            scaled = pygame.transform.scale(target, screen.get_size())
            screen.blit(scaled, (0, 0))

    # ------------------------------------------------------------------
    # Sky and lighting
    # ------------------------------------------------------------------

    def _get_sky_colour(self) -> tuple:
        """
        Interpolate between sky colours based on time of day.
        Returns an RGB colour tuple.
        """
        t = self.time_of_day

        if t < TIME_DAWN:
            # Dead of night
            return C_SKY_NIGHT
        elif t < TIME_DAY:
            # Dawn transition
            f = (t - TIME_DAWN) / (TIME_DAY - TIME_DAWN)
            return _lerp_colour(C_SKY_DAWN, C_SKY_DAY, f)
        elif t < TIME_DUSK:
            # Full daytime
            return C_SKY_DAY
        elif t < TIME_NIGHT:
            # Dusk transition
            f = (t - TIME_DUSK) / (TIME_NIGHT - TIME_DUSK)
            return _lerp_colour(C_SKY_DAY, C_SKY_DUSK, f)
        else:
            # Transition to night
            f = min(1.0, (t - TIME_NIGHT) / (1.0 - TIME_NIGHT + TIME_DAWN))
            return _lerp_colour(C_SKY_DUSK, C_SKY_NIGHT, f)

    def _draw_night_overlay(self, surface: pygame.Surface):
        """
        Draw a semi-transparent dark overlay at night to darken the scene.
        The opacity varies smoothly from 0 (day) to ~180 (night).
        """
        t = self.time_of_day

        # Calculate opacity: 0 during day, max at night
        if TIME_DAY <= t <= TIME_DUSK:
            alpha = 0
        elif t < TIME_DAWN:
            alpha = 160
        elif t < TIME_DAY:
            f = (t - TIME_DAWN) / (TIME_DAY - TIME_DAWN)
            alpha = int(160 * (1.0 - f))
        elif t < TIME_NIGHT:
            f = (t - TIME_DUSK) / (TIME_NIGHT - TIME_DUSK)
            alpha = int(160 * f)
        else:
            alpha = 160

        if alpha > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*C_NIGHT_OVERLAY, alpha))
            surface.blit(overlay, (0, 0))

    def _draw_ambient_tint(self, surface: pygame.Surface):
        """
        Overlay a subtle warm/cool colour tint on the world to simulate
        atmospheric lighting changes throughout the day.
        Dawn/dusk: warm orange-gold wash; day: nothing; night: handled elsewhere.
        """
        t = self.time_of_day
        tint_col = None
        alpha = 0

        if TIME_DAWN <= t < TIME_DAY:
            f = (t - TIME_DAWN) / (TIME_DAY - TIME_DAWN)
            alpha = int(55 * (1.0 - abs(f - 0.5) * 2))   # peaks mid-transition
            tint_col = (255, 160, 60)   # warm golden dawn
        elif TIME_DUSK <= t < TIME_NIGHT:
            f = (t - TIME_DUSK) / (TIME_NIGHT - TIME_DUSK)
            alpha = int(65 * math.sin(f * math.pi))       # peaks mid-dusk
            tint_col = (220, 90, 40)    # warm red-orange dusk

        if tint_col and alpha > 0:
            tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            tint.fill((*tint_col, alpha))
            surface.blit(tint, (0, 0))

    def get_time_string(self) -> str:
        """Return the in-game time as a human-readable "HH:MM" string."""
        # Map 0.0–1.0 to 0–24 hours
        total_hours = self.time_of_day * 24.0
        h = int(total_hours) % 24
        m = int((total_hours - int(total_hours)) * 60)
        return f"{h:02d}:{m:02d}"


# ---------------------------------------------------------------------------
# Static drawing helpers (farmhouse, flagpole, trees, etc.)
# ---------------------------------------------------------------------------

def _draw_sky_gradient(surface: pygame.Surface, sky_colour: tuple):
    """
    Draw a vertical gradient sky: darker/richer at the zenith, lighter at the horizon.
    Uses 4-pixel strips for a smooth look at low cost.
    """
    w = surface.get_width()
    h = surface.get_height()
    # Zenith is darker and more saturated; horizon is lighter and slightly warmer
    top = (max(0, sky_colour[0] - 50), max(0, sky_colour[1] - 28), min(255, sky_colour[2] + 18))
    bot = (min(255, sky_colour[0] + 22), min(255, sky_colour[1] + 18), max(0, sky_colour[2] - 8))
    strip = 4
    for y in range(0, h, strip):
        t = y / h
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.rect(surface, (r, g, b), (0, y, w, strip))


def _draw_tree_shadow(surface: pygame.Surface, sx: int, sy: int):
    """Draw a soft elliptical drop-shadow under a tree."""
    T = TILE_SIZE
    sh = pygame.Surface((T * 2 + 10, T // 2 + 8), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 52), sh.get_rect())
    surface.blit(sh, (sx - 5, sy + int(T * 2.05)))


def _draw_bush_shadow(surface: pygame.Surface, sx: int, sy: int):
    """Draw a soft elliptical drop-shadow under a bush."""
    T = TILE_SIZE
    sh = pygame.Surface((T, T // 4 + 6), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 46), sh.get_rect())
    surface.blit(sh, (sx, sy + T - 8))


def _draw_farmhouse(surface: pygame.Surface, sx: int, sy: int, w: int, h: int):
    """
    Draw the red Swedish farmhouse.

    The house is drawn as a top-down angled view (like Stardew Valley):
      - The roof occupies the top ~60% of the building area
      - The front wall is visible at the bottom, showing facade details
      - Windows, door, chimney and white corner trim are painted on

    sx, sy — screen top-left corner of the house area
    w, h   — pixel width and height of the house footprint
    """
    T = TILE_SIZE
    roof_h = int(h * 0.55)

    # ---- Roof ----
    pygame.draw.rect(surface, C_ROOF, (sx, sy, w, roof_h))
    # Shingle rows — subtle horizontal lines with slight colour variation
    for ry in range(sy + 8, sy + roof_h - 4, 8):
        row_dark = _darken(C_ROOF, 10 + (ry - sy) // 12)
        pygame.draw.line(surface, row_dark, (sx + 2, ry), (sx + w - 2, ry), 1)
    # Ridge (bright capping strip)
    pygame.draw.rect(surface, _lighten(C_ROOF, 38), (sx, sy, w, 5))
    pygame.draw.rect(surface, _lighten(C_ROOF, 20), (sx, sy + 5, w, 3))
    # Overhang drip-shadow
    pygame.draw.rect(surface, _darken(C_ROOF, 35), (sx, sy + roof_h - 6, w, 8))

    # ---- Chimney ----
    chimney_x = sx + int(w * 0.2)
    chimney_w = int(w * 0.08)
    chimney_h = int(h * 0.18)
    # Side shadow
    pygame.draw.rect(surface, _darken(C_CHIMNEY, 30),
                     (chimney_x - 2, sy - chimney_h + 6, chimney_w + 4, chimney_h + 8))
    # Main body
    pygame.draw.rect(surface, C_CHIMNEY,
                     (chimney_x, sy - chimney_h + 8, chimney_w, chimney_h + 6))
    # Brick lines
    for bi in range(0, chimney_h, 9):
        pygame.draw.line(surface, _darken(C_CHIMNEY, 20),
                         (chimney_x, sy - chimney_h + 8 + bi),
                         (chimney_x + chimney_w - 1, sy - chimney_h + 8 + bi), 1)
    # Cap
    pygame.draw.rect(surface, _darken(C_CHIMNEY, 28),
                     (chimney_x - 5, sy - chimney_h + 4, chimney_w + 10, 8))
    pygame.draw.rect(surface, _lighten(C_CHIMNEY, 12),
                     (chimney_x - 4, sy - chimney_h + 4, chimney_w + 8, 3))
    # Smoke puffs (alpha circles)
    for ox, oy, r, a in [(2, -8, 8, 85), (6, -20, 6, 58), (2, -32, 5, 35)]:
        sm = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(sm, (195, 190, 185, a), (r + 2, r + 2), r)
        surface.blit(sm, (chimney_x + chimney_w // 2 + ox - r - 2,
                          sy - chimney_h + oy - r - 2))

    # ---- Front wall ----
    wall_y = sy + roof_h
    wall_h = h - roof_h
    pygame.draw.rect(surface, C_HOUSE_RED, (sx, wall_y, w, wall_h))
    # Subtle horizontal board lines
    for by in range(wall_y + 14, wall_y + wall_h - 8, 16):
        pygame.draw.line(surface, _darken(C_HOUSE_RED, 16), (sx + 10, by), (sx + w - 10, by), 1)
    # Left-side wall shadow
    sh_w = pygame.Surface((w // 5, wall_h), pygame.SRCALPHA)
    for xi in range(w // 5):
        a = int(30 * (1.0 - xi / (w // 5)))
        pygame.draw.line(sh_w, (0, 0, 0, a), (xi, 0), (xi, wall_h))
    surface.blit(sh_w, (sx, wall_y))

    # ---- Foundation ----
    foundation_h = int(wall_h * 0.18)
    pygame.draw.rect(surface, C_FOUNDATION, (sx, sy + h - foundation_h, w, foundation_h))
    # Stone blocks
    for fi in range(0, w - 16, 26):
        fx = sx + fi + 2
        fy = sy + h - foundation_h + 3
        pygame.draw.rect(surface, _darken(C_FOUNDATION, 18),  (fx, fy, 22, foundation_h - 8))
        pygame.draw.rect(surface, _lighten(C_FOUNDATION, 14), (fx + 1, fy + 1, 20, 4))

    # ---- White trim ----
    trim_w = 9
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx,             wall_y, trim_w, wall_h))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx + w - trim_w, wall_y, trim_w, wall_h))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx, wall_y, w, 7))
    # Trim edge highlight
    pygame.draw.rect(surface, _lighten(C_HOUSE_TRIM, 18), (sx + 1, wall_y, 2, wall_h))
    pygame.draw.rect(surface, _lighten(C_HOUSE_TRIM, 18), (sx + w - trim_w + 1, wall_y, 2, wall_h))

    # ---- Windows ----
    win_w = int(w * 0.12)
    win_h = int(wall_h * 0.45)
    win_y = wall_y + int(wall_h * 0.12)
    window_cols = [sx + int(w * 0.08), sx + int(w * 0.24),
                   sx + int(w * 0.64), sx + int(w * 0.80)]
    for wx_ in window_cols:
        # Shadow recess
        pygame.draw.rect(surface, _darken(C_HOUSE_RED, 22),
                         (wx_ - 5, win_y - 5, win_w + 10, win_h + 10))
        # White frame
        pygame.draw.rect(surface, C_HOUSE_TRIM,
                         (wx_ - 3, win_y - 3, win_w + 6, win_h + 6))
        # Glass
        pygame.draw.rect(surface, C_WINDOW, (wx_, win_y, win_w, win_h))
        # Cross divider
        mid_wx = wx_ + win_w // 2
        mid_wy = win_y + win_h // 2
        pygame.draw.line(surface, C_HOUSE_TRIM, (mid_wx, win_y), (mid_wx, win_y + win_h), 2)
        pygame.draw.line(surface, C_HOUSE_TRIM, (wx_, mid_wy), (wx_ + win_w, mid_wy), 2)
        # Glass reflections
        pygame.draw.line(surface, (235, 248, 255),
                         (wx_ + 2, win_y + 2), (wx_ + win_w // 2 - 2, win_y + 3), 2)
        pygame.draw.line(surface, (205, 230, 248),
                         (wx_ + 2, win_y + 6), (wx_ + 5, win_y + win_h // 2), 1)
        # Flower box below window
        fb_y = win_y + win_h + 3
        pygame.draw.rect(surface, _darken(C_HOUSE_TRIM, 8),  (wx_ - 2, fb_y,     win_w + 4, 9))
        pygame.draw.rect(surface, _darken(C_HOUSE_TRIM, 22), (wx_ - 2, fb_y + 6, win_w + 4, 3))
        flower_colors = [C_FLOWERS_R, C_FLOWERS_Y, C_FLOWERS_R, C_FLOWERS_Y]
        for fi, fc in enumerate(flower_colors):
            fxx = wx_ + 3 + fi * (win_w // 4)
            pygame.draw.circle(surface, (38, 110, 28), (fxx, fb_y + 2), 2)
            pygame.draw.circle(surface, fc,             (fxx, fb_y - 1), 3)

    # ---- Door ----
    door_w = int(w * 0.14)
    door_h = int(wall_h * 0.72)
    door_x = sx + (w - door_w) // 2
    door_y = wall_y + wall_h - door_h - foundation_h
    # Shadow recess
    pygame.draw.rect(surface, _darken(C_HOUSE_RED, 28),
                     (door_x - 6, door_y - 6, door_w + 12, door_h + 12))
    # Frame
    pygame.draw.rect(surface, C_DOOR_FRAME, (door_x - 4, door_y - 4, door_w + 8, door_h + 8))
    # Door surface
    pygame.draw.rect(surface, C_DOOR, (door_x, door_y, door_w, door_h))
    # Raised panels
    panel_margin = 6
    panel_w = door_w - panel_margin * 2
    panel_h = (door_h - panel_margin * 3) // 2
    for pi in range(2):
        py_ = door_y + panel_margin + pi * (panel_h + panel_margin)
        pygame.draw.rect(surface, _darken(C_DOOR, 22), (door_x + panel_margin,     py_,     panel_w,     panel_h))
        pygame.draw.rect(surface, _lighten(C_DOOR, 18),(door_x + panel_margin + 1, py_ + 1, panel_w - 2, 3))
        pygame.draw.rect(surface, _lighten(C_DOOR, 18),(door_x + panel_margin + 1, py_ + 1, 3, panel_h - 2))
    # Handle
    pygame.draw.circle(surface, (200, 165, 60), (door_x + door_w - 8, door_y + door_h // 2), 5)
    pygame.draw.circle(surface, (245, 215, 105),(door_x + door_w - 9, door_y + door_h // 2 - 1), 2)

    # ---- Sign above door ----
    sign_x = door_x - 12
    sign_y = door_y - 23
    sign_w = door_w + 24
    sign_h = 17
    pygame.draw.rect(surface, _darken(C_HOUSE_RED, 12), (sign_x + 1, sign_y + 1, sign_w, sign_h))
    pygame.draw.rect(surface, (148, 108, 50),             (sign_x,     sign_y,     sign_w, sign_h))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sign_x, sign_y, sign_w, 3))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sign_x, sign_y + sign_h - 3, sign_w, 3))
    pygame.draw.rect(surface, _lighten((148, 108, 50), 28), (sign_x + 2, sign_y + 4, sign_w - 4, 5))


def _draw_flagpole(surface: pygame.Surface, sx: int, sy: int, time_of_day: float):
    """
    Draw a tall wooden flagpole topped with the Swedish flag.

    The flag gently waves — we simulate this with a simple sine-wave
    distortion applied to the flag's width.

    sx, sy — screen position of the pole's base tile (top-left)
    """
    T = TILE_SIZE

    # Pole base (a small stone base block)
    base_w, base_h = 16, 8
    bx = sx + T // 2 - base_w // 2
    by = sy + T * 5 - base_h
    pygame.draw.rect(surface, (110, 100, 90),  (bx, by, base_w, base_h))
    pygame.draw.rect(surface, (130, 120, 110), (bx + 2, by, base_w - 4, 4))

    # Pole itself (tall thin vertical line)
    pole_x  = sx + T // 2
    pole_top = sy - T * 1          # extends well above the tile
    pole_bot = sy + T * 5 - base_h
    pole_w   = 5
    pygame.draw.rect(surface, _darken(C_POLE, 20),
                     (pole_x - pole_w // 2 - 1, pole_top, pole_w + 2, pole_bot - pole_top))
    pygame.draw.rect(surface, C_POLE,
                     (pole_x - pole_w // 2,     pole_top, pole_w,     pole_bot - pole_top))
    # Pole tip (small gold ball)
    pygame.draw.circle(surface, C_FLAG_YELLOW, (pole_x, pole_top), 6)
    pygame.draw.circle(surface, (255, 220, 60), (pole_x - 1, pole_top - 1), 3)

    # Flag (inverted: blue background with yellow Nordic cross)
    flag_x = pole_x + pole_w // 2 + 1
    flag_y = pole_top + 8
    flag_w = T * 2 - 4    # flag width in pixels
    flag_h = T             # flag height in pixels

    # Gentle waving animation using sine
    wave = math.sin(time_of_day * 50.0) * 3
    wave2 = math.sin(time_of_day * 50.0 + 1.0) * 2

    # Draw flag background as a series of vertical slices with slight height variation
    slices = 12
    slice_w = flag_w // slices
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = flag_y + wave_offset
        sh_ = flag_h - abs(wave_offset)
        pygame.draw.rect(surface, C_FLAG_BLUE, (sx_, sy_, slice_w + 1, sh_))

    # Nordic cross (horizontal bar)
    cross_y   = flag_y + flag_h // 2 - 3
    cross_h   = 8
    cross_col_w = int(flag_w * 0.30)    # cross sits 30% from left
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = cross_y + wave_offset
        pygame.draw.rect(surface, C_FLAG_YELLOW, (sx_, sy_, slice_w + 1, cross_h))

    # Nordic cross (vertical bar — positioned 30% from left)
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = flag_y + wave_offset
        if flag_x + cross_col_w - 4 <= sx_ <= flag_x + cross_col_w + 4:
            pygame.draw.rect(surface, C_FLAG_YELLOW, (sx_, sy_, slice_w + 1, flag_h - abs(wave_offset)))

    # Flag outline / shadow edge
    pygame.draw.rect(surface, _darken(C_FLAG_BLUE, 40),
                     (flag_x, flag_y, 2, flag_h))


def _draw_tree(surface: pygame.Surface, sx: int, sy: int):
    """
    Draw a lush Swedish pine/birch tree with layered canopy and highlights.
    Trees are roughly 2 tiles wide × 3 tiles tall.
    """
    T  = TILE_SIZE
    cx = sx + T

    # Trunk — shadow side + lit side + highlight stripe
    trunk_w = 11
    trunk_h = int(T * 1.55)
    tx = cx - trunk_w // 2
    ty = sy + int(T * 1.75)
    pygame.draw.rect(surface, _darken(C_TREE_TRUNK, 28), (tx - 2, ty, trunk_w + 4, trunk_h))
    pygame.draw.rect(surface, C_TREE_TRUNK,               (tx,     ty, trunk_w,     trunk_h))
    pygame.draw.rect(surface, _lighten(C_TREE_TRUNK, 22), (tx + 2, ty + 4, 3, trunk_h - 8))
    # Root flare
    pygame.draw.ellipse(surface, _darken(C_TREE_TRUNK, 22),
                        (tx - 6, ty + trunk_h - 8, trunk_w + 12, 11))

    # Canopy layers — bottom-most to top.  Each progressively smaller and raised.
    # (dy_from_sy, radius, base_colour, x_offset)
    layers = [
        (int(T * 1.58), int(T * 0.96), C_TREE_DARK,   0),
        (int(T * 1.05), int(T * 0.82), C_TREE_MID,   -3),
        (int(T * 0.58), int(T * 0.70), C_TREE_DARK,   2),
        (int(T * 0.14), int(T * 0.55), C_TREE_MID,   -2),
        (int(T * -0.24),int(T * 0.38), C_TREE_LIGHT,  0),
    ]
    for dy, r, col, ox in layers:
        cy_ = sy + dy
        # Offset drop-shadow (slightly south-east)
        pygame.draw.circle(surface, _darken(col, 26), (cx + ox + 4, cy_ + 4), r)
        # Main sphere
        pygame.draw.circle(surface, col,               (cx + ox,     cy_),     r)
        # Sub-highlight (top-left, simulating sun from upper-left)
        hx_ = cx + ox - r // 3
        hy_ = cy_ - r // 3
        pygame.draw.circle(surface, _lighten(col, 26), (hx_, hy_), r // 3)
        # Tiny bright specular dot
        pygame.draw.circle(surface, _lighten(col, 44), (hx_ - 2, hy_ - 2), max(2, r // 7))


def _draw_bush(surface: pygame.Surface, sx: int, sy: int):
    """Draw a detailed rounded bush with berries and highlight."""
    T  = TILE_SIZE
    cx = sx + T // 2
    cy = sy + T - 14

    r = T // 3 + 3
    # Dark base shadow
    pygame.draw.circle(surface, _darken(C_BUSH, 32), (cx,     cy + 4), r + 2)
    # Three overlapping lobes
    pygame.draw.circle(surface, C_BUSH,               (cx - 6, cy + 1), r - 1)
    pygame.draw.circle(surface, C_BUSH,               (cx + 6, cy + 1), r - 1)
    pygame.draw.circle(surface, _lighten(C_BUSH, 14), (cx,     cy - 4), r - 2)
    # Top highlight
    pygame.draw.circle(surface, _lighten(C_BUSH, 30), (cx - 7, cy - 5), r // 3)
    # Red berries
    for bx_, by_ in [(cx - 4, cy - 1), (cx + 5, cy - 3), (cx, cy + 3)]:
        pygame.draw.circle(surface, (195, 48, 38),  (bx_, by_), 3)
        pygame.draw.circle(surface, (245, 140, 130),(bx_ - 1, by_ - 1), 1)


def _draw_sell_zone(surface: pygame.Surface, sx: int, sy: int):
    """
    Draw a market stall where the player sells harvested potatoes.
    Spans 2×2 tiles; awning extends one tile above sy.
    """
    T  = TILE_SIZE
    W  = T * 2          # total stall width

    # ---- Vertical support posts ----
    post_col = (105, 72, 32)
    post_hi  = _lighten(post_col, 22)
    for px in (sx + 8, sx + W - 16):
        pygame.draw.rect(surface, _darken(post_col, 18), (px - 1, sy - T,     8, T + T // 2))
        pygame.draw.rect(surface, post_col,               (px,     sy - T,     6, T + T // 2))
        pygame.draw.rect(surface, post_hi,                (px + 1, sy - T + 3, 2, T + T // 2 - 6))

    # ---- Horizontal beam connecting the tops of the posts ----
    beam_col = (120, 84, 38)
    pygame.draw.rect(surface, _darken(beam_col, 18), (sx + 8,  sy - T - 1, W - 16, 9))
    pygame.draw.rect(surface, beam_col,               (sx + 8,  sy - T,     W - 16, 7))
    pygame.draw.rect(surface, _lighten(beam_col, 18), (sx + 10, sy - T + 1, W - 20, 2))

    # ---- Striped awning ----
    awn_y  = sy - T - 16
    awn_h  = 18
    stripe_a = (200, 55, 45)    # Swedish red
    stripe_b = (235, 228, 210)  # cream
    n_stripes = 7
    sw = (W - 18) // n_stripes
    for i in range(n_stripes):
        sc = stripe_a if i % 2 == 0 else stripe_b
        pygame.draw.rect(surface, sc, (sx + 9 + i * sw, awn_y, sw + 1, awn_h))
    # Awning top edge shadow
    pygame.draw.rect(surface, _darken(stripe_a, 30), (sx + 9, awn_y, W - 18, 3))
    # Scalloped fringe along the bottom of the awning
    fringe_y  = awn_y + awn_h
    fringe_col = _darken(stripe_a, 10)
    fringe_n   = 6
    fw = (W - 18) // fringe_n
    for i in range(fringe_n):
        fx = sx + 9 + i * fw
        pygame.draw.polygon(surface, fringe_col,
                            [(fx, fringe_y), (fx + fw // 2, fringe_y + 9), (fx + fw, fringe_y)])
        pygame.draw.polygon(surface, _lighten(fringe_col, 18),
                            [(fx + 2, fringe_y), (fx + fw // 2, fringe_y + 6), (fx + fw - 2, fringe_y)])

    # ---- Hanging sign on left post ----
    sgn_x = sx + 16
    sgn_y = sy - T + 10
    sgn_w, sgn_h = 38, 26
    # Hanging cord
    pygame.draw.line(surface, (90, 62, 26), (sgn_x + sgn_w // 2, sgn_y - 5), (sgn_x + sgn_w // 2, sy - T + 8), 2)
    # Board shadow
    pygame.draw.rect(surface, _darken((152, 108, 46), 20), (sgn_x + 2, sgn_y + 2, sgn_w, sgn_h), border_radius=3)
    # Board
    pygame.draw.rect(surface, (152, 108, 46), (sgn_x, sgn_y, sgn_w, sgn_h), border_radius=3)
    pygame.draw.rect(surface, _lighten((152, 108, 46), 22), (sgn_x + 2, sgn_y + 2, sgn_w - 4, 3), border_radius=2)
    pygame.draw.rect(surface, (190, 148, 72), (sgn_x, sgn_y, sgn_w, sgn_h), 2, border_radius=3)
    # Potato icon on sign
    pc = sgn_x + sgn_w // 2
    py_ = sgn_y + sgn_h // 2 + 2
    pygame.draw.ellipse(surface, _darken((162, 118, 50), 20), (pc - 10, py_ - 6, 20, 14))
    pygame.draw.ellipse(surface, (162, 118, 50),              (pc - 10, py_ - 7, 20, 13))
    pygame.draw.ellipse(surface, _lighten((162, 118, 50), 30),(pc - 7,  py_ - 6, 9,  5))
    # Small sprout on top of potato icon
    pygame.draw.line(surface, (55, 140, 38), (pc, py_ - 7), (pc, py_ - 12), 2)
    pygame.draw.ellipse(surface, (70, 165, 48), (pc - 4, py_ - 14, 5, 4))
    pygame.draw.ellipse(surface, (70, 165, 48), (pc,     py_ - 14, 5, 4))
    # Gold coin on sign (price indicator)
    coin_col = (220, 185, 50)
    pygame.draw.circle(surface, _darken(coin_col, 18), (sgn_x + sgn_w - 8, sgn_y + 8), 6)
    pygame.draw.circle(surface, coin_col,               (sgn_x + sgn_w - 9, sgn_y + 7), 6)
    pygame.draw.circle(surface, _lighten(coin_col, 28), (sgn_x + sgn_w - 11, sgn_y + 5), 3)

    # ---- Table ----
    tbl_y    = sy + T // 2
    tbl_h    = 10
    tbl_col  = (195, 162, 88)
    cloth_col = (215, 195, 135)
    # Table shadow
    pygame.draw.rect(surface, _darken(tbl_col, 30), (sx + 5, tbl_y + 2, W - 10, tbl_h + 2))
    # Tablecloth surface
    pygame.draw.rect(surface, _darken(cloth_col, 14), (sx + 4, tbl_y,     W - 8, tbl_h + 2))
    pygame.draw.rect(surface, cloth_col,               (sx + 4, tbl_y,     W - 8, tbl_h))
    pygame.draw.rect(surface, _lighten(cloth_col, 22), (sx + 6, tbl_y + 1, W - 12, 2))
    # Cloth drape at front
    pygame.draw.rect(surface, _darken(cloth_col, 10), (sx + 4, tbl_y + tbl_h, W - 8, 12))
    # Table legs
    leg_col = _darken(tbl_col, 38)
    for lx in (sx + 10, sx + W - 17):
        pygame.draw.rect(surface, leg_col, (lx, tbl_y + tbl_h + 12, 7, T // 2 - 4))

    # ---- Potato pile on the table ----
    pot_col = (162, 118, 50)
    pot_hi  = _lighten(pot_col, 35)
    pot_sh  = _darken(pot_col, 28)
    for px, py2, pr in [
        (sx + T - 12, tbl_y - 10, 10),
        (sx + T + 2,  tbl_y - 8,   9),
        (sx + T - 22, tbl_y - 6,   8),
        (sx + T + 14, tbl_y - 7,   9),
        (sx + T - 6,  tbl_y - 18,  8),
    ]:
        pygame.draw.circle(surface, pot_sh,  (px + 2, py2 + 3), pr)
        pygame.draw.circle(surface, pot_col, (px,     py2),     pr)
        pygame.draw.circle(surface, pot_hi,  (px - 3, py2 - 3), pr // 3 + 1)

    # ---- Gold coin pile beside potatoes ----
    for cx_, cy_, cr in [(sx + W - 20, tbl_y - 9, 7), (sx + W - 17, tbl_y - 5, 7),
                          (sx + W - 23, tbl_y - 5, 6)]:
        pygame.draw.circle(surface, _darken(coin_col, 22), (cx_ + 1, cy_ + 1), cr)
        pygame.draw.circle(surface, coin_col,               (cx_,     cy_),     cr)
        pygame.draw.circle(surface, _lighten(coin_col, 30), (cx_ - 2, cy_ - 2), cr // 3 + 1)


# ---------------------------------------------------------------------------
# Tree placement
# ---------------------------------------------------------------------------

def _build_tree_list() -> list:
    """
    Return a list of (col, row, kind) tuples for trees and bushes.
    Manually positioned for a natural-looking arrangement around the map.
    """
    trees = []

    # Trees along the top edge
    for col in range(0, 60, 5):
        if col not in range(HOUSE_COL - 1, HOUSE_COL + HOUSE_COLS + 2):
            trees.append((col, 0, "tree"))

    # Trees along the left edge
    for row in range(15, 45, 6):
        trees.append((0, row, "tree"))

    # Trees along the right edge
    for row in range(0, 45, 5):
        trees.append((57, row, "tree"))

    # Trees along the bottom edge
    for col in range(0, 60, 6):
        trees.append((col, 42, "tree"))

    # A small copse of trees to the left of the farm
    for col, row in [(35, 20), (36, 22), (37, 19), (38, 21)]:
        trees.append((col, row, "tree"))

    # Bushes near the farmhouse
    for col, row in [(HOUSE_COL + HOUSE_COLS, HOUSE_ROW + 2),
                     (HOUSE_COL - 1, HOUSE_ROW + 3),
                     (HOUSE_COL - 1, HOUSE_ROW + 5)]:
        trees.append((col, row, "bush"))

    # Some bushes near the farm fence
    for col, row in [(FARM_COL + FARM_COLS + 1, FARM_ROW + 2),
                     (FARM_COL + FARM_COLS + 1, FARM_ROW + 5),
                     (FARM_COL - 2, FARM_ROW + 3)]:
        trees.append((col, row, "bush"))

    return trees


# ---------------------------------------------------------------------------
# Colour utility helpers
# ---------------------------------------------------------------------------

def _lerp_colour(a: tuple, b: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB colour tuples. t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _lighten(colour: tuple, amount: int) -> tuple:
    """Return a brighter version of the colour."""
    return tuple(min(255, c + amount) for c in colour)


def _darken(colour: tuple, amount: int) -> tuple:
    """Return a darker version of the colour."""
    return tuple(max(0, c - amount) for c in colour)
