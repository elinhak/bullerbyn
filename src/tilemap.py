"""
tilemap.py — The Game World Grid
==================================
The world is divided into a grid of tiles (like graph paper).
Each cell in the grid has:
  1. A BASE TILE  — what the ground looks like (grass, path, water, etc.)
  2. A FARM STATE — only for cells inside the farm plot (untilled, tilled, watered)

This file defines:
  - Tile ID constants (T_GRASS, T_PATH, etc.)
  - Farm state constants (FS_NONE, FS_DRY, etc.)
  - The TileMap class that stores and draws the map
  - generate_map() which builds the initial world layout

Coordinate system:
  Tile (col, row) maps to world pixel (col * TILE_SIZE, row * TILE_SIZE)
"""

import pygame
import random
from src.settings import (
    TILE_SIZE, MAP_COLS, MAP_ROWS,
    HOUSE_COL, HOUSE_ROW, HOUSE_COLS, HOUSE_ROWS,
    FLAG_COL, FLAG_ROW,
    FARM_COL, FARM_ROW, FARM_COLS, FARM_ROWS,
    FARM_INNER_COL, FARM_INNER_ROW, FARM_INNER_COLS, FARM_INNER_ROWS,
    C_GRASS_1, C_GRASS_2, C_PATH, C_PATH_DARK,
    C_DIRT_DRY, C_DIRT_TILLED, C_DIRT_WET,
    C_WATER, C_WATER_DARK,
    C_FENCE, C_FENCE_DARK,
    C_FLOWERS_R, C_FLOWERS_Y, C_BUSH,
)

# ---------------------------------------------------------------------------
# Tile IDs — what kind of ground is in each cell?
# ---------------------------------------------------------------------------
T_GRASS        = 0    # ordinary green grass
T_GRASS_FLOWER = 1    # grass with small wildflowers (purely decorative)
T_PATH         = 2    # packed-earth walking path
T_WATER        = 3    # water / pond (impassable)
T_HOUSE_FLOOR  = 4    # under/inside the farmhouse (impassable)
T_FENCE_H      = 5    # horizontal fence segment
T_FENCE_V      = 6    # vertical fence segment
T_FENCE_TL     = 7    # fence corner — top-left
T_FENCE_TR     = 8    # fence corner — top-right
T_FENCE_BL     = 9    # fence corner — bottom-left
T_FENCE_BR     = 10   # fence corner — bottom-right
T_FENCE_GATE   = 11   # gate in the fence (walkable, opens passage)
T_DIRT         = 12   # farmable dirt inside the fence (can be tilled)

# Which tiles block the player from walking through?
SOLID_TILES = {T_WATER, T_HOUSE_FLOOR, T_FENCE_H, T_FENCE_V,
               T_FENCE_TL, T_FENCE_TR, T_FENCE_BL, T_FENCE_BR}

# ---------------------------------------------------------------------------
# Farm State IDs — the state of the soil in each farmable cell
# ---------------------------------------------------------------------------
FS_NONE    = 0   # not a farm tile (ignore)
FS_DRY     = 1   # farmable but not yet tilled
FS_TILLED  = 2   # tilled with the hoe — ready to plant or water
FS_WATERED = 3   # tilled AND watered — crops grow one step faster today

# ---------------------------------------------------------------------------
# TileMap
# ---------------------------------------------------------------------------

class TileMap:
    """
    Stores the full game world as two 2D grids:

    self.tiles[row][col] — base tile type (T_GRASS, T_PATH, etc.)
    self.farm[row][col]  — farm soil state (FS_NONE, FS_DRY, FS_TILLED, FS_WATERED)

    The farm grid is mostly FS_NONE; only the farmable area inside the fence
    has meaningful values.
    """

    def __init__(self):
        # Build the world layout
        self.tiles, self.farm = generate_map()

        # Pre-build per-tile surfaces for fast rendering.
        # Instead of calling pygame.draw every frame for every tile,
        # we draw each tile type once into a Surface and reuse it.
        self._tile_cache = {}   # tile_id → pygame.Surface

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_tile(self, col: int, row: int) -> int:
        """Return the tile ID at (col, row), or T_GRASS if out of bounds."""
        if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
            return self.tiles[row][col]
        return T_GRASS

    def is_solid(self, col: int, row: int) -> bool:
        """Return True if the player cannot walk on this tile."""
        return self.get_tile(col, row) in SOLID_TILES

    def get_farm_state(self, col: int, row: int) -> int:
        """Return the farm soil state at (col, row)."""
        if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
            return self.farm[row][col]
        return FS_NONE

    def set_farm_state(self, col: int, row: int, state: int):
        """Update the farm soil state (e.g. when player tills or waters soil)."""
        if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
            self.farm[row][col] = state

    def is_farmable(self, col: int, row: int) -> bool:
        """Return True if this tile can be interacted with as a farm cell."""
        return self.farm[row][col] != FS_NONE if (0 <= col < MAP_COLS and 0 <= row < MAP_ROWS) else False

    # ------------------------------------------------------------------
    # Pixel ↔ Tile coordinate helpers
    # ------------------------------------------------------------------

    def world_to_tile(self, world_x: float, world_y: float) -> tuple:
        """Convert world pixel coordinates to tile (col, row)."""
        return (int(world_x // TILE_SIZE), int(world_y // TILE_SIZE))

    def tile_to_world(self, col: int, row: int) -> tuple:
        """Return the world pixel position of the top-left corner of a tile."""
        return (col * TILE_SIZE, row * TILE_SIZE)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera):
        """
        Draw all visible tiles to the screen.

        We only draw tiles that are actually on screen (culling),
        which keeps the frame rate high even on large maps.
        """
        # Figure out which tile columns and rows are visible right now
        # by dividing the camera position by tile size.
        start_col = max(0, int(camera.x // TILE_SIZE))
        start_row = max(0, int(camera.y // TILE_SIZE))

        # Add 2 extra tiles on each side so edges never flicker
        end_col = min(MAP_COLS, start_col + (surface.get_width()  // TILE_SIZE) + 3)
        end_row = min(MAP_ROWS, start_row + (surface.get_height() // TILE_SIZE) + 3)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = self.tiles[row][col]

                # World position of this tile's top-left corner
                wx = col * TILE_SIZE
                wy = row * TILE_SIZE

                # Screen position (shift by camera offset)
                sx = wx - camera.x
                sy = wy - camera.y

                rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)

                # Draw the base tile
                _draw_tile(surface, rect, tile_id, col, row)

                # Draw farm soil overlay on top of base tile
                farm_state = self.farm[row][col]
                if farm_state != FS_NONE:
                    _draw_farm_cell(surface, rect, farm_state)


# ---------------------------------------------------------------------------
# Internal drawing functions
# ---------------------------------------------------------------------------

def _draw_tile(surface: pygame.Surface, rect: pygame.Rect, tile_id: int,
               col: int = 0, row: int = 0):
    """
    Draw a single base tile into the given screen rect.
    col, row are world-space tile coordinates (used for stable patterns).
    """
    T = TILE_SIZE

    if tile_id in (T_GRASS, T_GRASS_FLOWER):
        colour = C_GRASS_1 if (col + row) % 2 == 0 else C_GRASS_2
        pygame.draw.rect(surface, colour, rect)

        # Subtle hand-painted texture: deterministic dots from a cheap integer hash
        h = (col * 2654435761 + row * 2246822519) & 0xFFFFFFFF
        dot_dark  = (max(0, colour[0] - 22), max(0, colour[1] - 20), max(0, colour[2] - 14))
        dot_light = (min(255, colour[0] + 18), min(255, colour[1] + 16), min(255, colour[2] + 10))
        for i in range(5):
            hh = (h ^ (h >> (i * 3 + 4))) & 0xFFFFFFFF
            dx = hh % (T - 8) + 4
            dy = (hh >> 8) % (T - 8) + 4
            dc = dot_dark if (hh >> 16) & 1 else dot_light
            r  = 1 + ((hh >> 20) & 1)
            pygame.draw.circle(surface, dc, (rect.x + dx, rect.y + dy), r)

        if tile_id == T_GRASS_FLOWER:
            cx, cy = rect.centerx, rect.centery
            fc = C_FLOWERS_R if (col * 3 + row) % 3 == 0 else C_FLOWERS_Y
            for dx, dy in [(-8, -5), (6, 4), (-3, 7), (9, -8)]:
                pygame.draw.circle(surface, fc, (cx + dx, cy + dy), 3)
                pygame.draw.circle(surface, (255, 248, 220), (cx + dx, cy + dy), 1)

    elif tile_id == T_PATH:
        pygame.draw.rect(surface, C_PATH, rect)
        # Edge lines
        pygame.draw.line(surface, C_PATH_DARK, (rect.x, rect.y + 12), (rect.right, rect.y + 12), 1)
        pygame.draw.line(surface, C_PATH_DARK, (rect.x, rect.y + 34), (rect.right, rect.y + 34), 1)
        # Pebbles via deterministic hash
        h = (col * 1619 + row * 2971) & 0xFFFFFFFF
        pebble_hi = (min(255, C_PATH[0] + 30), min(255, C_PATH[1] + 24), min(255, C_PATH[2] + 16))
        for i in range(6):
            hh = (h * (i * 6271 + 1)) & 0xFFFFFF
            px = rect.x + hh % (T - 8) + 4
            py = rect.y + (hh >> 8) % (T - 8) + 4
            pr = 1 + (hh >> 16) % 2
            pc = C_PATH_DARK if (hh >> 18) & 1 else pebble_hi
            pygame.draw.circle(surface, pc, (px, py), pr)

    elif tile_id == T_WATER:
        pygame.draw.rect(surface, C_WATER, rect)
        # Top-edge depth shadow
        pygame.draw.rect(surface, C_WATER_DARK, (rect.x, rect.y, T, 4))
        # Ripple lines
        water_hi = (min(255, C_WATER[0] + 38), min(255, C_WATER[1] + 30), min(255, C_WATER[2] + 20))
        for ry_off, rlen, rx_off in [(14, T - 14, 4), (26, T - 18, 10), (38, T - 10, 6)]:
            pygame.draw.line(surface, C_WATER_DARK,
                             (rect.x + rx_off, rect.y + ry_off),
                             (rect.x + rx_off + rlen, rect.y + ry_off), 2)
        # Highlight shimmer
        pygame.draw.line(surface, water_hi,
                         (rect.x + 6, rect.y + 8), (rect.x + T - 10, rect.y + 8), 2)

    elif tile_id == T_HOUSE_FLOOR:
        pygame.draw.rect(surface, (50, 100, 42), rect)

    elif tile_id == T_DIRT:
        pygame.draw.rect(surface, C_DIRT_DRY, rect)
        # Soil texture dots
        h = (col * 1619 + row * 2971) & 0xFFFFFFFF
        dc = (max(0, C_DIRT_DRY[0] - 24), max(0, C_DIRT_DRY[1] - 16), max(0, C_DIRT_DRY[2] - 10))
        for i in range(4):
            hh = (h * (i * 4127 + 1)) & 0xFFFFFF
            px = rect.x + hh % (T - 8) + 4
            py = rect.y + (hh >> 8) % (T - 8) + 4
            pygame.draw.circle(surface, dc, (px, py), 2)

    elif tile_id in (T_FENCE_H, T_FENCE_V,
                     T_FENCE_TL, T_FENCE_TR, T_FENCE_BL, T_FENCE_BR,
                     T_FENCE_GATE):
        base_colour = C_GRASS_1 if (col + row) % 2 == 0 else C_GRASS_2
        pygame.draw.rect(surface, base_colour, rect)
        # Match grass texture under fence
        h = (col * 2654435761 + row * 2246822519) & 0xFFFFFFFF
        dot_dark = (max(0, base_colour[0] - 22), max(0, base_colour[1] - 20), max(0, base_colour[2] - 14))
        for i in range(3):
            hh = (h ^ (h >> (i * 3 + 4))) & 0xFFFFFFFF
            dx = hh % (T - 8) + 4
            dy = (hh >> 8) % (T - 8) + 4
            pygame.draw.circle(surface, dot_dark, (rect.x + dx, rect.y + dy), 1)
        _draw_fence_segment(surface, rect, tile_id)

    else:
        pygame.draw.rect(surface, C_GRASS_1, rect)


def _draw_fence_segment(surface: pygame.Surface, rect: pygame.Rect, tile_id: int):
    """Draw a wooden fence post/rail into the tile rect."""
    T   = TILE_SIZE
    cx  = rect.x + T // 2
    cy  = rect.y + T // 2
    top = rect.y
    bot = rect.bottom
    lft = rect.x
    rgt = rect.right
    MID = T // 2     # offset to centre of tile
    RH  = 6          # rail half-height (the horizontal bar)

    if tile_id == T_FENCE_GATE:
        # Gate: draw a gap with two small posts on either side
        # Post left
        pygame.draw.rect(surface, C_FENCE_DARK, (lft + 6, top + 8, 8, T - 16))
        pygame.draw.rect(surface, C_FENCE, (lft + 8, top + 8, 6, T - 16))
        # Post right
        pygame.draw.rect(surface, C_FENCE_DARK, (rgt - 14, top + 8, 8, T - 16))
        pygame.draw.rect(surface, C_FENCE, (rgt - 12, top + 8, 6, T - 16))
        return

    # Horizontal fence: two rails running left-to-right, one post at centre
    if tile_id in (T_FENCE_H, T_FENCE_TL, T_FENCE_TR, T_FENCE_BL, T_FENCE_BR):
        # Rail at 1/3 height
        rail_y1 = rect.y + T // 3
        pygame.draw.rect(surface, C_FENCE_DARK, (lft, rail_y1 - 1, T, RH + 1))
        pygame.draw.rect(surface, C_FENCE,      (lft, rail_y1,     T, RH - 1))
        # Rail at 2/3 height
        rail_y2 = rect.y + (2 * T) // 3
        pygame.draw.rect(surface, C_FENCE_DARK, (lft, rail_y2 - 1, T, RH + 1))
        pygame.draw.rect(surface, C_FENCE,      (lft, rail_y2,     T, RH - 1))

    # Vertical fence: two rails running top-to-bottom
    if tile_id in (T_FENCE_V, T_FENCE_TL, T_FENCE_TR, T_FENCE_BL, T_FENCE_BR):
        rail_x1 = rect.x + T // 3
        pygame.draw.rect(surface, C_FENCE_DARK, (rail_x1 - 1, top, RH + 1, T))
        pygame.draw.rect(surface, C_FENCE,      (rail_x1,     top, RH - 1, T))
        rail_x2 = rect.x + (2 * T) // 3
        pygame.draw.rect(surface, C_FENCE_DARK, (rail_x2 - 1, top, RH + 1, T))
        pygame.draw.rect(surface, C_FENCE,      (rail_x2,     top, RH - 1, T))

    # Centre post (tall vertical plank)
    post_w = 10
    pygame.draw.rect(surface, C_FENCE_DARK, (cx - post_w//2 - 1, top, post_w + 2, T))
    pygame.draw.rect(surface, C_FENCE,      (cx - post_w//2,     top, post_w,     T))


def _draw_farm_cell(surface: pygame.Surface, rect: pygame.Rect, farm_state: int):
    """Draw the soil overlay on a farmable tile."""
    T = TILE_SIZE

    if farm_state == FS_DRY:
        pygame.draw.rect(surface, C_DIRT_DRY, rect)
        # Soil clump dots
        dc = (max(0, C_DIRT_DRY[0] - 24), max(0, C_DIRT_DRY[1] - 16), max(0, C_DIRT_DRY[2] - 10))
        lc = (min(255, C_DIRT_DRY[0] + 20), min(255, C_DIRT_DRY[1] + 14), min(255, C_DIRT_DRY[2] + 8))
        for px, py, r, light in [(8, 12, 2, False), (24, 8, 2, False), (36, 22, 3, False),
                                  (14, 34, 2, False), (40, 38, 2, False), (20, 18, 2, True)]:
            pygame.draw.circle(surface, lc if light else dc, (rect.x + px, rect.y + py), r)

    elif farm_state == FS_TILLED:
        pygame.draw.rect(surface, C_DIRT_TILLED, rect)
        # Deeper furrows with a ridge highlight between each groove
        furrow_d = (max(0, C_DIRT_TILLED[0] - 26), max(0, C_DIRT_TILLED[1] - 15), max(0, C_DIRT_TILLED[2] - 8))
        furrow_l = (min(255, C_DIRT_TILLED[0] + 24), min(255, C_DIRT_TILLED[1] + 14), min(255, C_DIRT_TILLED[2] + 7))
        for fy in range(rect.y + 7, rect.bottom - 4, 10):
            pygame.draw.line(surface, furrow_d,  (rect.x + 4, fy),     (rect.right - 4, fy),     2)
            pygame.draw.line(surface, furrow_l,  (rect.x + 5, fy - 2), (rect.right - 5, fy - 2), 1)

    elif farm_state == FS_WATERED:
        pygame.draw.rect(surface, C_DIRT_WET, rect)
        furrow_d = (max(0, C_DIRT_WET[0] - 14), max(0, C_DIRT_WET[1] - 9),  max(0, C_DIRT_WET[2] - 5))
        shine1   = (min(255, C_DIRT_WET[0] + 44), min(255, C_DIRT_WET[1] + 28), min(255, C_DIRT_WET[2] + 20))
        shine2   = (min(255, C_DIRT_WET[0] + 22), min(255, C_DIRT_WET[1] + 14), min(255, C_DIRT_WET[2] + 10))
        # Moist furrows
        for fy in range(rect.y + 7, rect.bottom - 4, 10):
            pygame.draw.line(surface, furrow_d, (rect.x + 4, fy), (rect.right - 4, fy), 2)
        # Multiple moisture sheen highlights
        pygame.draw.rect(surface, shine1, (rect.x + 4,  rect.y + 4,  T - 8,  3))
        pygame.draw.rect(surface, shine2, (rect.x + 8,  rect.y + 16, T - 18, 2))
        pygame.draw.rect(surface, shine2, (rect.x + 10, rect.y + 32, T - 22, 2))


# ---------------------------------------------------------------------------
# Map Generation
# ---------------------------------------------------------------------------

def generate_map():
    """
    Build and return the initial world layout as two 2D lists:
        tiles[row][col] — base tile IDs
        farm[row][col]  — farm soil states

    The map is 60 columns × 45 rows.
    Layout overview:
        - Upper-left:  farmhouse (impassable building tiles)
        - Left-centre: dirt path leading from house downward
        - Middle:      main horizontal dirt path
        - Right-centre: fenced farm plot with farmable interior
        - Everywhere else: grass with scattered flower tiles and trees
    """
    # Start with all grass
    tiles = [[T_GRASS] * MAP_COLS for _ in range(MAP_ROWS)]
    farm  = [[FS_NONE]  * MAP_COLS for _ in range(MAP_ROWS)]

    # -- 1. Farmhouse footprint ----------------------------------------
    # Fill the house area with T_HOUSE_FLOOR so the player is blocked.
    # The actual visual is drawn by world.py on top of these tiles.
    for row in range(HOUSE_ROW, HOUSE_ROW + HOUSE_ROWS):
        for col in range(HOUSE_COL, HOUSE_COL + HOUSE_COLS):
            tiles[row][col] = T_HOUSE_FLOOR

    # -- 2. Horizontal main path (row 11–12) ---------------------------
    for col in range(1, MAP_COLS - 1):
        tiles[11][col] = T_PATH
        tiles[12][col] = T_PATH

    # -- 3. Vertical path from house door down to main path (col 8–9) --
    for row in range(HOUSE_ROW + HOUSE_ROWS, 12):
        tiles[row][8] = T_PATH
        tiles[row][9] = T_PATH

    # -- 4. Vertical path from main path down to farm gate (col 22–23) -
    for row in range(12, FARM_ROW + 1):
        tiles[row][22] = T_PATH
        tiles[row][23] = T_PATH

    # -- 5. Farm plot fencing ------------------------------------------
    farm_right = FARM_COL + FARM_COLS - 1    # column of right fence
    farm_bot   = FARM_ROW + FARM_ROWS  - 1   # row of bottom fence

    for row in range(FARM_ROW, farm_bot + 1):
        for col in range(FARM_COL, farm_right + 1):

            is_top    = (row == FARM_ROW)
            is_bot    = (row == farm_bot)
            is_left   = (col == FARM_COL)
            is_right  = (col == farm_right)

            if is_top and is_left:
                tiles[row][col] = T_FENCE_TL
            elif is_top and is_right:
                tiles[row][col] = T_FENCE_TR
            elif is_bot and is_left:
                tiles[row][col] = T_FENCE_BL
            elif is_bot and is_right:
                tiles[row][col] = T_FENCE_BR
            elif is_top or is_bot:
                # Gate opening in the top fence at cols 22-23
                if is_top and col in (22, 23):
                    tiles[row][col] = T_FENCE_GATE
                else:
                    tiles[row][col] = T_FENCE_H
            elif is_left or is_right:
                tiles[row][col] = T_FENCE_V
            else:
                # Interior farmable dirt
                tiles[row][col] = T_DIRT
                farm[row][col]  = FS_DRY

    # -- 6. Scatter wildflower grass tiles -----------------------------
    # Use a seeded random so the map looks the same every run
    rng = random.Random(42)
    for row in range(MAP_ROWS):
        for col in range(MAP_COLS):
            if tiles[row][col] == T_GRASS:
                if rng.random() < 0.08:   # 8% chance of flowers
                    tiles[row][col] = T_GRASS_FLOWER

    # -- 7. Small pond (decorative, top-right area) --------------------
    for row in range(3, 8):
        for col in range(48, 56):
            tiles[row][col] = T_WATER

    # -- 8. Market stall (impassable — 2×2 tiles beside the farmhouse) -
    stall_col = HOUSE_COL + HOUSE_COLS + 1
    stall_row = HOUSE_ROW + HOUSE_ROWS - 2
    for r in range(stall_row, stall_row + 2):
        for c in range(stall_col, stall_col + 2):
            tiles[r][c] = T_HOUSE_FLOOR

    return tiles, farm
