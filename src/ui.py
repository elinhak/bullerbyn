"""
ui.py — Heads-Up Display (HUD)
================================
Everything drawn on the screen that is NOT part of the game world —
the player interface that stays fixed while the camera scrolls.

Includes:
  - Clock / day display (top-left)
  - Inventory panel (top-right: gold, seeds, potatoes)
  - Tool hotbar (bottom-centre, keys 1–4)
  - Notification messages (below clock)
  - Controls help text (bottom-left corner)

All positions are in screen coordinates (not world coordinates),
so the UI never scrolls with the camera.
"""

import pygame
import math
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE,
    TOOL_HAND, TOOL_HOE, TOOL_WATER, TOOL_SEEDS, TOOL_NAMES,
    C_UI_BG, C_UI_BORDER, C_UI_TEXT, C_UI_GOLD, C_UI_GREEN,
    C_UI_SELECT, C_UI_SLOT,
    C_FLAG_BLUE, C_FLAG_YELLOW,
    C_HOUSE_RED, C_HOUSE_TRIM,
)

# Tool icon colours (each tool has a distinct colour so you can recognise it)
TOOL_COLOURS = {
    TOOL_HAND:  (220, 180, 130),   # skin/wood
    TOOL_HOE:   (160,  95,  40),   # wooden handle + metal blade
    TOOL_WATER: ( 80, 160, 210),   # water-can blue
    TOOL_SEEDS: ( 90, 160,  55),   # potato-green
}


class UI:
    """
    Draws the complete HUD each frame.

    Usage:
        ui = UI()
        ui.draw(surface, player, world)
    """

    def __init__(self):
        pygame.font.init()
        # Prefer a slightly friendlier proportional font; fall back to monospace
        for fname in ("Georgia", "Palatino Linotype", "Times New Roman", "Courier New", None):
            try:
                self.font_large  = pygame.font.SysFont(fname, 22, bold=True)  if fname else pygame.font.Font(None, 24)
                self.font_medium = pygame.font.SysFont(fname, 17)              if fname else pygame.font.Font(None, 19)
                self.font_small  = pygame.font.SysFont(fname, 13)              if fname else pygame.font.Font(None, 15)
                break
            except Exception:
                continue

    def draw(self, surface: pygame.Surface, player, world):
        """
        Draw the complete HUD on top of the game world.
        Call this AFTER drawing the world so the UI is always on top.
        """
        self._draw_clock(surface, world)
        self._draw_inventory(surface, player)
        self._draw_hotbar(surface, player)
        self._draw_notifications(surface, world.notifications)
        self._draw_controls_hint(surface)

    # ------------------------------------------------------------------
    # Clock & Day display (top-left)
    # ------------------------------------------------------------------

    def _draw_clock(self, surface: pygame.Surface, world):
        """
        Draw a small clock panel in the top-left corner.
        Shows the in-game time (HH:MM) and current day number.
        """
        panel_x = 12
        panel_y = 12
        panel_w = 140
        panel_h = 56

        # Semi-transparent panel background
        _draw_panel(surface, panel_x, panel_y, panel_w, panel_h)

        # Day label
        day_text = f"Day {world.day_number}"
        _blit_text(surface, self.font_medium, day_text,
                   panel_x + 8, panel_y + 6, C_UI_GOLD)

        # Time
        time_text = world.get_time_string()
        _blit_text(surface, self.font_large, time_text,
                   panel_x + 8, panel_y + 26, C_UI_TEXT)

        # Small clock icon (simple drawn circle)
        cx = panel_x + panel_w - 22
        cy = panel_y + panel_h // 2
        r  = 14
        pygame.draw.circle(surface, C_UI_SLOT, (cx, cy), r)
        pygame.draw.circle(surface, C_UI_BORDER, (cx, cy), r, 2)
        # Clock hands
        t = world.time_of_day * math.pi * 2
        # Hour hand
        hx = int(cx + math.sin(t) * 6)
        hy = int(cy - math.cos(t) * 6)
        pygame.draw.line(surface, C_UI_TEXT, (cx, cy), (hx, hy), 2)
        # Minute hand (12× faster)
        mx = int(cx + math.sin(t * 12) * 9)
        my = int(cy - math.cos(t * 12) * 9)
        pygame.draw.line(surface, C_UI_GOLD, (cx, cy), (mx, my), 1)
        pygame.draw.circle(surface, C_UI_TEXT, (cx, cy), 2)

    # ------------------------------------------------------------------
    # Inventory panel (top-right)
    # ------------------------------------------------------------------

    def _draw_inventory(self, surface: pygame.Surface, player):
        """
        Draw the inventory panel in the top-right corner.
        Shows: gold coins, potato seeds remaining, harvested potatoes.
        """
        panel_w = 200
        panel_h = 86
        panel_x = SCREEN_WIDTH - panel_w - 12
        panel_y = 12

        _draw_panel(surface, panel_x, panel_y, panel_w, panel_h)

        items = [
            ("Gold",     f"{player.gold}",     C_UI_GOLD,       (220, 185, 55)),
            ("Seeds",    f"{player.seeds}",    C_UI_GREEN,      (105, 190, 70)),
            ("Potatoes", f"{player.potatoes}", (200, 162, 82),  (185, 145, 60)),
        ]
        for i, (label, val, text_col, dot_col) in enumerate(items):
            iy = panel_y + 10 + i * 22
            # Coloured dot icon
            pygame.draw.circle(surface, dot_col,      (panel_x + 14, iy + 8), 6)
            pygame.draw.circle(surface, (255, 255, 255, 80), (panel_x + 12, iy + 6), 2)
            _blit_text(surface, self.font_medium, f"{label}:",
                       panel_x + 26, iy, C_UI_TEXT)
            val_w = self.font_medium.size(val)[0]
            _blit_text(surface, self.font_medium, val,
                       panel_x + panel_w - val_w - 10, iy, text_col)

    # ------------------------------------------------------------------
    # Tool hotbar (bottom-centre)
    # ------------------------------------------------------------------

    def _draw_hotbar(self, surface: pygame.Surface, player):
        """
        Draw the four tool slots along the bottom of the screen.

        Each slot shows:
          - A background box (highlighted if selected)
          - A simple drawn icon for the tool
          - The key number (1–4)
          - The tool name

        Selected tool has a bright gold border.
        """
        num_tools = 4
        slot_size = 64     # size of each slot square
        gap       = 8      # gap between slots
        total_w   = num_tools * slot_size + (num_tools - 1) * gap + 24
        bar_x     = (SCREEN_WIDTH - total_w) // 2
        bar_y     = SCREEN_HEIGHT - slot_size - 20

        # Hotbar background panel
        _draw_panel(surface, bar_x - 8, bar_y - 8, total_w, slot_size + 24,
                    alpha=200)

        for i, tool_id in enumerate([TOOL_HAND, TOOL_HOE, TOOL_WATER, TOOL_SEEDS]):
            sx = bar_x + i * (slot_size + gap)
            sy = bar_y

            is_selected = (player.tool == tool_id)

            # Glow halo behind selected slot
            if is_selected:
                glow = pygame.Surface((slot_size + 12, slot_size + 12), pygame.SRCALPHA)
                for gr in range(8, 0, -1):
                    ga = 12 + gr * 8
                    pygame.draw.rect(glow, (*C_UI_GOLD, ga),
                                     (8 - gr, 8 - gr, slot_size + gr * 2, slot_size + gr * 2),
                                     border_radius=8 + gr)
                surface.blit(glow, (sx - 6, sy - 6))

            # Slot background
            if is_selected:
                pygame.draw.rect(surface, C_UI_SELECT, (sx, sy, slot_size, slot_size), border_radius=8)
                pygame.draw.rect(surface, C_UI_GOLD,   (sx, sy, slot_size, slot_size), 3, border_radius=8)
                # Inner top highlight
                pygame.draw.rect(surface, (min(255,C_UI_SELECT[0]+40), min(255,C_UI_SELECT[1]+36),
                                           min(255,C_UI_SELECT[2]+20), 180),
                                 (sx + 3, sy + 3, slot_size - 6, 4), border_radius=4)
            else:
                pygame.draw.rect(surface, C_UI_SLOT,   (sx, sy, slot_size, slot_size), border_radius=8)
                pygame.draw.rect(surface, C_UI_BORDER, (sx, sy, slot_size, slot_size), 2, border_radius=8)

            # Key number badge (small circle)
            key_col = C_UI_GOLD if is_selected else (105, 84, 52)
            badge_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(badge_surf, (*C_UI_BG, 190), (7, 7), 7)
            surface.blit(badge_surf, (sx + 3, sy + 3))
            _blit_text(surface, self.font_small, str(i + 1), sx + 6, sy + 4, key_col)

            # Tool icon
            icon_x = sx + slot_size // 2
            icon_y = sy + slot_size // 2 - 2
            _draw_tool_icon(surface, tool_id, icon_x, icon_y, selected=is_selected)

            # Tool name below slot
            name = TOOL_NAMES[tool_id]
            txt_col = C_UI_SELECT if is_selected else C_UI_TEXT
            txt_surface = self.font_small.render(name, True, txt_col)
            txt_x = sx + (slot_size - txt_surface.get_width()) // 2
            _blit_text(surface, self.font_small, name, txt_x, sy + slot_size + 4, txt_col)

    # ------------------------------------------------------------------
    # Notification messages (left side, below clock)
    # ------------------------------------------------------------------

    def _draw_notifications(self, surface: pygame.Surface, notifications: list):
        """
        Draw queued notification messages one below the other.
        Each message fades out (reduces in opacity) as its timer runs down.
        """
        x = 12
        y = 80   # start below the clock panel

        for msg, ttl in notifications[-5:]:   # show at most 5 recent messages
            # Opacity based on time remaining (full opacity for first 2s, fades last 1s)
            alpha = min(255, int(ttl / 1.0 * 255))
            alpha = max(60, alpha)

            # Background pill
            txt_surface = self.font_medium.render(msg, True, C_UI_TEXT)
            pill_w = txt_surface.get_width() + 20
            pill_h = txt_surface.get_height() + 8
            pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pygame.draw.rect(pill, (*C_UI_BG, min(200, alpha)),
                             (0, 0, pill_w, pill_h), border_radius=4)
            pygame.draw.rect(pill, (*C_UI_BORDER, min(180, alpha)),
                             (0, 0, pill_w, pill_h), 2, border_radius=4)

            # Render text onto the pill
            txt_alpha = pygame.Surface(txt_surface.get_size(), pygame.SRCALPHA)
            txt_alpha.blit(txt_surface, (0, 0))
            txt_alpha.set_alpha(alpha)
            pill.blit(txt_alpha, (10, 4))

            surface.blit(pill, (x, y))
            y += pill_h + 4

    # ------------------------------------------------------------------
    # Controls hint (bottom-left)
    # ------------------------------------------------------------------

    def _draw_controls_hint(self, surface: pygame.Surface):
        """
        Show a small controls reminder in the bottom-left corner.
        Useful for new players learning the controls.
        """
        hints = [
            "WASD / Arrows: Move",
            "1-4: Select tool",
            "SPACE / E: Use tool",
        ]
        x = 12
        y = SCREEN_HEIGHT - len(hints) * 18 - 10
        for hint in hints:
            _blit_text(surface, self.font_small, hint, x, y, (120, 100, 70))
            y += 18


# ---------------------------------------------------------------------------
# Tool icon drawing
# ---------------------------------------------------------------------------

def _draw_tool_icon(surface: pygame.Surface, tool_id: int,
                    cx: int, cy: int, selected: bool = False):
    """
    Draw a simple icon for each tool, centred at (cx, cy).
    Icons are drawn with pygame.draw calls — no image files needed.
    """
    bright = 40 if selected else 0

    if tool_id == TOOL_HAND:
        # A simple hand silhouette
        col = _add(TOOL_COLOURS[TOOL_HAND], bright)
        # Palm
        pygame.draw.ellipse(surface, col, (cx - 9, cy - 4, 18, 14))
        # Fingers
        for fx, fw in [(-8, 5), (-3, 5), (2, 5), (7, 4)]:
            pygame.draw.rect(surface, col, (cx + fx, cy - 14, fw, 12), border_radius=2)
        # Thumb
        pygame.draw.ellipse(surface, col, (cx - 14, cy - 2, 8, 10))

    elif tool_id == TOOL_HOE:
        # A garden hoe: long handle with angled blade
        col_handle = _add((140, 95, 45), bright)
        col_blade  = _add((160, 155, 150), bright)
        # Handle
        pygame.draw.line(surface, col_handle,
                         (cx - 8, cy + 14), (cx + 8, cy - 14), 5)
        # Blade (perpendicular rectangle at the top)
        pygame.draw.rect(surface, col_blade,
                         (cx,     cy - 16, 14, 6), border_radius=2)

    elif tool_id == TOOL_WATER:
        # A watering can: body, spout, handle
        col = _add(TOOL_COLOURS[TOOL_WATER], bright)
        col_dark = tuple(max(0, c - 30) for c in col)
        # Body
        pygame.draw.ellipse(surface, col, (cx - 12, cy - 8, 20, 16))
        # Spout (angled forward)
        spout_pts = [(cx + 6, cy - 2), (cx + 18, cy - 10),
                     (cx + 18, cy - 6), (cx + 8,  cy + 2)]
        pygame.draw.polygon(surface, col_dark, spout_pts)
        # Handle (loop at the back)
        pygame.draw.arc(surface, col_dark,
                        (cx - 18, cy - 10, 12, 18), 0, math.pi, 3)
        # Water drops from spout
        for i, (dx, dy) in enumerate([(20, -4), (22, 0), (19, 4)]):
            pygame.draw.circle(surface, col, (cx + dx, cy + dy), 2)

    elif tool_id == TOOL_SEEDS:
        # A small seed bag with potato seeds spilling out
        col_bag  = _add((170, 130, 60), bright)
        col_seed = _add((100, 160, 55), bright)
        # Bag body
        pygame.draw.rect(surface, col_bag, (cx - 8, cy - 6, 16, 18), border_radius=4)
        pygame.draw.rect(surface, _add(col_bag, 20), (cx - 6, cy - 4, 12, 4))
        # Bag top tie
        pygame.draw.ellipse(surface, _add(col_bag, -20), (cx - 4, cy - 10, 8, 6))
        # Some seeds
        for dx, dy in [(-4, 6), (0, 10), (4, 7), (-2, 14), (3, 13)]:
            pygame.draw.circle(surface, col_seed, (cx + dx, cy + dy), 3)


# ---------------------------------------------------------------------------
# Shared drawing helpers
# ---------------------------------------------------------------------------

def _draw_panel(surface: pygame.Surface,
                x: int, y: int, w: int, h: int,
                alpha: int = 215):
    """
    Draw a polished semi-transparent rounded panel with inner highlight bevel.
    """
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    # Main background fill
    pygame.draw.rect(panel, (*C_UI_BG, alpha), (0, 0, w, h), border_radius=8)
    # Subtle inner top-edge highlight (simulates panel thickness)
    hi_col = (min(255, C_UI_BG[0]+40), min(255, C_UI_BG[1]+32), min(255, C_UI_BG[2]+22))
    pygame.draw.rect(panel, (*hi_col, min(255, alpha - 50)),
                     (2, 2, w - 4, 3), border_radius=6)
    # Outer border
    pygame.draw.rect(panel, (*C_UI_BORDER, min(255, alpha + 25)),
                     (0, 0, w, h), 2, border_radius=8)
    # Inner shadow at bottom
    sh_col = (max(0, C_UI_BG[0]-12), max(0, C_UI_BG[1]-10), max(0, C_UI_BG[2]-8))
    pygame.draw.rect(panel, (*sh_col, min(255, alpha - 30)),
                     (2, h - 4, w - 4, 2), border_radius=4)
    surface.blit(panel, (x, y))


def _blit_text(surface: pygame.Surface,
               font: pygame.font.Font,
               text: str,
               x: int, y: int,
               colour: tuple):
    """Render and blit a text string at (x, y) with a subtle drop shadow."""
    # Shadow (dark, offset 1px)
    shadow = font.render(text, True, (10, 10, 10))
    surface.blit(shadow, (x + 1, y + 1))
    # Main text
    rendered = font.render(text, True, colour)
    surface.blit(rendered, (x, y))


def _add(colour: tuple, amount: int) -> tuple:
    """Add a brightness offset to an RGB colour (clamp to 0–255)."""
    return tuple(max(0, min(255, c + amount)) for c in colour)
