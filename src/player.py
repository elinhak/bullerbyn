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

    def __init__(self):
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
        Draw a simple top-down pixel-art character.
        The character is 32×32 pixels on screen.

        For a top-down game we show:
          - A round head (skin colour + hat)
          - Body (shirt colour)
          - Two legs (shoes) that animate
        """
        T  = PLAYER_SIZE         # 32
        cx = sx + T // 2        # centre x
        cy = sy + T // 2        # centre y

        # -- Shadow --
        pygame.draw.ellipse(surface, (0, 0, 0, 80),
                            (sx + 4, sy + T - 8, T - 8, 8))

        # -- Legs/feet (drawn first, behind body) --
        if direction in (DIR_DOWN, DIR_UP):
            # Legs visible below/above body
            leg_offset = 4 if frame == 0 else -4
            pygame.draw.rect(surface, COL_PANTS, (cx - 9, sy + 18, 8, 8))
            pygame.draw.rect(surface, COL_PANTS, (cx + 1, sy + 18, 8, 8))
            pygame.draw.rect(surface, COL_SHOES, (cx - 10, sy + 24, 9, 5))
            pygame.draw.rect(surface, COL_SHOES, (cx + 1,  sy + 24, 9, 5))
        else:
            # Side view — legs one in front of the other
            leg_offset = 5 if frame == 0 else -5
            pygame.draw.rect(surface, COL_PANTS, (cx - 8, sy + 18 - leg_offset, 7, 9))
            pygame.draw.rect(surface, COL_PANTS, (cx + 1, sy + 18 + leg_offset, 7, 9))

        # -- Body (shirt) --
        pygame.draw.ellipse(surface, COL_SHIRT,
                            (sx + 6, sy + 10, T - 12, 16))

        # -- Arms --
        arm_w, arm_h = 5, 10
        if direction == DIR_LEFT:
            pygame.draw.rect(surface, COL_SHIRT, (sx,        sy + 12, arm_w, arm_h))
            pygame.draw.rect(surface, COL_SKIN,  (sx - 1,    sy + 20, arm_w, 5))
        elif direction == DIR_RIGHT:
            pygame.draw.rect(surface, COL_SHIRT, (sx + T - arm_w, sy + 12, arm_w, arm_h))
            pygame.draw.rect(surface, COL_SKIN,  (sx + T - arm_w, sy + 20, arm_w + 1, 5))
        else:
            # Facing up/down — show both arms to the sides
            pygame.draw.rect(surface, COL_SHIRT, (sx + 2,       sy + 13, arm_w, 9))
            pygame.draw.rect(surface, COL_SHIRT, (sx + T - arm_w - 2, sy + 13, arm_w, 9))

        # -- Head --
        head_r = 9
        pygame.draw.circle(surface, COL_SKIN, (cx, sy + 9), head_r)

        # -- Hair (visible at back depending on direction) --
        if direction == DIR_DOWN:
            pygame.draw.arc(surface, COL_HAIR,
                            (cx - head_r, sy, head_r * 2, head_r * 2),
                            0, 3.14159, 3)
        elif direction == DIR_UP:
            pygame.draw.circle(surface, COL_HAIR, (cx, sy + 9), head_r)  # full back

        # -- Hat (wide-brimmed 1920s style) --
        brim_y  = sy + 1
        brim_w  = T - 4
        crown_w = T - 12
        crown_h = 7
        # Brim
        pygame.draw.rect(surface, COL_HAT,
                         (sx + 2, brim_y + crown_h - 2, brim_w, 4))
        # Crown
        pygame.draw.rect(surface, COL_HAT,
                         (sx + (T - crown_w) // 2, brim_y, crown_w, crown_h))
        # Hat band (light-coloured strip on the brim)
        pygame.draw.rect(surface, (140, 110, 60),
                         (sx + (T - crown_w) // 2, brim_y + crown_h - 3, crown_w, 3))

        # -- Eyes (visible only when facing down or sideways) --
        if direction == DIR_DOWN:
            pygame.draw.circle(surface, (50, 35, 20), (cx - 3, sy + 9), 2)
            pygame.draw.circle(surface, (50, 35, 20), (cx + 3, sy + 9), 2)
        elif direction == DIR_LEFT:
            pygame.draw.circle(surface, (50, 35, 20), (cx - 5, sy + 9), 2)
        elif direction == DIR_RIGHT:
            pygame.draw.circle(surface, (50, 35, 20), (cx + 5, sy + 9), 2)
