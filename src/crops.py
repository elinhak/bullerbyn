"""
crops.py — Potato Crop System
================================
Handles everything about growing potatoes:
  - Planting a seed
  - Tracking growth over in-game days
  - Watering (speeds up growth)
  - Drawing each growth stage
  - Harvesting (removing the plant and returning potatoes)

Growth stages:
  Stage 0 — SEED     (just planted, barely visible in soil)
  Stage 1 — SPROUT   (tiny green shoot breaking the surface)
  Stage 2 — GROWING  (leafy young plant)
  Stage 3 — MATURE   (full-grown, golden-green, ready to harvest!)

Each stage requires a certain number of in-game days to reach.
Watered soil does NOT speed up growth in this version but is required
to plant seeds (soil must be tilled; watering is optional for now — you
can add a "must water daily" mechanic later if you want more challenge).
"""

import pygame
from src.settings import (
    TILE_SIZE,
    POTATO_DAYS_SPROUT, POTATO_DAYS_GROWING, POTATO_DAYS_MATURE,
    C_DIRT_TILLED, C_DIRT_WET,
    C_CROP_SEED, C_CROP_SPROUT, C_CROP_GROWING, C_CROP_MATURE,
    C_GRASS_1,
)

# ---------------------------------------------------------------------------
# Stage constants — easier to read than bare numbers
# ---------------------------------------------------------------------------
STAGE_SEED    = 0
STAGE_SPROUT  = 1
STAGE_GROWING = 2
STAGE_MATURE  = 3


class Crop:
    """
    Represents a single potato plant in one farm cell.

    Attributes:
        col, row   — tile grid position of this crop
        age_days   — how many full in-game days this crop has been alive
        stage      — current growth stage (STAGE_SEED … STAGE_MATURE)
        watered    — was this cell watered today? (resets each new day)
    """

    def __init__(self, col: int, row: int):
        self.col       = col
        self.row       = row
        self.age_days  = 0       # starts at zero days old
        self.stage     = STAGE_SEED
        self.watered   = False   # becomes True when player waters it

    def advance_day(self):
        """
        Called once per in-game day to age the crop and possibly
        advance to the next growth stage.
        """
        self.age_days += 1

        # Check if enough days have passed to advance the stage
        if self.age_days >= POTATO_DAYS_MATURE:
            self.stage = STAGE_MATURE
        elif self.age_days >= POTATO_DAYS_GROWING:
            self.stage = STAGE_GROWING
        elif self.age_days >= POTATO_DAYS_SPROUT:
            self.stage = STAGE_SPROUT
        else:
            self.stage = STAGE_SEED

        # Watering resets each new day
        self.watered = False

    def is_ready(self) -> bool:
        """Return True if this potato is ready to harvest."""
        return self.stage == STAGE_MATURE

    def draw(self, surface: pygame.Surface, screen_x: float, screen_y: float):
        """
        Draw this crop at the given screen position.
        Each stage has a distinct visual so players can easily tell how
        far along their crops are.
        """
        T  = TILE_SIZE
        cx = int(screen_x + T // 2)   # centre x of the tile
        cy = int(screen_y + T // 2)   # centre y of the tile
        bx = int(screen_x)
        by = int(screen_y)

        if self.stage == STAGE_SEED:
            _draw_seed(surface, cx, cy, T)

        elif self.stage == STAGE_SPROUT:
            _draw_sprout(surface, cx, cy, T)

        elif self.stage == STAGE_GROWING:
            _draw_growing(surface, cx, cy, T)

        elif self.stage == STAGE_MATURE:
            _draw_mature(surface, cx, cy, T)


# ---------------------------------------------------------------------------
# Per-stage drawing helpers
# ---------------------------------------------------------------------------

def _draw_seed(surface, cx, cy, T):
    """Stage 0: A small soil mound with a seed peeking out."""
    # Shadow
    pygame.draw.ellipse(surface, (60, 35, 8), (cx - 7, cy + 1, 14, 5))
    # Mound
    pygame.draw.ellipse(surface, (95, 58, 16), (cx - 6, cy - 3, 12, 8))
    pygame.draw.ellipse(surface, (118, 76, 28), (cx - 4, cy - 2, 8, 4))
    # Tiny seed nub at top
    pygame.draw.circle(surface, (145, 100, 40), (cx, cy - 4), 2)


def _draw_sprout(surface, cx, cy, T):
    """Stage 1: A fresh bright-green shoot breaking the soil."""
    stem_col = (55, 145, 38)
    # Shadow beneath
    pygame.draw.ellipse(surface, (60, 40, 10), (cx - 5, cy + 4, 10, 4))
    # Stem
    pygame.draw.line(surface, stem_col, (cx, cy + 6), (cx, cy - 6), 3)
    pygame.draw.line(surface, (88, 185, 60), (cx - 1, cy + 4), (cx - 1, cy - 4), 1)
    # Left leaf
    pygame.draw.ellipse(surface, C_CROP_SPROUT, (cx - 10, cy - 10, 11, 7))
    pygame.draw.ellipse(surface, (118, 200, 90), (cx - 9,  cy - 9,  7, 4))
    # Right leaf
    pygame.draw.ellipse(surface, C_CROP_SPROUT, (cx - 1, cy - 10, 11, 7))
    pygame.draw.ellipse(surface, (118, 200, 90), (cx,     cy - 9,  7, 4))
    # Leaf vein dots
    pygame.draw.circle(surface, (148, 210, 105), (cx - 5, cy - 7), 1)
    pygame.draw.circle(surface, (148, 210, 105), (cx + 4, cy - 7), 1)


def _draw_growing(surface, cx, cy, T):
    """Stage 2: A bushy leafy plant with visible stem and multiple leaf clusters."""
    stem_col  = (50, 118, 32)
    leaf_sh   = (max(0, C_CROP_GROWING[0]-22), max(0, C_CROP_GROWING[1]-18), max(0, C_CROP_GROWING[2]-12))
    leaf_hi   = (min(255, C_CROP_GROWING[0]+28), min(255, C_CROP_GROWING[1]+24), min(255, C_CROP_GROWING[2]+16))

    # Shadow
    pygame.draw.ellipse(surface, (50, 32, 8), (cx - 12, cy + 5, 24, 7))
    # Main stem
    pygame.draw.line(surface, stem_col, (cx, cy + 9), (cx, cy - 10), 3)
    pygame.draw.line(surface, (80, 155, 52), (cx - 1, cy + 6), (cx - 1, cy - 8), 1)

    # Leaf clusters — shadow then lit
    leaves = [
        (cx - 14, cy - 5,  14, 9),
        (cx + 1,  cy - 5,  14, 9),
        (cx - 9,  cy - 16, 18, 10),
        (cx - 13, cy + 2,  11, 7),
        (cx + 2,  cy + 2,  11, 7),
    ]
    for lx, ly, lw, lh in leaves:
        pygame.draw.ellipse(surface, leaf_sh, (lx + 1, ly + 1, lw, lh))
        pygame.draw.ellipse(surface, C_CROP_GROWING, (lx, ly, lw, lh))

    # Highlights on uppermost leaves
    for lx, ly, lw, lh in [(cx - 12, cy - 14, 9, 5), (cx - 6, cy - 4, 7, 4)]:
        pygame.draw.ellipse(surface, leaf_hi, (lx, ly, lw, lh))


def _draw_mature(surface, cx, cy, T):
    """Stage 3: Dense golden-green canopy with harvest flowers on top."""
    stem_col = (55, 112, 32)
    leaf_sh  = (max(0, C_CROP_MATURE[0]-24), max(0, C_CROP_MATURE[1]-20), max(0, C_CROP_MATURE[2]-14))
    leaf_hi  = (min(255, C_CROP_MATURE[0]+30), min(255, C_CROP_MATURE[1]+26), min(255, C_CROP_MATURE[2]+18))

    # Ground shadow
    pygame.draw.ellipse(surface, (48, 30, 8), (cx - 14, cy + 7, 28, 8))
    # Main stem
    pygame.draw.line(surface, stem_col, (cx, cy + 11), (cx, cy - 14), 3)
    pygame.draw.line(surface, (85, 148, 55), (cx - 1, cy + 8), (cx - 1, cy - 11), 1)

    # Dense canopy — shadow then colour then highlight
    canopy = [
        (cx - 17, cy - 6,  16, 11),
        (cx + 1,  cy - 6,  16, 11),
        (cx - 11, cy - 19, 22, 12),
        (cx - 15, cy + 3,  13, 9),
        (cx + 2,  cy + 3,  13, 9),
        (cx - 7,  cy - 12, 14, 10),
    ]
    for lx, ly, lw, lh in canopy:
        pygame.draw.ellipse(surface, leaf_sh,     (lx + 1, ly + 1, lw, lh))
        pygame.draw.ellipse(surface, C_CROP_MATURE,(lx,    ly,     lw, lh))

    # Highlight patches
    for lx, ly, lw, lh in [(cx - 9, cy - 17, 11, 6), (cx - 6, cy - 5, 8, 5)]:
        pygame.draw.ellipse(surface, leaf_hi, (lx, ly, lw, lh))

    # Harvest flowers — white petals + golden centre
    flower_positions = [(cx, cy - 21), (cx - 5, cy - 18), (cx + 5, cy - 19)]
    for fx, fy in flower_positions:
        for pdx, pdy in [(0, -4), (3, -3), (4, 0), (3, 3), (0, 4), (-3, 3), (-4, 0), (-3, -3)]:
            pygame.draw.circle(surface, (255, 242, 205), (fx + pdx, fy + pdy), 2)
        pygame.draw.circle(surface, (255, 215, 50), (fx, fy), 3)
        pygame.draw.circle(surface, (255, 240, 120), (fx - 1, fy - 1), 1)


# ---------------------------------------------------------------------------
# CropManager
# ---------------------------------------------------------------------------

class CropManager:
    """
    Manages all the potato crops currently growing on the farm.

    Internally stores crops in a dictionary keyed by (col, row) tuple,
    so it's fast to check if a specific tile has a crop.

    Usage in world.py:
        crop_mgr = CropManager()
        crop_mgr.plant(col, row)       # plant a new crop
        crop_mgr.new_day()             # advance all crops by one day
        crop_mgr.harvest(col, row)     # remove and return how many potatoes
        crop_mgr.draw(surface, camera) # draw all crops
    """

    def __init__(self):
        # Dictionary: (col, row) → Crop instance
        self._crops = {}

    def has_crop(self, col: int, row: int) -> bool:
        """Return True if there is a crop in this tile."""
        return (col, row) in self._crops

    def get_crop(self, col: int, row: int):
        """Return the Crop object at (col, row), or None if there isn't one."""
        return self._crops.get((col, row))

    def plant(self, col: int, row: int) -> bool:
        """
        Plant a new potato seed at (col, row).
        Returns True if successful, False if there's already a crop there.
        """
        if (col, row) in self._crops:
            return False   # already has a crop — can't plant twice
        self._crops[(col, row)] = Crop(col, row)
        return True

    def harvest(self, col: int, row: int) -> int:
        """
        Harvest the crop at (col, row).
        Returns the number of potatoes yielded (0 if no mature crop).
        Removes the crop from the field.
        """
        crop = self._crops.get((col, row))
        if crop is None:
            return 0
        if not crop.is_ready():
            return 0   # not ready yet — tell the player to wait

        # Remove the harvested crop
        del self._crops[(col, row)]

        # Yield a small random amount — between 2 and 5 potatoes per plant
        # (You could make this depend on watering history for added depth)
        import random
        return random.randint(2, 5)

    def new_day(self):
        """
        Advance all crops by one day.
        Call this once per in-game day from the world/game update code.
        """
        for crop in self._crops.values():
            crop.advance_day()

    def water_crop(self, col: int, row: int):
        """Mark a crop as watered today (visual feedback + future mechanics)."""
        crop = self._crops.get((col, row))
        if crop:
            crop.watered = True

    def draw(self, surface: pygame.Surface, camera):
        """
        Draw all crops that are currently visible on screen.
        """
        for (col, row), crop in self._crops.items():
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE

            # Only draw if this tile is on screen (performance optimisation)
            sx, sy = camera.apply(wx, wy)
            if -TILE_SIZE <= sx <= surface.get_width() + TILE_SIZE and \
               -TILE_SIZE <= sy <= surface.get_height() + TILE_SIZE:
                crop.draw(surface, sx, sy)

    def to_dict(self) -> dict:
        """
        Serialize all crops to a plain dictionary for saving to a JSON file.
        """
        return {
            f"{col},{row}": {"age": c.age_days, "stage": c.stage, "watered": c.watered}
            for (col, row), c in self._crops.items()
        }

    def from_dict(self, data: dict):
        """
        Load crops from a previously saved dictionary.
        """
        self._crops.clear()
        for key, val in data.items():
            col, row = map(int, key.split(","))
            crop = Crop(col, row)
            crop.age_days = val.get("age", 0)
            crop.stage    = val.get("stage", STAGE_SEED)
            crop.watered  = val.get("watered", False)
            self._crops[(col, row)] = crop
