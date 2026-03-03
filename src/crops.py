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
    """Stage 0: A small brown bump in the soil — seed has just been planted."""
    # Tiny mound of dirt
    pygame.draw.ellipse(surface, (90, 55, 15),
                        (cx - 6, cy - 3, 12, 7))
    # Slightly lighter top to give roundness
    pygame.draw.ellipse(surface, (110, 70, 25),
                        (cx - 4, cy - 2, 8, 4))


def _draw_sprout(surface, cx, cy, T):
    """Stage 1: A tiny green shoot peeking out of the soil."""
    # Small stem
    pygame.draw.line(surface, (60, 140, 40),
                     (cx, cy + 6), (cx, cy - 5), 3)
    # Two small leaves at the top
    pygame.draw.ellipse(surface, C_CROP_SPROUT,
                        (cx - 8, cy - 9, 9, 6))    # left leaf
    pygame.draw.ellipse(surface, C_CROP_SPROUT,
                        (cx,     cy - 9, 9, 6))    # right leaf
    # Leaf highlight
    pygame.draw.ellipse(surface, (110, 195, 85),
                        (cx - 6, cy - 8, 5, 3))


def _draw_growing(surface, cx, cy, T):
    """Stage 2: A bushy leafy plant, about half-grown."""
    # Main stem
    pygame.draw.line(surface, (55, 120, 35),
                     (cx, cy + 8), (cx, cy - 8), 3)

    # Several leaf clusters radiating outward
    leaf_positions = [
        (cx - 13, cy - 4,  13, 8),
        (cx,      cy - 4,  13, 8),
        (cx - 8,  cy - 14, 15, 9),
        (cx - 12, cy + 1,  10, 6),
        (cx + 2,  cy + 1,  10, 6),
    ]
    for lx, ly, lw, lh in leaf_positions:
        pygame.draw.ellipse(surface, C_CROP_GROWING, (lx, ly, lw, lh))

    # Lighter green highlights
    pygame.draw.ellipse(surface, (80, 170, 60),
                        (cx - 10, cy - 12, 8, 5))
    pygame.draw.ellipse(surface, (80, 170, 60),
                        (cx - 6,  cy - 3,  7, 4))


def _draw_mature(surface, cx, cy, T):
    """
    Stage 3: Full-grown potato plant — dense foliage with a golden-green tint.
    A small yellow flower indicates it is ready to harvest!
    """
    # Main stem (taller than growing stage)
    pygame.draw.line(surface, (60, 115, 35),
                     (cx, cy + 10), (cx, cy - 12), 3)

    # Dense leaf canopy (darker green with golden highlights)
    canopy = [
        (cx - 16, cy - 5,  15, 10),
        (cx + 1,  cy - 5,  15, 10),
        (cx - 10, cy - 17, 20, 11),
        (cx - 14, cy + 2,  12, 8),
        (cx + 2,  cy + 2,  12, 8),
        (cx - 6,  cy - 10, 12, 9),
    ]
    for lx, ly, lw, lh in canopy:
        pygame.draw.ellipse(surface, C_CROP_MATURE, (lx, ly, lw, lh))

    # Golden-yellow highlights to make it look lush
    pygame.draw.ellipse(surface, (205, 195, 55),
                        (cx - 8, cy - 15, 10, 6))
    pygame.draw.ellipse(surface, (205, 195, 55),
                        (cx - 5, cy - 4,  8, 5))

    # Small white flower at the top — signals "ready to harvest!"
    pygame.draw.circle(surface, (255, 240, 200), (cx,     cy - 19), 4)
    pygame.draw.circle(surface, (255, 210, 50),  (cx,     cy - 19), 2)
    pygame.draw.circle(surface, (255, 240, 200), (cx - 4, cy - 17), 3)
    pygame.draw.circle(surface, (255, 240, 200), (cx + 4, cy - 17), 3)


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
