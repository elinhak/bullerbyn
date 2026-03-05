"""
crops.py — Crop System (Potato, Carrot, Corn, Strawberry)
===========================================================
Handles everything about growing crops:
  - Planting a seed
  - Tracking growth over in-game days
  - Drawing each growth stage
  - Harvesting

Growth stages (all crop types):
  Stage 0 — SEED     (just planted, barely visible in soil)
  Stage 1 — SPROUT   (tiny shoot breaking the surface)
  Stage 2 — GROWING  (young leafy plant)
  Stage 3 — MATURE   (full-grown, ready to harvest!)

Grow time constants live in src/settings.py so they are easy to find and tweak.
Each crop type has its own DAYS_SPROUT / DAYS_GROWING / DAYS_MATURE triple.

Summary of grow times (in in-game days):
  Potato:     sprout 1 / growing 2 / mature 4
  Carrot:     sprout 2 / growing 4 / mature 6
  Corn:       sprout 3 / growing 6 / mature 9
  Strawberry: sprout 3 / growing 7 / mature 12
"""

import pygame
from src.settings import (
    TILE_SIZE,
    CROP_POTATO, CROP_CARROT, CROP_CORN, CROP_STRAWBERRY,
    POTATO_DAYS_SPROUT,  POTATO_DAYS_GROWING,  POTATO_DAYS_MATURE,
    CARROT_DAYS_SPROUT,  CARROT_DAYS_GROWING,  CARROT_DAYS_MATURE,
    CORN_DAYS_SPROUT,    CORN_DAYS_GROWING,    CORN_DAYS_MATURE,
    STRAWBERRY_DAYS_SPROUT, STRAWBERRY_DAYS_GROWING, STRAWBERRY_DAYS_MATURE,
    C_DIRT_TILLED, C_DIRT_WET,
    C_CROP_SEED, C_CROP_SPROUT, C_CROP_GROWING, C_CROP_MATURE,
)

# ---------------------------------------------------------------------------
# Stage constants — easier to read than bare numbers
# ---------------------------------------------------------------------------
STAGE_SEED    = 0
STAGE_SPROUT  = 1
STAGE_GROWING = 2
STAGE_MATURE  = 3

# Grow-time lookup: (sprout_days, growing_days, mature_days) per crop type
_GROW_TIMES = {
    CROP_POTATO:     (POTATO_DAYS_SPROUT,     POTATO_DAYS_GROWING,     POTATO_DAYS_MATURE),
    CROP_CARROT:     (CARROT_DAYS_SPROUT,     CARROT_DAYS_GROWING,     CARROT_DAYS_MATURE),
    CROP_CORN:       (CORN_DAYS_SPROUT,       CORN_DAYS_GROWING,       CORN_DAYS_MATURE),
    CROP_STRAWBERRY: (STRAWBERRY_DAYS_SPROUT, STRAWBERRY_DAYS_GROWING, STRAWBERRY_DAYS_MATURE),
}


class Crop:
    """
    Represents a single crop plant in one farm cell.

    Attributes:
        col, row    — tile grid position
        crop_type   — CROP_POTATO, CROP_CARROT, CROP_CORN, or CROP_STRAWBERRY
        age_days    — how many full in-game days this crop has been alive
        stage       — current growth stage (STAGE_SEED … STAGE_MATURE)
        watered     — was this cell watered today?
    """

    def __init__(self, col: int, row: int, crop_type: int = CROP_POTATO):
        self.col       = col
        self.row       = row
        self.crop_type = crop_type
        self.age_days  = 0
        self.stage     = STAGE_SEED
        self.watered   = False

    def advance_day(self):
        """Age the crop by one in-game day and update its growth stage."""
        self.age_days += 1
        d_sprout, d_growing, d_mature = _GROW_TIMES[self.crop_type]

        if self.age_days >= d_mature:
            self.stage = STAGE_MATURE
        elif self.age_days >= d_growing:
            self.stage = STAGE_GROWING
        elif self.age_days >= d_sprout:
            self.stage = STAGE_SPROUT
        else:
            self.stage = STAGE_SEED

        self.watered = False  # watering resets each new day

    def is_ready(self) -> bool:
        """Return True if this crop is ready to harvest."""
        return self.stage == STAGE_MATURE

    def draw(self, surface: pygame.Surface, screen_x: float, screen_y: float):
        """Draw this crop at the given screen position."""
        T  = TILE_SIZE
        cx = int(screen_x + T // 2)
        cy = int(screen_y + T // 2)

        draw_fn = _DRAW_TABLE.get((self.crop_type, self.stage))
        if draw_fn:
            draw_fn(surface, cx, cy, T)


# ---------------------------------------------------------------------------
# ─── POTATO drawings ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _potato_seed(surface, cx, cy, T):
    """Stage 0: A small soil mound with a seed peeking out."""
    pygame.draw.ellipse(surface, (60, 35, 8),   (cx - 7, cy + 1, 14, 5))
    pygame.draw.ellipse(surface, (95, 58, 16),  (cx - 6, cy - 3, 12, 8))
    pygame.draw.ellipse(surface, (118, 76, 28), (cx - 4, cy - 2, 8, 4))
    pygame.draw.circle(surface,  (145, 100, 40), (cx, cy - 4), 2)


def _potato_sprout(surface, cx, cy, T):
    """Stage 1: A fresh bright-green shoot."""
    stem_col = (55, 145, 38)
    pygame.draw.ellipse(surface, (60, 40, 10),  (cx - 5, cy + 4, 10, 4))
    pygame.draw.line(surface, stem_col,          (cx, cy + 6), (cx, cy - 6), 3)
    pygame.draw.line(surface, (88, 185, 60),     (cx - 1, cy + 4), (cx - 1, cy - 4), 1)
    pygame.draw.ellipse(surface, C_CROP_SPROUT,  (cx - 10, cy - 10, 11, 7))
    pygame.draw.ellipse(surface, (118, 200, 90), (cx - 9,  cy - 9,  7, 4))
    pygame.draw.ellipse(surface, C_CROP_SPROUT,  (cx - 1, cy - 10, 11, 7))
    pygame.draw.ellipse(surface, (118, 200, 90), (cx,     cy - 9,  7, 4))
    pygame.draw.circle(surface, (148, 210, 105), (cx - 5, cy - 7), 1)
    pygame.draw.circle(surface, (148, 210, 105), (cx + 4, cy - 7), 1)


def _potato_growing(surface, cx, cy, T):
    """Stage 2: Bushy leafy plant."""
    stem_col = (50, 118, 32)
    leaf_sh  = (max(0, C_CROP_GROWING[0]-22), max(0, C_CROP_GROWING[1]-18), max(0, C_CROP_GROWING[2]-12))
    leaf_hi  = (min(255, C_CROP_GROWING[0]+28), min(255, C_CROP_GROWING[1]+24), min(255, C_CROP_GROWING[2]+16))
    pygame.draw.ellipse(surface, (50, 32, 8),   (cx - 12, cy + 5, 24, 7))
    pygame.draw.line(surface, stem_col,          (cx, cy + 9), (cx, cy - 10), 3)
    pygame.draw.line(surface, (80, 155, 52),     (cx - 1, cy + 6), (cx - 1, cy - 8), 1)
    leaves = [(cx-14,cy-5,14,9),(cx+1,cy-5,14,9),(cx-9,cy-16,18,10),(cx-13,cy+2,11,7),(cx+2,cy+2,11,7)]
    for lx, ly, lw, lh in leaves:
        pygame.draw.ellipse(surface, leaf_sh,         (lx+1, ly+1, lw, lh))
        pygame.draw.ellipse(surface, C_CROP_GROWING,  (lx,   ly,   lw, lh))
    for lx, ly, lw, lh in [(cx-12,cy-14,9,5),(cx-6,cy-4,7,4)]:
        pygame.draw.ellipse(surface, leaf_hi, (lx, ly, lw, lh))


def _potato_mature(surface, cx, cy, T):
    """Stage 3: Dense golden-green canopy with harvest flowers."""
    stem_col = (55, 112, 32)
    leaf_sh  = (max(0, C_CROP_MATURE[0]-24), max(0, C_CROP_MATURE[1]-20), max(0, C_CROP_MATURE[2]-14))
    leaf_hi  = (min(255, C_CROP_MATURE[0]+30), min(255, C_CROP_MATURE[1]+26), min(255, C_CROP_MATURE[2]+18))
    pygame.draw.ellipse(surface, (48, 30, 8), (cx-14, cy+7, 28, 8))
    pygame.draw.line(surface, stem_col,        (cx, cy+11), (cx, cy-14), 3)
    pygame.draw.line(surface, (85, 148, 55),   (cx-1, cy+8), (cx-1, cy-11), 1)
    canopy = [(cx-17,cy-6,16,11),(cx+1,cy-6,16,11),(cx-11,cy-19,22,12),(cx-15,cy+3,13,9),(cx+2,cy+3,13,9),(cx-7,cy-12,14,10)]
    for lx, ly, lw, lh in canopy:
        pygame.draw.ellipse(surface, leaf_sh,        (lx+1, ly+1, lw, lh))
        pygame.draw.ellipse(surface, C_CROP_MATURE,  (lx,   ly,   lw, lh))
    for lx, ly, lw, lh in [(cx-9,cy-17,11,6),(cx-6,cy-5,8,5)]:
        pygame.draw.ellipse(surface, leaf_hi, (lx, ly, lw, lh))
    for fx, fy in [(cx, cy-21),(cx-5, cy-18),(cx+5, cy-19)]:
        for pdx, pdy in [(0,-4),(3,-3),(4,0),(3,3),(0,4),(-3,3),(-4,0),(-3,-3)]:
            pygame.draw.circle(surface, (255, 242, 205), (fx+pdx, fy+pdy), 2)
        pygame.draw.circle(surface, (255, 215, 50),  (fx, fy), 3)
        pygame.draw.circle(surface, (255, 240, 120), (fx-1, fy-1), 1)


# ---------------------------------------------------------------------------
# ─── CARROT drawings ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _carrot_seed(surface, cx, cy, T):
    """Stage 0: Orange-tinted seed mound in soil."""
    pygame.draw.ellipse(surface, (65, 38, 10),  (cx - 7, cy + 1, 14, 5))
    pygame.draw.ellipse(surface, (105, 62, 18), (cx - 6, cy - 3, 12, 8))
    pygame.draw.ellipse(surface, (130, 82, 32), (cx - 4, cy - 2, 8, 4))
    pygame.draw.circle(surface,  (195, 110, 35), (cx, cy - 4), 2)   # orange seed nub


def _carrot_sprout(surface, cx, cy, T):
    """Stage 1: Thin bright upright carrot shoots."""
    stem = (65, 160, 45)
    pygame.draw.ellipse(surface, (58, 38, 8),  (cx - 5, cy + 4, 10, 4))
    # Three thin upright shoots
    for ox in (-4, 0, 4):
        h = 10 + abs(ox) * 2
        pygame.draw.line(surface, stem,          (cx+ox, cy+5), (cx+ox, cy+5-h), 2)
        pygame.draw.circle(surface, (100,200,65),(cx+ox, cy+5-h), 2)


def _carrot_growing(surface, cx, cy, T):
    """Stage 2: Feathery carrot tops — wispy branching fronds."""
    stem  = (55, 148, 38)
    frond = (80, 185, 55)
    frond_hi = (120, 210, 90)
    pygame.draw.ellipse(surface, (50, 32, 8),  (cx - 10, cy + 6, 20, 6))
    # Central stem
    pygame.draw.line(surface, stem, (cx, cy+8), (cx, cy-12), 3)
    # Feathery fronds branching left and right
    for ox, oy, l in [(-6, -4, 8), (5, -4, 8), (-9, -9, 7), (8, -9, 7), (-5, -13, 6), (4, -13, 6)]:
        end_x = cx + ox + (-3 if ox < 0 else 3)
        end_y = cy + oy - l
        pygame.draw.line(surface, frond,    (cx+ox, cy+oy), (end_x, end_y), 2)
        pygame.draw.line(surface, frond_hi, (cx+ox, cy+oy), (end_x, end_y), 1)


def _carrot_mature(surface, cx, cy, T):
    """Stage 3: Orange carrot visible in soil, lush feathery green tops."""
    stem  = (55, 148, 38)
    frond = (70, 175, 50)
    frond_hi = (115, 210, 80)
    # Ground shadow
    pygame.draw.ellipse(surface, (48, 30, 8), (cx-12, cy+8, 24, 7))
    # Carrot body peeking out of soil — orange root
    pygame.draw.ellipse(surface, (200, 95, 20), (cx-5, cy+2, 11, 9))
    pygame.draw.ellipse(surface, (225, 125, 40), (cx-4, cy+2,  9, 6))
    pygame.draw.ellipse(surface, (245, 155, 65), (cx-3, cy+3,  5, 3))
    # Root tip
    pygame.draw.polygon(surface, (175, 80, 15), [(cx-2, cy+11),(cx+2, cy+11),(cx, cy+15)])
    # Thick central stem
    pygame.draw.line(surface, stem, (cx, cy+5), (cx, cy-14), 3)
    # Dense feathery fronds
    fronds = [(-7,-5,9),( 6,-5,9),(-10,-10,8),(9,-10,8),(-6,-14,7),(5,-14,7),(-3,-18,7),(2,-18,7)]
    for ox, oy, l in fronds:
        end_x = cx + ox + (-4 if ox < 0 else 4)
        end_y = cy + oy - l
        pygame.draw.line(surface, frond,    (cx+ox, cy+oy), (end_x, end_y), 2)
        pygame.draw.line(surface, frond_hi, (cx+ox+1, cy+oy), (end_x+1, end_y), 1)


# ---------------------------------------------------------------------------
# ─── CORN drawings ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _corn_seed(surface, cx, cy, T):
    """Stage 0: Pale beige seed mound."""
    pygame.draw.ellipse(surface, (68, 42, 12),  (cx - 7, cy + 1, 14, 5))
    pygame.draw.ellipse(surface, (105, 72, 28), (cx - 6, cy - 3, 12, 8))
    pygame.draw.ellipse(surface, (135, 98, 50), (cx - 4, cy - 2, 8, 4))
    pygame.draw.circle(surface,  (195, 168, 85), (cx, cy - 4), 2)  # beige-yellow kernel


def _corn_sprout(surface, cx, cy, T):
    """Stage 1: Thick pale-green shoot with single broad leaf."""
    stem = (75, 155, 45)
    leaf = (95, 178, 58)
    pygame.draw.ellipse(surface, (55, 35, 8),  (cx - 5, cy + 4, 10, 4))
    pygame.draw.line(surface, stem, (cx, cy+6), (cx, cy-8), 4)
    # Single broad leaf curving right
    pts = [(cx, cy-4), (cx+12, cy-10), (cx+10, cy-6), (cx, cy)]
    pygame.draw.polygon(surface, leaf, pts)
    pygame.draw.line(surface, (125, 205, 78), (cx, cy-4), (cx+8, cy-9), 1)


def _corn_growing(surface, cx, cy, T):
    """Stage 2: Tall stalk with 2-3 broad arching leaves."""
    stem  = (60, 140, 38)
    leaf  = (78, 168, 52)
    leaf_hi = (115, 200, 78)
    pygame.draw.ellipse(surface, (50, 32, 8), (cx-10, cy+7, 20, 6))
    # Stalk
    pygame.draw.line(surface, stem, (cx, cy+9), (cx, cy-18), 4)
    pygame.draw.line(surface, (100, 175, 62), (cx+1, cy+6), (cx+1, cy-16), 1)
    # Lower-left leaf
    pts_l = [(cx, cy), (cx-16, cy-6), (cx-14, cy-2), (cx, cy+4)]
    pygame.draw.polygon(surface, leaf, pts_l)
    pygame.draw.line(surface, leaf_hi, (cx, cy), (cx-12, cy-5), 1)
    # Mid-right leaf
    pts_r = [(cx, cy-8), (cx+15, cy-15), (cx+13, cy-11), (cx, cy-4)]
    pygame.draw.polygon(surface, leaf, pts_r)
    pygame.draw.line(surface, leaf_hi, (cx, cy-8), (cx+11, cy-14), 1)
    # Upper-left leaf
    pts_ul = [(cx, cy-14), (cx-13, cy-19), (cx-11, cy-16), (cx, cy-10)]
    pygame.draw.polygon(surface, leaf, pts_ul)


def _corn_mature(surface, cx, cy, T):
    """Stage 3: Tall stalk with golden corn cob and tassels at top."""
    stem    = (60, 140, 38)
    leaf    = (70, 158, 48)
    leaf_hi = (108, 192, 72)
    cob_col = (235, 195, 45)
    cob_sh  = (190, 150, 25)
    cob_hi  = (252, 220, 90)
    silk    = (240, 210, 120)

    pygame.draw.ellipse(surface, (48, 30, 8), (cx-12, cy+8, 24, 7))
    # Stalk
    pygame.draw.line(surface, stem, (cx, cy+10), (cx, cy-20), 5)
    pygame.draw.line(surface, (95, 170, 58), (cx+1, cy+7), (cx+1, cy-18), 1)
    # Arching leaves
    for pts in [
        [(cx, cy+2), (cx-17, cy-5), (cx-15, cy-1), (cx, cy+6)],
        [(cx, cy-6), (cx+17, cy-13), (cx+15, cy-9), (cx, cy-2)],
        [(cx, cy-13),(cx-15, cy-19),(cx-13, cy-15),(cx, cy-9)],
    ]:
        pygame.draw.polygon(surface, leaf, pts)
    # Corn cob (elongated rounded rectangle with kernel grid)
    cob_x, cob_y, cob_w, cob_h = cx + 6, cy - 10, 10, 16
    pygame.draw.rect(surface, cob_sh,  (cob_x+1, cob_y+1, cob_w, cob_h), border_radius=4)
    pygame.draw.rect(surface, cob_col, (cob_x,   cob_y,   cob_w, cob_h), border_radius=4)
    pygame.draw.rect(surface, cob_hi,  (cob_x+1, cob_y+1, cob_w-4, 5),  border_radius=3)
    # Kernel rows
    for ky in range(cob_y+3, cob_y+cob_h-2, 4):
        pygame.draw.line(surface, cob_sh, (cob_x+1, ky), (cob_x+cob_w-2, ky), 1)
    # Husk leaves around cob
    pygame.draw.polygon(surface, (90, 170, 55),
                        [(cx+5, cy-9), (cx+3, cy+8), (cx+7, cy+6)])
    # Tassel / silk strands at top
    for tx in range(cx-3, cx+4, 2):
        pygame.draw.line(surface, silk, (tx, cy-20), (tx+1, cy-27), 1)


# ---------------------------------------------------------------------------
# ─── STRAWBERRY drawings ────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _strawberry_seed(surface, cx, cy, T):
    """Stage 0: Tiny seed mound, slightly reddish tint."""
    pygame.draw.ellipse(surface, (62, 36, 10),  (cx - 6, cy + 1, 12, 5))
    pygame.draw.ellipse(surface, (98, 60, 18),  (cx - 5, cy - 3, 10, 7))
    pygame.draw.ellipse(surface, (125, 82, 30), (cx - 3, cy - 2, 7, 4))
    pygame.draw.circle(surface,  (175, 55, 55),  (cx, cy - 4), 2)   # tiny red seed


def _strawberry_sprout(surface, cx, cy, T):
    """Stage 1: Two small rounded heart-shaped leaves on short stems."""
    stem = (68, 148, 42)
    leaf = (90, 175, 58)
    pygame.draw.ellipse(surface, (55, 35, 8), (cx - 5, cy + 4, 10, 4))
    # Left stem + leaf
    pygame.draw.line(surface, stem, (cx-2, cy+5), (cx-5, cy-4), 2)
    pygame.draw.ellipse(surface, leaf, (cx-12, cy-8, 10, 8))
    # Right stem + leaf
    pygame.draw.line(surface, stem, (cx+2, cy+5), (cx+5, cy-4), 2)
    pygame.draw.ellipse(surface, leaf, (cx+2, cy-8, 10, 8))
    # Leaf highlights
    pygame.draw.ellipse(surface, (130, 210, 90), (cx-11, cy-7, 5, 3))
    pygame.draw.ellipse(surface, (130, 210, 90), (cx+3,  cy-7, 5, 3))


def _strawberry_growing(surface, cx, cy, T):
    """Stage 2: Low spreading plant with several rounded leaves, runners."""
    stem  = (62, 140, 38)
    leaf  = (78, 168, 52)
    leaf_hi = (118, 205, 80)
    pygame.draw.ellipse(surface, (50, 32, 8), (cx-12, cy+6, 24, 6))
    # Central stems
    for ox, oy in [(-5,-10),( 5,-10),(-8,-5),(8,-5),(0,-13)]:
        pygame.draw.line(surface, stem, (cx, cy+4), (cx+ox, cy+oy), 2)
    # Leaf clusters (rounded trifoil leaves)
    for lx, ly, lw, lh in [
        (cx-16, cy-14, 12, 9), (cx+4, cy-14, 12, 9),
        (cx-14, cy-8,  11, 8), (cx+3, cy-8,  11, 8),
        (cx-6,  cy-18, 12, 9),
    ]:
        pygame.draw.ellipse(surface, leaf,    (lx,   ly,   lw,   lh))
        pygame.draw.ellipse(surface, leaf_hi, (lx+1, ly+1, lw-4, lh//2))


def _strawberry_mature(surface, cx, cy, T):
    """Stage 3: Rich green leaves with bright red strawberries hanging below."""
    stem    = (62, 140, 38)
    leaf    = (72, 162, 50)
    leaf_hi = (112, 200, 76)
    berry   = (215, 40, 40)
    berry_hi = (255, 110, 110)
    seed_dot = (255, 230, 180)
    cap_col  = (55, 140, 35)

    pygame.draw.ellipse(surface, (48, 30, 8), (cx-14, cy+8, 28, 7))
    # Leaf mass
    for ox, oy in [(-5,-11),(5,-11),(-8,-5),(8,-5),(0,-14),(-3,-7),(3,-7)]:
        pygame.draw.line(surface, stem, (cx, cy+3), (cx+ox, cy+oy), 2)
    for lx, ly, lw, lh in [
        (cx-17, cy-15, 13, 10), (cx+4,  cy-15, 13, 10),
        (cx-15, cy-9,  12, 9),  (cx+3,  cy-9,  12, 9),
        (cx-7,  cy-19, 14, 10),
    ]:
        pygame.draw.ellipse(surface, leaf,    (lx,   ly,   lw,   lh))
        pygame.draw.ellipse(surface, leaf_hi, (lx+1, ly+1, lw-4, lh//2))

    # Strawberries hanging below the leaves
    berry_positions = [(cx-8, cy+3, 8), (cx+2, cy+1, 9), (cx-2, cy+6, 7)]
    for bx, by, br in berry_positions:
        # Green cap
        pygame.draw.ellipse(surface, cap_col, (bx-br//2-1, by-2, br+2, 5))
        # Berry body (heart-ish shape via two circles + triangle)
        pygame.draw.circle(surface, berry, (bx-br//3, by+2), br//2+1)
        pygame.draw.circle(surface, berry, (bx+br//3, by+2), br//2+1)
        pygame.draw.polygon(surface, berry,
                            [(bx-br//2, by+3), (bx+br//2, by+3), (bx, by+br+1)])
        # Highlight + seed dots
        pygame.draw.circle(surface, berry_hi, (bx-2, by+1), 2)
        for sdx, sdy in [(-2, 4), (1, 5), (3, 3)]:
            pygame.draw.circle(surface, seed_dot, (bx+sdx, by+sdy), 1)


# ---------------------------------------------------------------------------
# Dispatch table: (crop_type, stage) → draw function
# ---------------------------------------------------------------------------
_DRAW_TABLE = {
    (CROP_POTATO,     STAGE_SEED):    _potato_seed,
    (CROP_POTATO,     STAGE_SPROUT):  _potato_sprout,
    (CROP_POTATO,     STAGE_GROWING): _potato_growing,
    (CROP_POTATO,     STAGE_MATURE):  _potato_mature,
    (CROP_CARROT,     STAGE_SEED):    _carrot_seed,
    (CROP_CARROT,     STAGE_SPROUT):  _carrot_sprout,
    (CROP_CARROT,     STAGE_GROWING): _carrot_growing,
    (CROP_CARROT,     STAGE_MATURE):  _carrot_mature,
    (CROP_CORN,       STAGE_SEED):    _corn_seed,
    (CROP_CORN,       STAGE_SPROUT):  _corn_sprout,
    (CROP_CORN,       STAGE_GROWING): _corn_growing,
    (CROP_CORN,       STAGE_MATURE):  _corn_mature,
    (CROP_STRAWBERRY, STAGE_SEED):    _strawberry_seed,
    (CROP_STRAWBERRY, STAGE_SPROUT):  _strawberry_sprout,
    (CROP_STRAWBERRY, STAGE_GROWING): _strawberry_growing,
    (CROP_STRAWBERRY, STAGE_MATURE):  _strawberry_mature,
}


# ---------------------------------------------------------------------------
# CropManager
# ---------------------------------------------------------------------------

class CropManager:
    """
    Manages all crops currently growing on the farm.
    Stores crops in a dict keyed by (col, row) tuple.
    """

    def __init__(self):
        self._crops = {}

    def has_crop(self, col: int, row: int) -> bool:
        return (col, row) in self._crops

    def get_crop(self, col: int, row: int):
        return self._crops.get((col, row))

    def plant(self, col: int, row: int, crop_type: int = CROP_POTATO) -> bool:
        """
        Plant a new seed of the given crop type at (col, row).
        Returns True if successful, False if already occupied.
        """
        if (col, row) in self._crops:
            return False
        self._crops[(col, row)] = Crop(col, row, crop_type)
        return True

    def harvest(self, col: int, row: int):
        """
        Harvest the crop at (col, row).
        Returns (qty, crop_type) where qty > 0 only if mature.
        Returns (0, None) if no mature crop.
        """
        import random
        crop = self._crops.get((col, row))
        if crop is None or not crop.is_ready():
            return 0, None
        crop_type = crop.crop_type
        del self._crops[(col, row)]
        return random.randint(2, 5), crop_type

    def new_day(self):
        """Advance all crops by one in-game day."""
        for crop in self._crops.values():
            crop.advance_day()

    def water_crop(self, col: int, row: int):
        crop = self._crops.get((col, row))
        if crop:
            crop.watered = True

    def draw(self, surface: pygame.Surface, camera):
        for (col, row), crop in self._crops.items():
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE
            sx, sy = camera.apply(wx, wy)
            if (-TILE_SIZE <= sx <= surface.get_width()  + TILE_SIZE and
                -TILE_SIZE <= sy <= surface.get_height() + TILE_SIZE):
                crop.draw(surface, sx, sy)

    def to_dict(self) -> dict:
        return {
            f"{col},{row}": {
                "age":    c.age_days,
                "stage":  c.stage,
                "watered": c.watered,
                "type":   c.crop_type,
            }
            for (col, row), c in self._crops.items()
        }

    def from_dict(self, data: dict):
        self._crops.clear()
        for key, val in data.items():
            col, row = map(int, key.split(","))
            ctype = val.get("type", CROP_POTATO)
            crop  = Crop(col, row, ctype)
            crop.age_days = val.get("age",   0)
            crop.stage    = val.get("stage", STAGE_SEED)
            crop.watered  = val.get("watered", False)
            self._crops[(col, row)] = crop
