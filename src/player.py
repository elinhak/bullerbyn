"""
player.py — The Player Character
==================================
Handles everything the player can do:
  - Moving around the world (WASD or arrow keys)
  - Collision with solid tiles so the player can't walk through walls/fences
  - Selecting a tool from the hotbar (keys 1–4)
  - Using the selected tool on the tile in front of the player (SPACE or E)

The player is drawn as a simple pixel-art character:
  - A round head with a wide-brimmed hat (1920s Swedish farm worker look)
  - A coloured body
  - Legs that animate while moving

Facing direction is tracked so the character appears to look the right way.
"""

import pygame
import dataclasses
import random as _random
from src.settings import (
    TILE_SIZE, PLAYER_SPEED, PLAYER_SIZE,
    PLAYER_START_COL, PLAYER_START_ROW,
    TOOL_HAND, TOOL_HOE, TOOL_WATER, TOOL_SEEDS,
    STARTING_GOLD, STARTING_SEEDS,
    C_HOUSE_TRIM, C_TREE_TRUNK, C_GRASS_1,
)
from src.tilemap import TileMap, FS_DRY, FS_TILLED, FS_WATERED, FS_NONE

# Direction constants (used for animation frame selection)
DIR_DOWN  = 0
DIR_LEFT  = 1
DIR_RIGHT = 2
DIR_UP    = 3

# Player body colours — Swedish farm-worker palette
COL_SKIN    = (220, 170, 125)   # warm skin tone
COL_HAT     = (80,  55,  30)    # dark brown hat
COL_SHIRT   = (90, 120, 160)    # muted blue linen shirt
COL_PANTS   = (55,  50,  40)    # dark work trousers
COL_SHOES   = (60,  40,  20)    # brown leather shoes
COL_HAIR    = (110,  70,  30)   # brown hair

# -----------------------------------------------------------------------
# Character customisation palettes
# -----------------------------------------------------------------------

SHIRT_COLORS = [
    (90,  120, 160),   # default blue linen
    (160,  90,  90),   # red
    (90,  145,  90),   # green
    (160, 140,  70),   # wheat
    (120,  80, 160),   # purple
    (160, 120,  70),   # tan
    (60,   60,  60),   # charcoal
    (200, 180, 140),   # cream
]

PANTS_COLORS = [
    (55,   50,  40),   # default dark work trousers
    (80,   90, 115),   # navy
    (110,  70,  40),   # brown
    (70,   95,  70),   # forest green
    (130, 110,  90),   # sand
    (40,   40,  40),   # black
    (170, 140, 110),   # beige
    (100,  60,  60),   # burgundy
]

_RANDOM_NAMES = ["Elsa", "Lars", "Sigrid", "Nils", "Britta", "Olle", "Maja", "Knut"]


@dataclasses.dataclass
class CharacterConfig:
    name:        str   = "Elsa"
    shirt_color: tuple = dataclasses.field(default_factory=lambda: SHIRT_COLORS[0])
    pants_color: tuple = dataclasses.field(default_factory=lambda: PANTS_COLORS[0])
    sex:         str   = "female"   # "male" or "female"
    has_hat:     bool  = True

    def randomize(self):
        self.name        = _random.choice(_RANDOM_NAMES)
        self.shirt_color = _random.choice(SHIRT_COLORS)
        self.pants_color = _random.choice(PANTS_COLORS)
        self.sex         = _random.choice(["male", "female"])
        self.has_hat     = _random.choice([True, False])

    def to_dict(self):
        return {
            "name":        self.name,
            "shirt_color": list(self.shirt_color),
            "pants_color": list(self.pants_color),
            "sex":         self.sex,
            "has_hat":     self.has_hat,
        }

    @staticmethod
    def from_dict(d):
        return CharacterConfig(
            name        = d.get("name", "Elsa"),
            shirt_color = tuple(d.get("shirt_color", SHIRT_COLORS[0])),
            pants_color = tuple(d.get("pants_color", PANTS_COLORS[0])),
            sex         = d.get("sex", "female"),
            has_hat     = d.get("has_hat", True),
        )


class Player:
    """
    The player character.

    Key attributes:
        x, y       — world position in pixels (top-left of collision box)
        rect       — pygame.Rect for collision detection
        direction  — which way the player is facing (DIR_DOWN etc.)
        tool       — currently selected tool (TOOL_HAND etc.)
        seeds      — number of potato seeds in inventory
        gold       — total gold coins earned
        potatoes   — harvested potatoes not yet sold
    """

    def __init__(self, char_config=None):
        self.char_config = char_config if char_config is not None else CharacterConfig()

        # Start position (centre of the starting tile, adjusted for player size)
        start_x = PLAYER_START_COL * TILE_SIZE + (TILE_SIZE - PLAYER_SIZE) // 2
        start_y = PLAYER_START_ROW * TILE_SIZE + (TILE_SIZE - PLAYER_SIZE) // 2

        self.x = float(start_x)
        self.y = float(start_y)

        # Collision rectangle — used for checking solid tiles
        self.rect = pygame.Rect(int(self.x), int(self.y), PLAYER_SIZE, PLAYER_SIZE)

        # Facing direction (for drawing and interaction)
        self.direction = DIR_DOWN

        # Currently equipped tool
        self.tool = TOOL_HAND

        # Inventory
        self.seeds    = STARTING_SEEDS
        self.gold     = STARTING_GOLD
        self.potatoes = 0

        # Animation state
        self._walk_timer  = 0.0    # accumulates time for leg-swing animation
        self._is_moving   = False  # True when the player is walking
        self._anim_frame  = 0      # 0 or 1 — leg position frame

        # Interaction cooldown (so one key-press doesn't trigger 60 times)
        self._action_cooldown = 0.0

    # ------------------------------------------------------------------
    # Update — called every frame
    # ------------------------------------------------------------------

    def update(self, dt: float, tilemap: TileMap, crop_mgr, notifications):
        """
        dt          — seconds since the last frame
        tilemap     — the world grid (for collision and soil queries)
        crop_mgr    — the CropManager (for planting/harvesting)
        notifications — list to append message strings to (for UI display)
        """
        self._handle_movement(dt, tilemap)
        self._handle_tool_selection()

        # Reduce cooldown timer
        if self._action_cooldown > 0:
            self._action_cooldown -= dt

        # Use tool when SPACE or E is pressed (but only once per press)
        keys = pygame.key.get_pressed()
        if self._action_cooldown <= 0 and (keys[pygame.K_SPACE] or keys[pygame.K_e]):
            self._use_tool(tilemap, crop_mgr, notifications)
            self._action_cooldown = 0.3   # 300 ms before next action

        # Keep rect in sync with position
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    # ------------------------------------------------------------------
    # Movement with tile collision
    # ------------------------------------------------------------------

    def _handle_movement(self, dt: float, tilemap: TileMap):
        """
        Read arrow/WASD keys and move the player.
        Uses axis-separated collision so the player slides along walls
        rather than getting stuck in corners.
        """
        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            dx = -1.0
            self.direction = DIR_LEFT
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx =  1.0
            self.direction = DIR_RIGHT
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            dy = -1.0
            self.direction = DIR_UP
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            dy =  1.0
            self.direction = DIR_DOWN

        # Normalise diagonal movement so diagonal speed = straight speed
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        speed = PLAYER_SPEED * dt

        # --- Horizontal movement ---
        if dx != 0:
            new_x = self.x + dx * speed
            test_rect = pygame.Rect(int(new_x), int(self.y), PLAYER_SIZE, PLAYER_SIZE)
            if not self._collides(test_rect, tilemap):
                self.x = new_x

        # --- Vertical movement ---
        if dy != 0:
            new_y = self.y + dy * speed
            test_rect = pygame.Rect(int(self.x), int(new_y), PLAYER_SIZE, PLAYER_SIZE)
            if not self._collides(test_rect, tilemap):
                self.y = new_y

        # Clamp to world bounds (can't walk off the edge of the map)
        from src.settings import WORLD_WIDTH, WORLD_HEIGHT
        self.x = max(0, min(self.x, WORLD_WIDTH  - PLAYER_SIZE))
        self.y = max(0, min(self.y, WORLD_HEIGHT - PLAYER_SIZE))

        # Update animation
        self._is_moving = (dx != 0 or dy != 0)
        if self._is_moving:
            self._walk_timer += dt
            if self._walk_timer >= 0.18:   # swap legs every 180 ms
                self._walk_timer = 0.0
                self._anim_frame = 1 - self._anim_frame   # toggle 0/1
        else:
            self._walk_timer = 0.0
            self._anim_frame = 0

    def _collides(self, test_rect: pygame.Rect, tilemap: TileMap) -> bool:
        """
        Check whether test_rect would overlap any solid tile.

        We test all four corners of the player's collision box
        (plus a tiny inset so the player can pass through narrow gaps).
        """
        inset = 2   # pixel inset so corners don't catch on single-tile gaps
        corners = [
            (test_rect.left  + inset, test_rect.top    + inset),
            (test_rect.right - inset, test_rect.top    + inset),
            (test_rect.left  + inset, test_rect.bottom - inset),
            (test_rect.right - inset, test_rect.bottom - inset),
        ]
        for px, py in corners:
            col = int(px // TILE_SIZE)
            row = int(py // TILE_SIZE)
            if tilemap.is_solid(col, row):
                return True
        return False

    # ------------------------------------------------------------------
    # Tool selection
    # ------------------------------------------------------------------

    def _handle_tool_selection(self):
        """Switch tool when the player presses 1, 2, 3, or 4."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]:
            self.tool = TOOL_HAND
        elif keys[pygame.K_2]:
            self.tool = TOOL_HOE
        elif keys[pygame.K_3]:
            self.tool = TOOL_WATER
        elif keys[pygame.K_4]:
            self.tool = TOOL_SEEDS

    # ------------------------------------------------------------------
    # Tool use (SPACE / E)
    # ------------------------------------------------------------------

    def _use_tool(self, tilemap: TileMap, crop_mgr, notifications: list):
        """
        Apply the currently held tool to the tile the player is facing.

        The "target tile" is the tile immediately in front of the player
        in the direction they are facing.
        """
        # Find the tile the player is standing in
        cx = int((self.x + PLAYER_SIZE / 2) // TILE_SIZE)
        cy = int((self.y + PLAYER_SIZE / 2) // TILE_SIZE)

        # The target tile is one step in the facing direction
        offsets = {
            DIR_DOWN:  (0, 1),
            DIR_UP:    (0, -1),
            DIR_LEFT:  (-1, 0),
            DIR_RIGHT: (1, 0),
        }
        dc, dr = offsets[self.direction]
        target_col = cx + dc
        target_row = cy + dr

        farm_state = tilemap.get_farm_state(target_col, target_row)
        has_crop   = crop_mgr.has_crop(target_col, target_row)

        # --- HAND: harvest mature crops ---
        if self.tool == TOOL_HAND:
            if has_crop:
                crop = crop_mgr.get_crop(target_col, target_row)
                if crop.is_ready():
                    qty = crop_mgr.harvest(target_col, target_row)
                    if qty > 0:
                        self.potatoes += qty
                        tilemap.set_farm_state(target_col, target_row, FS_TILLED)
                        notifications.append(f"Harvested {qty} potatoes!")
                else:
                    days_left = max(0, 6 - crop.age_days)
                    notifications.append(f"Not ready yet — {days_left} day(s) to go.")
            else:
                notifications.append("Nothing to pick up here.")

        # --- HOE: till dry soil ---
        elif self.tool == TOOL_HOE:
            if farm_state == FS_DRY:
                tilemap.set_farm_state(target_col, target_row, FS_TILLED)
                notifications.append("Soil tilled!")
            elif farm_state == FS_TILLED or farm_state == FS_WATERED:
                notifications.append("Already tilled.")
            elif farm_state == FS_NONE:
                notifications.append("Can't till here — use the farm plot.")
            else:
                notifications.append("Nothing to till here.")

        # --- WATERING CAN: water tilled soil ---
        elif self.tool == TOOL_WATER:
            if farm_state == FS_TILLED:
                tilemap.set_farm_state(target_col, target_row, FS_WATERED)
                if has_crop:
                    crop_mgr.water_crop(target_col, target_row)
                notifications.append("Watered!")
            elif farm_state == FS_WATERED:
                notifications.append("Already watered today.")
            elif farm_state == FS_DRY:
                notifications.append("Till the soil first (press 2 to select Hoe).")
            else:
                notifications.append("No tilled soil here.")

        # --- SEEDS: plant on tilled (or watered) soil ---
        elif self.tool == TOOL_SEEDS:
            if self.seeds <= 0:
                notifications.append("You have no seeds left!")
            elif has_crop:
                notifications.append("There is already something growing here.")
            elif farm_state in (FS_TILLED, FS_WATERED):
                if crop_mgr.plant(target_col, target_row):
                    self.seeds -= 1
                    notifications.append(f"Planted a potato seed! ({self.seeds} seeds left)")
            elif farm_state == FS_DRY:
                notifications.append("Till the soil first (press 2 to select Hoe).")
            else:
                notifications.append("Can only plant on tilled soil inside the farm.")

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera):
        """
        Draw the player at their current world position, converted to screen
        coordinates using the camera.
        """
        sx, sy = camera.apply(self.x, self.y)
        self._draw_character(surface, int(sx), int(sy), self.direction,
                             self._anim_frame, self._is_moving)

    def _draw_character(self, surface, sx, sy, direction, frame, moving):
        """
        Draw a detailed top-down pixel-art character (32×32 px collision box).
        Rendered with layered shading: shadow → legs → body → arms → head → hat.
        Uses self.char_config for shirt/pants colours, hat visibility, and sex.
        """
        _draw_character_gfx(surface, sx, sy, direction, frame, self.char_config)


# ---------------------------------------------------------------------------
# Standalone character drawing helpers (used by both Player and the creation screen)
# ---------------------------------------------------------------------------

def _draw_character_gfx(surface, sx, sy, direction, frame, config):
    """
    Draw the character sprite using the given CharacterConfig.
    sx, sy — top-left pixel of the 32×32 character tile on `surface`.
    direction — one of DIR_DOWN / DIR_LEFT / DIR_RIGHT / DIR_UP.
    frame — 0 or 1 animation frame.
    config — CharacterConfig instance (colours, hat, sex).
    """
    COL_SHIRT = config.shirt_color
    COL_PANTS = config.pants_color

    T  = PLAYER_SIZE   # 32
    cx = sx + T // 2
    cy = sy + T // 2   # noqa: F841  (kept for clarity)

    # -- Drop shadow (moved down to sit below extended legs) --
    sh = pygame.Surface((T - 4, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 65), sh.get_rect())
    surface.blit(sh, (sx + 2, sy + T - 4))

    # -- Legs / shoes --
    shoe_dark = (max(0, COL_SHOES[0] - 18), max(0, COL_SHOES[1] - 12), max(0, COL_SHOES[2] - 8))
    pant_dark = (max(0, COL_PANTS[0] - 12), max(0, COL_PANTS[1] - 10), max(0, COL_PANTS[2] - 8))

    if direction in (DIR_DOWN, DIR_UP):
        lo = 2 if frame == 0 else -2
        for lx in (cx - 9, cx + 1):
            pygame.draw.rect(surface, pant_dark, (lx - 1, sy + 18 + abs(lo), 9, 12))
            pygame.draw.rect(surface, COL_PANTS, (lx,     sy + 18,            8, 11))
        # Shoes — slid down to sit below the longer pants
        pygame.draw.rect(surface, shoe_dark, (cx - 11, sy + 27, 10, 6))
        pygame.draw.rect(surface, COL_SHOES, (cx - 10, sy + 27,  9, 5))
        pygame.draw.rect(surface, shoe_dark, (cx + 1,  sy + 27, 10, 6))
        pygame.draw.rect(surface, COL_SHOES, (cx + 1,  sy + 27,  9, 5))
        pygame.draw.line(surface,
                         (min(255, COL_SHOES[0]+25), min(255, COL_SHOES[1]+18), min(255, COL_SHOES[2]+12)),
                         (cx - 9, sy + 27), (cx - 3, sy + 27), 1)
    else:
        lo = 6 if frame == 0 else -6
        for lx, ly in [(cx - 8, sy + 17 - lo), (cx + 1, sy + 17 + lo)]:
            pygame.draw.rect(surface, pant_dark, (lx - 1, ly,      8, 13))
            pygame.draw.rect(surface, COL_PANTS, (lx,     ly,      7, 12))
            pygame.draw.rect(surface, shoe_dark, (lx - 1, ly + 10, 9, 5))
            pygame.draw.rect(surface, COL_SHOES, (lx,     ly + 10, 8, 4))

    # -- Body (shirt) — shortened so legs are visible below --
    shirt_hi = (min(255, COL_SHIRT[0]+22), min(255, COL_SHIRT[1]+20), min(255, COL_SHIRT[2]+18))
    shirt_sh = (max(0,   COL_SHIRT[0]-18), max(0,   COL_SHIRT[1]-16), max(0,   COL_SHIRT[2]-14))
    pygame.draw.ellipse(surface, shirt_sh,  (sx + 5, sy + 10, T - 10, 13))
    pygame.draw.ellipse(surface, COL_SHIRT, (sx + 6, sy + 10, T - 12, 12))
    pygame.draw.ellipse(surface, shirt_hi,  (sx + 8, sy + 11, T - 18, 5))
    pygame.draw.arc(surface,
                    (min(255, COL_SHIRT[0]+40), min(255, COL_SHIRT[1]+38), min(255, COL_SHIRT[2]+36)),
                    (cx - 5, sy + 9, 10, 6), 0, 3.14159, 2)

    # -- Arms --
    arm_w, arm_h = 5, 10
    skin_hi = (min(255, COL_SKIN[0]+22), min(255, COL_SKIN[1]+16), min(255, COL_SKIN[2]+10))
    if direction == DIR_LEFT:
        pygame.draw.rect(surface, shirt_sh,  (sx - 1,         sy + 12, arm_w + 1, arm_h))
        pygame.draw.rect(surface, COL_SHIRT, (sx,             sy + 12, arm_w,     arm_h))
        pygame.draw.rect(surface, COL_SKIN,  (sx - 1,         sy + 20, arm_w + 1, 6))
        pygame.draw.circle(surface, skin_hi, (sx + 1,         sy + 25), 2)
    elif direction == DIR_RIGHT:
        pygame.draw.rect(surface, shirt_sh,  (sx + T - arm_w, sy + 12, arm_w + 1, arm_h))
        pygame.draw.rect(surface, COL_SHIRT, (sx + T - arm_w, sy + 12, arm_w,     arm_h))
        pygame.draw.rect(surface, COL_SKIN,  (sx + T - arm_w, sy + 20, arm_w + 1, 6))
        pygame.draw.circle(surface, skin_hi, (sx + T - arm_w + 2, sy + 25), 2)
    else:
        for ax in (sx + 2, sx + T - arm_w - 2):
            pygame.draw.rect(surface, shirt_sh,  (ax - 1, sy + 13, arm_w + 1, 9))
            pygame.draw.rect(surface, COL_SHIRT, (ax,     sy + 13, arm_w,     9))

    # -- Head --
    head_r  = 9
    head_sh = (max(0, COL_SKIN[0]-18), max(0, COL_SKIN[1]-14), max(0, COL_SKIN[2]-10))
    pygame.draw.circle(surface, head_sh, (cx + 1, sy + 10), head_r)
    pygame.draw.circle(surface, COL_SKIN, (cx,    sy + 9),  head_r)
    pygame.draw.circle(surface, skin_hi,  (cx - 3, sy + 5), 3)

    # -- Hair (sex-dependent) --
    is_female = (config.sex == "female")
    hair_dark = (max(0, COL_HAIR[0]-15), max(0, COL_HAIR[1]-12), max(0, COL_HAIR[2]-10))

    if is_female:
        # Bun at the back / braids visible when facing down or sides
        if direction == DIR_DOWN:
            # wide hair arc + side braids
            pygame.draw.arc(surface, COL_HAIR,
                            (cx - head_r - 1, sy - 1, (head_r + 1) * 2, head_r * 2), 0, 3.14159, 5)
            pygame.draw.circle(surface, COL_HAIR,  (cx - head_r + 1, sy + 10), 4)   # left braid bob
            pygame.draw.circle(surface, COL_HAIR,  (cx + head_r - 1, sy + 10), 4)   # right braid bob
            pygame.draw.circle(surface, hair_dark, (cx - head_r + 2, sy + 11), 3)
            pygame.draw.circle(surface, hair_dark, (cx + head_r - 2, sy + 11), 3)
        elif direction == DIR_UP:
            # Bun on top, all hair visible from behind
            pygame.draw.circle(surface, COL_HAIR, (cx, sy + 9), head_r)
            pygame.draw.circle(surface, hair_dark, (cx + 1, sy + 10), head_r)
            pygame.draw.circle(surface, COL_HAIR,  (cx, sy + 3), 5)  # bun
        else:
            pygame.draw.arc(surface, COL_HAIR,
                            (cx - head_r + 2, sy, head_r * 2 - 4, head_r * 2), 0, 3.14159, 3)
            # Side braid bob
            bob_x = (cx - head_r) if direction == DIR_LEFT else (cx + head_r)
            pygame.draw.circle(surface, COL_HAIR,  (bob_x, sy + 12), 4)
            pygame.draw.circle(surface, hair_dark, (bob_x, sy + 13), 3)
    else:
        # Short male hair
        if direction == DIR_DOWN:
            pygame.draw.arc(surface, COL_HAIR,
                            (cx - head_r, sy, head_r * 2, head_r * 2), 0, 3.14159, 4)
        elif direction == DIR_UP:
            pygame.draw.circle(surface, COL_HAIR, (cx, sy + 9), head_r)
            pygame.draw.circle(surface, hair_dark, (cx + 1, sy + 10), head_r)
        else:
            pygame.draw.arc(surface, COL_HAIR,
                            (cx - head_r + 2, sy, head_r * 2 - 4, head_r * 2), 0, 3.14159, 3)

    # -- Hat (optional) — black top hat with red band --
    if config.has_hat:
        hat_blk = (18, 16, 14)        # near-black body
        hat_hi  = (58, 52, 46)        # subtle left/top edge highlight
        hat_sh  = (6,  5,  4)         # deep shadow offset
        hat_red = (185, 28, 28)       # red band
        hat_rdl = (110, 16, 16)       # band shadow underline

        brim_y  = sy - 15              # top of crown — brim lands at head top, clear of eyes
        crown_w = 18                  # narrower than old felt hat
        crown_h = 20                  # tall cylindrical crown
        crown_x = sx + (T - crown_w) // 2

        brim_w  = 24                  # flat brim — modest overhang
        brim_x  = sx + (T - brim_w) // 2
        brim_h  = 2                   # thin flat brim

        # Crown — shadow then fill
        pygame.draw.rect(surface, hat_sh,  (crown_x + 1, brim_y + 1, crown_w, crown_h))
        pygame.draw.rect(surface, hat_blk, (crown_x,     brim_y,     crown_w, crown_h))
        # Left edge highlight (1 px vertical)
        pygame.draw.line(surface, hat_hi,
                         (crown_x + 1, brim_y + 1),
                         (crown_x + 1, brim_y + crown_h - 2), 1)
        # Top edge highlight (1 px horizontal)
        pygame.draw.line(surface, hat_hi,
                         (crown_x + 1,           brim_y + 1),
                         (crown_x + crown_w - 2, brim_y + 1), 1)

        # Red band — 2 px, sits 4 px above crown base
        band_y = brim_y + crown_h - 4
        pygame.draw.rect(surface, hat_red, (crown_x, band_y,     crown_w, 2))
        pygame.draw.rect(surface, hat_rdl, (crown_x, band_y + 2, crown_w, 1))

        # Brim — shadow then fill, flush at crown base
        brim_top = brim_y + crown_h - 1
        pygame.draw.rect(surface, hat_sh,  (brim_x + 1, brim_top + 1, brim_w, brim_h))
        pygame.draw.rect(surface, hat_blk, (brim_x,     brim_top,     brim_w, brim_h))
        # Brim top highlight
        pygame.draw.line(surface, hat_hi,
                         (brim_x + 1,          brim_top),
                         (brim_x + brim_w - 2, brim_top), 1)

    # -- Eyes --
    eye_col = (48, 34, 18)
    eye_hi  = (210, 230, 250)
    if direction == DIR_DOWN:
        for ex in (cx - 3, cx + 3):
            pygame.draw.circle(surface, eye_col, (ex,     sy + 9), 2)
            pygame.draw.circle(surface, eye_hi,  (ex - 1, sy + 8), 1)
    elif direction == DIR_LEFT:
        pygame.draw.circle(surface, eye_col, (cx - 5, sy + 9), 2)
        pygame.draw.circle(surface, eye_hi,  (cx - 6, sy + 8), 1)
    elif direction == DIR_RIGHT:
        pygame.draw.circle(surface, eye_col, (cx + 5, sy + 9), 2)
        pygame.draw.circle(surface, eye_hi,  (cx + 4, sy + 8), 1)

    # -- Rosy cheeks --
    if direction != DIR_UP:
        cheek = (220, 155, 125)
        if direction == DIR_DOWN:
            pygame.draw.circle(surface, cheek, (cx - 5, sy + 11), 2)
            pygame.draw.circle(surface, cheek, (cx + 5, sy + 11), 2)
        elif direction == DIR_LEFT:
            pygame.draw.circle(surface, cheek, (cx - 3, sy + 11), 2)
        elif direction == DIR_RIGHT:
            pygame.draw.circle(surface, cheek, (cx + 3, sy + 11), 2)


def draw_character_preview(surface, sx, sy, config, scale=3):
    """
    Draw a scaled-up character preview for the character creation screen.
    The character is drawn at PLAYER_SIZE*scale resolution, centred on (sx, sy).
    """
    size = PLAYER_SIZE * scale
    buf  = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
    _draw_character_gfx(buf, 0, 0, DIR_DOWN, 0, config)
    scaled = pygame.transform.scale(buf, (size, size))
    surface.blit(scaled, (sx - size // 2, sy - size // 2))
