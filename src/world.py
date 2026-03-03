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

    def __init__(self):
        self.tilemap    = TileMap()
        self.crop_mgr   = CropManager()
        self.player     = Player()
        self.camera     = Camera()

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
        If the player walks onto the sell zone with potatoes,
        automatically sell them.
        """
        if self.player.potatoes <= 0:
            return

        sz_x = self._sell_zone_col * TILE_SIZE
        sz_y = self._sell_zone_row * TILE_SIZE
        sell_rect = pygame.Rect(sz_x, sz_y, TILE_SIZE * 2, TILE_SIZE * 2)

        if self.player.rect.colliderect(sell_rect):
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

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
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
        """
        # 1. Sky (fills behind everything — in case the world doesn't fully cover screen)
        sky_colour = self._get_sky_colour()
        surface.fill(sky_colour)

        # 2 & 3. Tilemap (ground + farm soil)
        self.tilemap.draw(surface, self.camera)

        # 4. Crops
        self.crop_mgr.draw(surface, self.camera)

        # 5. Trees and bushes
        for (col, row, kind) in self._trees:
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE
            if self.camera.is_visible(wx, wy, TILE_SIZE * 2, TILE_SIZE * 3):
                sx, sy = self.camera.apply(wx, wy)
                if kind == "tree":
                    _draw_tree(surface, int(sx), int(sy))
                elif kind == "bush":
                    _draw_bush(surface, int(sx), int(sy))

        # 6. Farmhouse (drawn over the T_HOUSE_FLOOR tiles)
        hx = HOUSE_COL * TILE_SIZE
        hy = HOUSE_ROW * TILE_SIZE
        hw = HOUSE_COLS * TILE_SIZE
        hh = HOUSE_ROWS * TILE_SIZE
        if self.camera.is_visible(hx, hy, hw, hh):
            sx, sy = self.camera.apply(hx, hy)
            _draw_farmhouse(surface, int(sx), int(sy), hw, hh)

        # 7. Flagpole
        fx = FLAG_COL * TILE_SIZE
        fy = FLAG_ROW * TILE_SIZE
        if self.camera.is_visible(fx, fy, TILE_SIZE * 2, TILE_SIZE * 6):
            sx, sy = self.camera.apply(fx, fy)
            _draw_flagpole(surface, int(sx), int(sy), self.time_of_day)

        # 8. Sell-zone marker (a simple market table visual)
        szx = self._sell_zone_col * TILE_SIZE
        szy = self._sell_zone_row * TILE_SIZE
        if self.camera.is_visible(szx, szy, TILE_SIZE * 2, TILE_SIZE * 2):
            sx, sy = self.camera.apply(szx, szy)
            _draw_sell_zone(surface, int(sx), int(sy))

        # 9. Player
        self.player.draw(surface, self.camera)

        # 10. Night overlay (semi-transparent dark layer at night)
        self._draw_night_overlay(surface)

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

    # ---- Roof (top 55% of the building) ----
    roof_h = int(h * 0.55)
    roof_rect = pygame.Rect(sx, sy, w, roof_h)
    pygame.draw.rect(surface, C_ROOF, roof_rect)

    # Roof ridge line (slightly lighter along the top)
    pygame.draw.rect(surface, _lighten(C_ROOF, 30), (sx, sy, w, 6))

    # Roof edge (overhang shadow along the bottom of the roof)
    pygame.draw.rect(surface, C_ROOF_EDGE, (sx, sy + roof_h - 4, w, 6))

    # Chimney (left side of roof)
    chimney_x = sx + int(w * 0.2)
    chimney_w = int(w * 0.08)
    chimney_h = int(h * 0.15)
    pygame.draw.rect(surface, C_CHIMNEY,
                     (chimney_x, sy - chimney_h + 8, chimney_w, chimney_h + 8))
    # Chimney cap
    pygame.draw.rect(surface, _darken(C_CHIMNEY, 20),
                     (chimney_x - 4, sy - chimney_h + 6, chimney_w + 8, 8))
    # Chimney smoke dots (decorative)
    pygame.draw.circle(surface, (180, 175, 170, 120),
                       (chimney_x + chimney_w // 2, sy - chimney_h - 4), 6)
    pygame.draw.circle(surface, (160, 155, 150, 80),
                       (chimney_x + chimney_w // 2 + 4, sy - chimney_h - 14), 5)

    # ---- Front wall (bottom 45%) ----
    wall_y = sy + roof_h
    wall_h = h - roof_h
    pygame.draw.rect(surface, C_HOUSE_RED, (sx, wall_y, w, wall_h))

    # Foundation strip at the very bottom
    foundation_h = int(wall_h * 0.18)
    pygame.draw.rect(surface, C_FOUNDATION,
                     (sx, sy + h - foundation_h, w, foundation_h))

    # ---- White corner trim ----
    trim_w = 8
    # Left edge trim
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx,         wall_y, trim_w, wall_h))
    # Right edge trim
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx + w - trim_w, wall_y, trim_w, wall_h))
    # Top of wall strip
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sx, wall_y, w, 6))

    # ---- Windows (2 on each side of the door) ----
    win_w = int(w * 0.12)
    win_h = int(wall_h * 0.45)
    win_y = wall_y + int(wall_h * 0.12)
    window_cols = [
        sx + int(w * 0.08),
        sx + int(w * 0.24),
        sx + int(w * 0.64),
        sx + int(w * 0.80),
    ]
    for wx in window_cols:
        # White frame
        pygame.draw.rect(surface, C_HOUSE_TRIM,
                         (wx - 3, win_y - 3, win_w + 6, win_h + 6))
        # Glass pane (light blue)
        pygame.draw.rect(surface, C_WINDOW,
                         (wx, win_y, win_w, win_h))
        # Window cross-divider
        mid_wx = wx + win_w // 2
        mid_wy = win_y + win_h // 2
        pygame.draw.line(surface, C_HOUSE_TRIM, (mid_wx, win_y), (mid_wx, win_y + win_h), 2)
        pygame.draw.line(surface, C_HOUSE_TRIM, (wx, mid_wy), (wx + win_w, mid_wy), 2)
        # Reflection glint
        pygame.draw.line(surface, (220, 240, 255),
                         (wx + 2, win_y + 2), (wx + win_w // 2 - 2, win_y + 2), 2)

    # ---- Door (centre of wall) ----
    door_w = int(w * 0.14)
    door_h = int(wall_h * 0.72)
    door_x = sx + (w - door_w) // 2
    door_y = wall_y + wall_h - door_h - foundation_h
    # Door frame (white)
    pygame.draw.rect(surface, C_DOOR_FRAME,
                     (door_x - 4, door_y - 4, door_w + 8, door_h + 8))
    # Door panel (dark wood)
    pygame.draw.rect(surface, C_DOOR, (door_x, door_y, door_w, door_h))
    # Door panels (decorative raised panels)
    panel_margin = 6
    panel_w = door_w - panel_margin * 2
    panel_h = (door_h - panel_margin * 3) // 2
    for pi in range(2):
        py_ = door_y + panel_margin + pi * (panel_h + panel_margin)
        pygame.draw.rect(surface, _lighten(C_DOOR, 20),
                         (door_x + panel_margin, py_, panel_w, panel_h))
        pygame.draw.rect(surface, _darken(C_DOOR, 15),
                         (door_x + panel_margin + 2, py_ + 2, panel_w - 4, panel_h - 4))
    # Door handle (small circle)
    pygame.draw.circle(surface, (180, 150, 60),
                       (door_x + door_w - 8, door_y + door_h // 2), 4)

    # ---- House name sign above door ----
    # (Font would look nicer but we avoid requiring font files)
    sign_x = door_x - 10
    sign_y = door_y - 20
    sign_w = door_w + 20
    sign_h = 16
    pygame.draw.rect(surface, (140, 100, 45), (sign_x, sign_y, sign_w, sign_h))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sign_x, sign_y, sign_w, 3))
    pygame.draw.rect(surface, C_HOUSE_TRIM, (sign_x, sign_y + sign_h - 3, sign_w, 3))


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

    # Flag (Swedish: yellow/gold background with blue Nordic cross)
    flag_x = pole_x + pole_w // 2 + 1
    flag_y = pole_top + 8
    flag_w = T * 2 - 4    # flag width in pixels
    flag_h = T             # flag height in pixels

    # Gentle waving animation using sine
    wave = math.sin(time_of_day * 50.0) * 3
    wave2 = math.sin(time_of_day * 50.0 + 1.0) * 2

    # Draw flag as a series of vertical slices with slight height variation
    slices = 12
    slice_w = flag_w // slices
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = flag_y + wave_offset
        sh_ = flag_h - abs(wave_offset)
        pygame.draw.rect(surface, C_FLAG_YELLOW, (sx_, sy_, slice_w + 1, sh_))

    # Nordic cross (horizontal bar)
    cross_y   = flag_y + flag_h // 2 - 3
    cross_h   = 8
    cross_col_w = int(flag_w * 0.30)    # cross sits 30% from left
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = cross_y + wave_offset
        pygame.draw.rect(surface, C_FLAG_BLUE, (sx_, sy_, slice_w + 1, cross_h))

    # Nordic cross (vertical bar — positioned 30% from left)
    for i in range(slices):
        wave_offset = int(math.sin(i / slices * 3.14 + time_of_day * 50.0) * 3)
        sx_ = flag_x + i * slice_w
        sy_ = flag_y + wave_offset
        if flag_x + cross_col_w - 4 <= sx_ <= flag_x + cross_col_w + 4:
            pygame.draw.rect(surface, C_FLAG_BLUE, (sx_, sy_, slice_w + 1, flag_h - abs(wave_offset)))

    # Flag outline / shadow edge
    pygame.draw.rect(surface, _darken(C_FLAG_YELLOW, 40),
                     (flag_x, flag_y, 2, flag_h))


def _draw_tree(surface: pygame.Surface, sx: int, sy: int):
    """
    Draw a tall Swedish pine/birch style tree.
    Trees are roughly 2 tiles wide × 3 tiles tall.
    """
    T  = TILE_SIZE
    cx = sx + T          # centre x of the 2-tile-wide tree

    # Trunk
    trunk_w = 10
    trunk_h = int(T * 1.4)
    trunk_x = cx - trunk_w // 2
    trunk_y = sy + int(T * 1.8)
    pygame.draw.rect(surface, _darken(C_TREE_TRUNK, 20),
                     (trunk_x - 2, trunk_y, trunk_w + 4, trunk_h))
    pygame.draw.rect(surface, C_TREE_TRUNK,
                     (trunk_x, trunk_y, trunk_w, trunk_h))

    # Three canopy layers (wider at bottom, narrower at top — pine silhouette)
    layers = [
        # (centre_y_offset, radius, colour)
        (int(T * 1.6),  int(T * 0.90), C_TREE_DARK),
        (int(T * 1.0),  int(T * 0.75), C_TREE_MID),
        (int(T * 0.4),  int(T * 0.60), C_TREE_LIGHT),
        (int(T * -0.1), int(T * 0.40), C_TREE_MID),
    ]
    for dy, r, col in layers:
        pygame.draw.circle(surface, _darken(col, 15), (cx,     sy + dy + 2), r)
        pygame.draw.circle(surface, col,              (cx,     sy + dy),     r)
        pygame.draw.circle(surface, _lighten(col, 15),(cx - r//3, sy + dy - r//3), r // 3)


def _draw_bush(surface: pygame.Surface, sx: int, sy: int):
    """Draw a small round bush — occupies roughly one tile."""
    T  = TILE_SIZE
    cx = sx + T // 2
    cy = sy + T - 12

    r = T // 3
    pygame.draw.circle(surface, _darken(C_BUSH, 20), (cx,     cy + 2), r + 2)
    pygame.draw.circle(surface, C_BUSH,              (cx - 4, cy),     r)
    pygame.draw.circle(surface, C_BUSH,              (cx + 4, cy),     r)
    pygame.draw.circle(surface, C_BUSH,              (cx,     cy - 4), r - 2)
    pygame.draw.circle(surface, _lighten(C_BUSH, 20),(cx - 5, cy - 4), r // 2)


def _draw_sell_zone(surface: pygame.Surface, sx: int, sy: int):
    """
    Draw a small market table / selling stall.
    The player walks here to automatically sell their harvested potatoes.
    """
    T = TILE_SIZE

    # Table top
    table_col = (190, 155, 80)
    pygame.draw.rect(surface, _darken(table_col, 20),
                     (sx + 2, sy + 10, T * 2 - 4, T - 16))
    pygame.draw.rect(surface, table_col,
                     (sx + 4, sy + 8, T * 2 - 8, T - 18))

    # Potato sack on the table
    sack_col = (180, 145, 70)
    pygame.draw.ellipse(surface, _darken(sack_col, 20),
                        (sx + T - 14, sy, 28, 20))
    pygame.draw.ellipse(surface, sack_col,
                        (sx + T - 12, sy + 1, 24, 18))

    # "SELL" sign
    sign_col = (200, 170, 80)
    pygame.draw.rect(surface, (80, 55, 20), (sx + 4, sy - 14, T * 2 - 8, 14))
    pygame.draw.rect(surface, sign_col,     (sx + 6, sy - 12, T * 2 - 12, 10))

    # Table legs
    leg_col = _darken(table_col, 30)
    pygame.draw.rect(surface, leg_col, (sx + 6,      sy + T - 8, 6, 10))
    pygame.draw.rect(surface, leg_col, (sx + T*2 - 12, sy + T - 8, 6, 10))


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
