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
import datetime

from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TILE_SIZE,
    C_HOUSE_RED, C_HOUSE_TRIM, C_UI_TEXT, C_UI_GOLD,
    C_FLAG_BLUE, C_FLAG_YELLOW, C_UI_BG, C_UI_BORDER,
    C_SKY_DAY, SAVE_FILE,
    CROP_POTATO, CROP_CARROT, CROP_CORN, CROP_STRAWBERRY, CROP_NAMES,
    POTATO_SELL_PRICE, CARROT_SELL_PRICE, CORN_SELL_PRICE, STRAWBERRY_SELL_PRICE,
    POTATO_SEED_PRICE, CARROT_SEED_PRICE, CORN_SEED_PRICE, STRAWBERRY_SEED_PRICE,
)
from src.world import (
    World,
    _draw_sky_gradient, _draw_farmhouse, _draw_flagpole,
    _draw_tree, _draw_tree_shadow, _draw_bush, _draw_bush_shadow,
)
from src.tilemap import _draw_tile, T_GRASS, T_GRASS_FLOWER, T_PATH
from src.ui    import UI, _draw_panel, _blit_text
from src.player import (
    CharacterConfig, SHIRT_COLORS, PANTS_COLORS, draw_character_preview,
)

# Game state constants
STATE_TITLE              = "title"
STATE_PLAYING            = "playing"
STATE_PAUSED             = "paused"
STATE_CHARACTER_CREATION = "char_creation"


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

        # Screenshot button — two positions:
        #   _screenshot_btn      : during gameplay (below inventory panel, y=274)
        #   _screenshot_btn_top  : on title / character-creation screens (top-right, y=8)
        self._screenshot_btn     = pygame.Rect(SCREEN_WIDTH - 108, 274, 96, 26)
        self._screenshot_btn_top = pygame.Rect(SCREEN_WIDTH - 108,   8, 96, 26)

        # Character creation state
        self._char_config  = CharacterConfig()
        self._name_input   = self._char_config.name
        self._name_active  = False
        self._cc_rects     = {}   # interactive rect map built during draw

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
                self._on_keydown(event.key, event)

            elif event.type == pygame.TEXTINPUT:
                if self.state == STATE_CHARACTER_CREATION and self._name_active:
                    self._name_input += event.text

            elif event.type == pygame.MOUSEWHEEL:
                if self.state == STATE_PLAYING and self.world:
                    if event.y > 0:
                        self.world.zoom_in()
                    elif event.y < 0:
                        self.world.zoom_out()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _active_btn = (self._screenshot_btn_top
                               if self.state in (STATE_TITLE, STATE_CHARACTER_CREATION)
                               else self._screenshot_btn)
                if _active_btn.collidepoint(event.pos):
                    self._take_screenshot()
                elif self.state == STATE_PLAYING and self.world:
                    if self.world.market_open:
                        self._market_handle_click(event.pos)
                    elif (self.ui.zoom_btn_minus and
                            self.ui.zoom_btn_minus.collidepoint(event.pos)):
                        self.world.zoom_out()
                    elif (self.ui.zoom_btn_plus and
                            self.ui.zoom_btn_plus.collidepoint(event.pos)):
                        self.world.zoom_in()
                    else:
                        # Tool hotbar click
                        clicked_tool = False
                        for tool_id, rect in self.ui.hotbar_rects.items():
                            if rect.collidepoint(event.pos):
                                self.world.player.tool = tool_id
                                clicked_tool = True
                                break
                        if not clicked_tool:
                            # Seed type selection from inventory
                            for ctype, rect in self.ui.seed_type_rects.items():
                                if rect.collidepoint(event.pos):
                                    self.world.player.selected_seed = ctype
                                    break
                elif self.state == STATE_CHARACTER_CREATION:
                    self._cc_handle_click(event.pos)

    def update(self, dt: float):
        """Advance the game state by dt seconds."""
        self._title_timer += dt

        if self.state == STATE_PLAYING and self.world is not None:
            self.world.update(dt)

    def draw(self):
        """Render the current game state to the screen."""
        if self.state == STATE_TITLE:
            self._draw_title()

        elif self.state == STATE_CHARACTER_CREATION:
            self._draw_character_creation()

        elif self.state == STATE_PLAYING and self.world is not None:
            self.world.draw(self.screen)
            self.ui.draw(self.screen, self.world.player, self.world)

            if self.world.market_open:
                self._draw_market_window()

        elif self.state == STATE_PAUSED:
            # Draw the world dimmed, then the pause overlay
            if self.world:
                self.world.draw(self.screen)
                self.ui.draw(self.screen, self.world.player, self.world)
                if self.world.market_open:
                    self._draw_market_window()
            self._draw_pause_overlay()

        # Screenshot button always drawn on top
        self._draw_screenshot_btn()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_keydown(self, key: int, event=None):
        """Handle a key-press event according to the current state."""

        if self.state == STATE_TITLE:
            if key == pygame.K_RETURN or key == pygame.K_SPACE:
                # Go to character creation instead of jumping straight into game
                self._char_config = CharacterConfig()
                self._name_input  = self._char_config.name
                self._name_active = False
                self._cc_rects    = {}
                self.state = STATE_CHARACTER_CREATION
            elif key == pygame.K_l:
                self._try_load_game()

        elif self.state == STATE_CHARACTER_CREATION:
            if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
                self._char_config.name = self._name_input.strip() or "Farmer"
                self._start_new_game()
            elif key == pygame.K_ESCAPE:
                self.state = STATE_TITLE
            elif key == pygame.K_BACKSPACE:
                if self._name_active:
                    self._name_input = self._name_input[:-1]

        elif self.state == STATE_PLAYING:
            if key == pygame.K_ESCAPE:
                if self.world and self.world.market_open:
                    self.world.market_open = False
                else:
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

    def _draw_screenshot_btn(self):
        """Draw a small camera button; position depends on current state."""
        r = (self._screenshot_btn_top
             if self.state in (STATE_TITLE, STATE_CHARACTER_CREATION)
             else self._screenshot_btn)
        mx, my = pygame.mouse.get_pos()
        hovered = r.collidepoint(mx, my)

        col_bg = (60, 50, 35) if hovered else (38, 32, 22)
        col_bd = (160, 130, 70) if hovered else (110, 88, 48)
        pygame.draw.rect(self.screen, col_bg, r, border_radius=5)
        pygame.draw.rect(self.screen, col_bd, r, 1, border_radius=5)

        # Camera icon
        ix = r.x + 7
        iy = r.y + r.height // 2 - 5
        body_col = (195, 188, 175)
        lens_col = (55,  80, 130)
        lens_hi  = (130, 160, 210)
        pygame.draw.rect(self.screen, body_col, (ix,     iy + 3, 14,  9), border_radius=2)
        pygame.draw.rect(self.screen, body_col, (ix + 4, iy,      6,  4))   # viewfinder bump
        pygame.draw.circle(self.screen, lens_col, (ix + 7, iy + 7), 3)
        pygame.draw.circle(self.screen, lens_hi,  (ix + 6, iy + 6), 1)

        # Label
        lbl = self.hint_font.render("Capture", True,
                                    (230, 210, 150) if hovered else (185, 165, 110))
        self.screen.blit(lbl, (ix + 18, r.y + r.height // 2 - lbl.get_height() // 2))

    def _take_screenshot(self):
        """
        Save the current frame to the screenshots folder.
        Always writes 'latest.png' (for quick reference) plus a
        timestamped copy so nothing is ever overwritten.
        """
        folder = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(folder, exist_ok=True)

        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"screenshot_{ts}.png"

        pygame.image.save(self.screen, os.path.join(folder, name))
        pygame.image.save(self.screen, os.path.join(folder, "latest.png"))

        print(f"[Bullerbyn] Screenshot saved: screenshots/{name}")

        # Show a brief in-game notification if we're playing
        if self.state == STATE_PLAYING and self.world:
            self.world._add_notification("Screenshot saved! (F12)")

    # ------------------------------------------------------------------
    # Market Window
    # ------------------------------------------------------------------

    def _draw_market_window(self):
        """
        Draw the market stall buy/sell popup window.
        Rebuilds self._market_rects for click detection.
        """
        if not self.world:
            return
        world  = self.world
        player = world.player
        rects  = {}

        CROP_LIST = [CROP_POTATO, CROP_CARROT, CROP_CORN, CROP_STRAWBERRY]
        SELL_PRICES = {
            CROP_POTATO:     POTATO_SELL_PRICE,
            CROP_CARROT:     CARROT_SELL_PRICE,
            CROP_CORN:       CORN_SELL_PRICE,
            CROP_STRAWBERRY: STRAWBERRY_SELL_PRICE,
        }
        SEED_PRICES = {
            CROP_POTATO:     POTATO_SEED_PRICE,
            CROP_CARROT:     CARROT_SEED_PRICE,
            CROP_CORN:       CORN_SEED_PRICE,
            CROP_STRAWBERRY: STRAWBERRY_SEED_PRICE,
        }
        DOT_COLS = {
            CROP_POTATO:     (200, 158, 60),
            CROP_CARROT:     (220, 105, 30),
            CROP_CORN:       (235, 195, 45),
            CROP_STRAWBERRY: (210, 45, 45),
        }

        # Dim the game world behind the window
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 520, 360
        px = SCREEN_WIDTH  // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        _draw_panel(self.screen, px, py, pw, ph, alpha=245)

        # Title
        title = self.sub_font.render("Market Stall", True, C_UI_GOLD)
        self.screen.blit(title, (px + pw // 2 - title.get_width() // 2, py + 10))

        # Tab buttons
        tab_w, tab_h = 120, 26
        sell_tab_r = pygame.Rect(px + pw // 2 - tab_w - 4, py + 36, tab_w, tab_h)
        buy_tab_r  = pygame.Rect(px + pw // 2 + 4,          py + 36, tab_w, tab_h)
        rects["tab_sell"] = sell_tab_r
        rects["tab_buy"]  = buy_tab_r
        for tab_r, label, key in [(sell_tab_r, "Sell Crops", "sell"),
                                   (buy_tab_r,  "Buy Seeds",  "buy")]:
            active = (world.market_tab == key)
            bg = (100, 78, 38) if active else (52, 42, 24)
            bd = (200, 165, 65) if active else (110, 88, 46)
            pygame.draw.rect(self.screen, bg, tab_r, border_radius=5)
            pygame.draw.rect(self.screen, bd, tab_r, 2, border_radius=5)
            ts = self.hint_font.render(label, True,
                                       (240, 215, 100) if active else C_UI_TEXT)
            self.screen.blit(ts, (tab_r.x + tab_r.w // 2 - ts.get_width() // 2,
                                  tab_r.y + tab_r.h // 2 - ts.get_height() // 2))

        # Content area
        cy = py + 72
        pad = 18
        row_h = 46

        if world.market_tab == "sell":
            info = self.hint_font.render(
                "Sell your harvested crops for gold.", True, (160, 140, 90))
            self.screen.blit(info, (px + pad, cy))
            cy += 20

            for crop_type in CROP_LIST:
                qty     = player.harvest.get(crop_type, 0)
                price   = SELL_PRICES[crop_type]
                name    = CROP_NAMES[crop_type]
                dot_col = DOT_COLS[crop_type]
                total   = qty * price

                # Row background
                row_rect = pygame.Rect(px + pad, cy, pw - pad * 2, row_h - 4)
                if qty > 0:
                    rb = pygame.Surface(row_rect.size, pygame.SRCALPHA)
                    rb.fill((55, 42, 18, 80))
                    self.screen.blit(rb, row_rect.topleft)
                    pygame.draw.rect(self.screen, (100, 78, 38), row_rect, 1, border_radius=4)

                # Dot + name + qty
                pygame.draw.circle(self.screen, dot_col,
                                   (px + pad + 12, cy + row_h // 2 - 4), 7)
                pygame.draw.circle(self.screen, tuple(min(255,c+40) for c in dot_col),
                                   (px + pad + 10, cy + row_h // 2 - 6), 3)
                name_s = self.sub_font.render(f"{name}", True, C_UI_TEXT)
                self.screen.blit(name_s, (px + pad + 24, cy + 4))
                qty_s = self.hint_font.render(f"× {qty}", True,
                                              (200, 175, 90) if qty > 0 else (70, 58, 38))
                self.screen.blit(qty_s, (px + pad + 24, cy + row_h // 2))

                # Sell All button (only if qty > 0)
                if qty > 0:
                    btn_w, btn_h2 = 150, 26
                    btn_x = px + pw - pad - btn_w
                    btn_y = cy + (row_h - btn_h2) // 2 - 2
                    btn_r = pygame.Rect(btn_x, btn_y, btn_w, btn_h2)
                    rects[f"sell_{crop_type}"] = btn_r
                    pygame.draw.rect(self.screen, (75, 110, 45), btn_r, border_radius=5)
                    pygame.draw.rect(self.screen, (140, 195, 90), btn_r, 1, border_radius=5)
                    lbl = self.hint_font.render(
                        f"Sell All  →  {total}g", True, (200, 240, 150))
                    self.screen.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2,
                                          btn_y + btn_h2 // 2 - lbl.get_height() // 2))
                else:
                    none_s = self.hint_font.render("(none harvested)", True, (65, 52, 32))
                    none_w = pw - pad * 2 - 140
                    self.screen.blit(none_s, (px + pad + 140, cy + row_h // 2 - 6))

                cy += row_h

        else:  # buy tab
            info = self.hint_font.render(
                "Buy seed packets to plant new crops.", True, (160, 140, 90))
            self.screen.blit(info, (px + pad, cy))
            cy += 20

            for crop_type in CROP_LIST:
                price   = SEED_PRICES[crop_type]
                name    = CROP_NAMES[crop_type]
                dot_col = DOT_COLS[crop_type]
                owned   = player.seeds.get(crop_type, 0)
                can_buy = player.gold >= price * 5

                row_rect = pygame.Rect(px + pad, cy, pw - pad * 2, row_h - 4)
                if can_buy:
                    rb = pygame.Surface(row_rect.size, pygame.SRCALPHA)
                    rb.fill((30, 55, 22, 80))
                    self.screen.blit(rb, row_rect.topleft)
                    pygame.draw.rect(self.screen, (70, 100, 40), row_rect, 1, border_radius=4)

                pygame.draw.circle(self.screen, dot_col,
                                   (px + pad + 12, cy + row_h // 2 - 4), 7)
                pygame.draw.circle(self.screen, tuple(min(255,c+40) for c in dot_col),
                                   (px + pad + 10, cy + row_h // 2 - 6), 3)
                name_s = self.sub_font.render(f"{name} Seeds", True, C_UI_TEXT)
                self.screen.blit(name_s, (px + pad + 24, cy + 4))
                own_s = self.hint_font.render(
                    f"Have: {owned}  |  {price}g each", True, (160, 140, 90))
                self.screen.blit(own_s, (px + pad + 24, cy + row_h // 2))

                # Buy 5 button
                btn_w, btn_h2 = 160, 26
                btn_x = px + pw - pad - btn_w
                btn_y = cy + (row_h - btn_h2) // 2 - 2
                btn_r = pygame.Rect(btn_x, btn_y, btn_w, btn_h2)
                rects[f"buy_{crop_type}"] = btn_r
                if can_buy:
                    pygame.draw.rect(self.screen, (48, 80, 105), btn_r, border_radius=5)
                    pygame.draw.rect(self.screen, (100, 160, 205), btn_r, 1, border_radius=5)
                    lbl = self.hint_font.render(
                        f"Buy 5  →  {price*5}g", True, (160, 215, 255))
                else:
                    pygame.draw.rect(self.screen, (38, 32, 22), btn_r, border_radius=5)
                    pygame.draw.rect(self.screen, (75, 60, 38), btn_r, 1, border_radius=5)
                    lbl = self.hint_font.render(
                        f"Buy 5  →  {price*5}g", True, (80, 70, 50))
                self.screen.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2,
                                      btn_y + btn_h2 // 2 - lbl.get_height() // 2))

                cy += row_h

        # Footer: gold + close hint
        footer_y = py + ph - 32
        gold_s = self.sub_font.render(f"Gold: {player.gold}g", True, C_UI_GOLD)
        self.screen.blit(gold_s, (px + pad, footer_y))
        close_s = self.hint_font.render("ESC — Close", True, (160, 140, 90))
        self.screen.blit(close_s,
                         (px + pw - close_s.get_width() - pad, footer_y + 4))

        self._market_rects = rects

    def _market_handle_click(self, pos):
        """Handle clicks inside the market window."""
        if not self.world:
            return
        rects = getattr(self, "_market_rects", {})

        if "tab_sell" in rects and rects["tab_sell"].collidepoint(pos):
            self.world.market_tab = "sell"
            return
        if "tab_buy" in rects and rects["tab_buy"].collidepoint(pos):
            self.world.market_tab = "buy"
            return

        for crop_type in [CROP_POTATO, CROP_CARROT, CROP_CORN, CROP_STRAWBERRY]:
            sell_key = f"sell_{crop_type}"
            buy_key  = f"buy_{crop_type}"
            if sell_key in rects and rects[sell_key].collidepoint(pos):
                self.world.sell_harvest(crop_type)
                return
            if buy_key in rects and rects[buy_key].collidepoint(pos):
                self.world.buy_seeds(crop_type, 5)
                return

    def _start_new_game(self):
        """Create a fresh world and switch to the playing state."""
        self.world = World(char_config=self._char_config)
        self._market_rects = {}
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
            "character": p.char_config.to_dict(),
            "player": {
                "x":             p.x,
                "y":             p.y,
                "tool":          p.tool,
                "selected_seed": p.selected_seed,
                "gold":          p.gold,
                "seeds": {str(k): v for k, v in p.seeds.items()},
                "harvest": {str(k): v for k, v in p.harvest.items()},
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

            char_cfg = CharacterConfig.from_dict(data.get("character", {}))
            self._char_config = char_cfg
            self.world = World(char_config=char_cfg)
            w = self.world
            p = w.player

            w.day_number   = data.get("day",  1)
            w._day_timer   = data.get("time", 0.0)
            w.time_of_day  = (w._day_timer % 240) / 240

            pd = data.get("player", {})
            p.x             = float(pd.get("x",    p.x))
            p.y             = float(pd.get("y",    p.y))
            p.tool          = int(  pd.get("tool", p.tool))
            p.selected_seed = int(  pd.get("selected_seed", CROP_POTATO))
            p.gold          = int(  pd.get("gold", p.gold))
            p.rect.x        = int(p.x)
            p.rect.y        = int(p.y)
            # Seeds dict — keys stored as strings in JSON
            raw_seeds = pd.get("seeds", {})
            if isinstance(raw_seeds, dict):
                for k, v in raw_seeds.items():
                    p.seeds[int(k)] = int(v)
            else:
                # Backwards compat: old save had a single int
                p.seeds[CROP_POTATO] = int(raw_seeds)
            # Harvest dict
            raw_harvest = pd.get("harvest", {})
            if isinstance(raw_harvest, dict):
                for k, v in raw_harvest.items():
                    p.harvest[int(k)] = int(v)
            else:
                # Backwards compat: old save had "potatoes" int
                old_pot = int(pd.get("potatoes", 0))
                p.harvest[CROP_POTATO] = old_pot

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
        Draw the title screen using the same drawing functions as the game world,
        so the scene looks like a real snapshot of Bullerbyn.
        """
        import math

        screen = self.screen
        t      = self._title_timer
        T      = TILE_SIZE

        # ---- Sky (same gradient as in-game) ----
        _draw_sky_gradient(screen, C_SKY_DAY)

        # ---- Ground: grass tiles below the horizon line ----
        horizon_y = 400
        cols = SCREEN_WIDTH  // T + 2
        rows = (SCREEN_HEIGHT - horizon_y) // T + 2
        for row_i in range(rows):
            for col_i in range(cols):
                sx_ = col_i * T
                sy_ = horizon_y + row_i * T
                # Path strip at the very top of the ground
                if row_i == 0:
                    tile_id = T_PATH
                else:
                    h = (col_i * 2654435761 + (row_i + 50) * 2246822519) & 0xFFFFFFFF
                    tile_id = T_GRASS_FLOWER if h % 100 < 8 else T_GRASS
                _draw_tile(screen, pygame.Rect(sx_, sy_, T, T), tile_id, col_i, row_i + 50)

        # ---- Scene layout ----
        # Farmhouse — left side, sits on the horizon
        hw, hh = 300, 200
        hx = 70
        hy = horizon_y - hh + T // 3

        # Flagpole — just to the right of the house
        # _draw_flagpole expects sy such that pole base = sy + T*5
        fp_sx = hx + hw + 14
        fp_sy = horizon_y - T * 5

        # Trees — right side and far edges
        scene_trees = [
            (SCREEN_WIDTH - 130, horizon_y - T),
            (SCREEN_WIDTH - 230, horizon_y - T),
            (SCREEN_WIDTH - 50,  horizon_y - T),
            (14,                 horizon_y - T),
        ]
        # Bushes — near the house and path
        scene_bushes = [
            (hx + hw,            horizon_y + T // 3),
            (hx - T // 2,        horizon_y + T // 2),
            (fp_sx + T * 3,      horizon_y + T // 4),
        ]

        # Draw shadows first (behind everything)
        for tx_, ty_ in scene_trees:
            _draw_tree_shadow(screen, tx_, ty_)
        for bx_, by_ in scene_bushes:
            _draw_bush_shadow(screen, bx_, by_)

        # Farmhouse (pass t so smoke is animated on the title screen)
        _draw_farmhouse(screen, hx, hy, hw, hh, t)

        # Flagpole
        _draw_flagpole(screen, fp_sx, fp_sy, t / 240.0)

        # Trees and bushes
        for tx_, ty_ in scene_trees:
            _draw_tree(screen, tx_, ty_)
        for bx_, by_ in scene_bushes:
            _draw_bush(screen, bx_, by_)

        # ---- Animated fireflies on the grass ----
        for i in range(6):
            angle = t * 0.6 + i * 1.05
            fx = int(SCREEN_WIDTH * 0.55 + math.sin(angle + i * 0.9) * 200 + i * 40)
            fy = int(horizon_y + T + math.cos(angle * 0.8 + i) * 20 + i * 14)
            brightness = int(180 + math.sin(t * 3 + i) * 70)
            brightness = max(0, min(255, brightness))
            glow = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (brightness, brightness, 50, brightness // 2), (4, 4), 4)
            pygame.draw.circle(glow, (brightness, brightness, 80, brightness),      (4, 4), 2)
            screen.blit(glow, (fx % SCREEN_WIDTH - 4, fy))

        # ---- Title panel (centred, right half of screen) ----
        panel_w = 500
        panel_h = 230
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2 + 160
        panel_y = 80
        _draw_panel(screen, panel_x, panel_y, panel_w, panel_h, alpha=225)

        # Game title
        title_surf  = self.title_font.render("Bullerbyn", True, (255, 245, 205))
        shadow_surf = self.title_font.render("Bullerbyn", True, (28, 18, 8))
        tx = panel_x + panel_w // 2 - title_surf.get_width() // 2
        ty = panel_y + 22
        screen.blit(shadow_surf, (tx + 3, ty + 3))
        screen.blit(title_surf,  (tx, ty))

        # Subtitle
        sub = self.sub_font.render("A farming simulator", True, (200, 175, 118))
        screen.blit(sub, (panel_x + panel_w // 2 - sub.get_width() // 2, ty + 64))

        # Decorative divider line
        line_y = ty + 100
        pygame.draw.line(screen, (150, 120, 60),
                         (panel_x + 40, line_y), (panel_x + panel_w - 40, line_y), 2)
        pygame.draw.line(screen, (100, 76, 38),
                         (panel_x + 40, line_y + 3), (panel_x + panel_w - 40, line_y + 3), 1)

        # "Press enter" prompt
        start = self.sub_font.render("Press ENTER to begin", True, (225, 205, 140))
        screen.blit(start, (panel_x + panel_w // 2 - start.get_width() // 2,
                            line_y + 14))

        # Load hint
        load_txt = self.hint_font.render("Press L to load saved game",
                                         True, (165, 145, 95))
        screen.blit(load_txt, (panel_x + panel_w // 2 - load_txt.get_width() // 2,
                                line_y + 48))

        # ---- How-to-play hints at the bottom ----
        hints = [
            "Farm potatoes | Sell for gold",
            "WASD to walk  |  1-4 select tool  |  SPACE use tool",
            "F5 to save    |  ESC to pause",
        ]
        for i, hint in enumerate(hints):
            hs = self.hint_font.render(hint, True, (65, 50, 32))
            screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2,
                             SCREEN_HEIGHT - 68 + i * 18))

    # ------------------------------------------------------------------
    # Character Creation Screen
    # ------------------------------------------------------------------

    def _draw_character_creation(self):
        """
        Draw the character creation screen over the scenic backdrop.
        Also rebuilds self._cc_rects so mouse clicks can be hit-tested.
        """
        import math

        screen = self.screen
        t      = self._title_timer
        T      = TILE_SIZE
        rects  = {}   # key → pygame.Rect

        # ---- Reuse the title backdrop ----
        _draw_sky_gradient(screen, C_SKY_DAY)
        horizon_y = 400
        cols = SCREEN_WIDTH  // T + 2
        rows = (SCREEN_HEIGHT - horizon_y) // T + 2
        for row_i in range(rows):
            for col_i in range(cols):
                sx_ = col_i * T
                sy_ = horizon_y + row_i * T
                tile_id = T_PATH if row_i == 0 else (
                    T_GRASS_FLOWER if ((col_i * 2654435761 + (row_i + 50) * 2246822519) & 0xFFFFFFFF) % 100 < 8
                    else T_GRASS
                )
                _draw_tile(screen, pygame.Rect(sx_, sy_, T, T), tile_id, col_i, row_i + 50)

        hw, hh = 300, 200
        hx, hy = 70, horizon_y - hh + T // 3
        fp_sx  = hx + hw + 14
        fp_sy  = horizon_y - T * 5
        scene_trees  = [(SCREEN_WIDTH - 130, horizon_y - T), (SCREEN_WIDTH - 230, horizon_y - T),
                        (SCREEN_WIDTH - 50, horizon_y - T), (14, horizon_y - T)]
        scene_bushes = [(hx + hw, horizon_y + T // 3), (hx - T // 2, horizon_y + T // 2),
                        (fp_sx + T * 3, horizon_y + T // 4)]

        for tx_, ty_ in scene_trees:  _draw_tree_shadow(screen, tx_, ty_)
        for bx_, by_ in scene_bushes: _draw_bush_shadow(screen, bx_, by_)
        _draw_farmhouse(screen, hx, hy, hw, hh, t)
        _draw_flagpole(screen, fp_sx, fp_sy, t / 240.0)
        for tx_, ty_ in scene_trees:  _draw_tree(screen, tx_, ty_)
        for bx_, by_ in scene_bushes: _draw_bush(screen, bx_, by_)

        # Dim backdrop
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 80))
        screen.blit(dim, (0, 0))

        cfg = self._char_config

        # ---- Left panel — preview ----
        lp_w, lp_h = 240, 340
        lp_x = SCREEN_WIDTH // 2 - lp_w - 16
        lp_y = (SCREEN_HEIGHT - lp_h) // 2
        _draw_panel(screen, lp_x, lp_y, lp_w, lp_h, alpha=230)

        hdr = self.sub_font.render("Your Farmer", True, C_UI_GOLD)
        screen.blit(hdr, (lp_x + lp_w // 2 - hdr.get_width() // 2, lp_y + 12))

        # Preview sprite (scale 4×)
        prev_cx = lp_x + lp_w // 2
        prev_cy = lp_y + 160
        draw_character_preview(screen, prev_cx, prev_cy, cfg, scale=4)

        # Name below preview
        name_surf = self.sub_font.render(cfg.name or "_", True, C_UI_TEXT)
        screen.blit(name_surf, (lp_x + lp_w // 2 - name_surf.get_width() // 2, lp_y + 280))

        # ---- Right panel — form ----
        rp_w, rp_h = 380, 400
        rp_x = SCREEN_WIDTH // 2 + 16
        rp_y = (SCREEN_HEIGHT - rp_h) // 2
        _draw_panel(screen, rp_x, rp_y, rp_w, rp_h, alpha=230)

        hdr2 = self.sub_font.render("Create Your Farmer", True, C_UI_GOLD)
        screen.blit(hdr2, (rp_x + rp_w // 2 - hdr2.get_width() // 2, rp_y + 12))

        cy_  = rp_y + 50
        pad  = 16
        lbl_col = C_UI_TEXT
        sel_col = (255, 230, 80)     # gold highlight for selected option

        def label(text, y):
            s = self.hint_font.render(text, True, lbl_col)
            screen.blit(s, (rp_x + pad, y))

        def btn(text, bx, by, bw, bh, active, key):
            col_bg  = (100, 80, 40) if active else (55, 45, 30)
            col_txt = sel_col       if active else C_UI_TEXT
            r = pygame.Rect(bx, by, bw, bh)
            pygame.draw.rect(screen, col_bg,  r, border_radius=4)
            pygame.draw.rect(screen, (150, 120, 60), r, 1, border_radius=4)
            ts = self.hint_font.render(text, True, col_txt)
            screen.blit(ts, (bx + bw // 2 - ts.get_width() // 2, by + bh // 2 - ts.get_height() // 2))
            rects[key] = r

        # -- Name field --
        label("Name:", cy_)
        nf_x = rp_x + pad + 50
        nf_w = rp_w - pad * 2 - 50
        nf_h = 22
        nf_r = pygame.Rect(nf_x, cy_, nf_w, nf_h)
        nf_col = (80, 65, 40) if self._name_active else (50, 42, 28)
        pygame.draw.rect(screen, nf_col, nf_r, border_radius=3)
        pygame.draw.rect(screen, (150, 120, 60), nf_r, 1, border_radius=3)
        cursor = "|" if self._name_active and int(t * 2) % 2 == 0 else ""
        nf_txt = self.hint_font.render(self._name_input + cursor, True, C_UI_TEXT)
        screen.blit(nf_txt, (nf_x + 4, cy_ + 4))
        rects["name_field"] = nf_r
        cy_ += 34

        # -- Sex --
        label("Sex:", cy_)
        btn("Male",   rp_x + pad + 50,      cy_, 70, 22, cfg.sex == "male",   "sex_male")
        btn("Female", rp_x + pad + 50 + 78, cy_, 70, 22, cfg.sex == "female", "sex_female")
        cy_ += 34

        # -- Shirt colour --
        label("Shirt:", cy_ + 4)
        for i, col in enumerate(SHIRT_COLORS):
            cx2 = rp_x + pad + 55 + i * 34
            cy2 = cy_ + 12          # center y — circles sit flush at cy_
            r   = pygame.Rect(cx2 - 12, cy2 - 12, 24, 24)
            pygame.draw.ellipse(screen, col, r)
            if col == cfg.shirt_color:
                pygame.draw.ellipse(screen, sel_col, r, 3)
            else:
                pygame.draw.ellipse(screen, (0, 0, 0, 80), r, 1)
            rects[f"shirt_{i}"] = r
        cy_ += 32

        # -- Pants colour --
        label("Pants:", cy_ + 4)
        for i, col in enumerate(PANTS_COLORS):
            cx2 = rp_x + pad + 55 + i * 34
            cy2 = cy_ + 12          # center y — circles sit flush at cy_
            r   = pygame.Rect(cx2 - 12, cy2 - 12, 24, 24)
            pygame.draw.ellipse(screen, col, r)
            if col == cfg.pants_color:
                pygame.draw.ellipse(screen, sel_col, r, 3)
            else:
                pygame.draw.ellipse(screen, (0, 0, 0, 80), r, 1)
            rects[f"pants_{i}"] = r
        cy_ += 32

        # -- Hat toggle --
        label("Hat:", cy_)
        btn("ON",  rp_x + pad + 50,      cy_, 60, 22, cfg.has_hat,      "hat_on")
        btn("OFF", rp_x + pad + 50 + 68, cy_, 60, 22, not cfg.has_hat,  "hat_off")
        cy_ += 40

        # -- Dice / randomize button --
        db_w, db_h = 150, 32
        db_x = rp_x + pad
        db_y = cy_
        db_r = pygame.Rect(db_x, db_y, db_w, db_h)
        pygame.draw.rect(screen, (75, 58, 32), db_r, border_radius=6)
        pygame.draw.rect(screen, (160, 128, 64), db_r, 2, border_radius=6)
        rects["randomize"] = db_r

        # Dice face (20×20) — shows ⚄ (five dots)
        di_x = db_x + 6
        di_y = db_y + 6
        di_s = 20
        pygame.draw.rect(screen, (235, 228, 210), (di_x, di_y, di_s, di_s), border_radius=3)
        pygame.draw.rect(screen, (100, 76, 38),   (di_x, di_y, di_s, di_s), 1, border_radius=3)
        dot = (50, 38, 22)
        for dx, dy in [(4, 4), (12, 4), (8, 10), (4, 16), (12, 16)]:
            pygame.draw.circle(screen, dot, (di_x + dx, di_y + dy), 2)

        # "Randomize" label next to the die
        rnd_s = self.hint_font.render("Randomize", True, (220, 195, 120))
        screen.blit(rnd_s, (db_x + di_s + 12, db_y + db_h // 2 - rnd_s.get_height() // 2))

        cy_ += db_h + 10
        enter_s = self.sub_font.render("ENTER — Begin!", True, (225, 205, 140))
        screen.blit(enter_s, (rp_x + rp_w // 2 - enter_s.get_width() // 2, cy_))

        # Persist rects for click handling
        self._cc_rects = rects

    def _cc_handle_click(self, pos):
        """Handle a mouse click on the character creation screen."""
        rects = self._cc_rects
        cfg   = self._char_config

        if "name_field" in rects and rects["name_field"].collidepoint(pos):
            self._name_active = True
            return
        else:
            self._name_active = False

        if "randomize" in rects and rects["randomize"].collidepoint(pos):
            cfg.randomize()
            self._name_input = cfg.name
            return
        if "sex_male"   in rects and rects["sex_male"].collidepoint(pos):
            cfg.sex = "male";   return
        if "sex_female" in rects and rects["sex_female"].collidepoint(pos):
            cfg.sex = "female"; return
        if "hat_on"  in rects and rects["hat_on"].collidepoint(pos):
            cfg.has_hat = True;  return
        if "hat_off" in rects and rects["hat_off"].collidepoint(pos):
            cfg.has_hat = False; return

        for i in range(len(SHIRT_COLORS)):
            key = f"shirt_{i}"
            if key in rects and rects[key].collidepoint(pos):
                cfg.shirt_color = SHIRT_COLORS[i]; return

        for i in range(len(PANTS_COLORS)):
            key = f"pants_{i}"
            if key in rects and rects[key].collidepoint(pos):
                cfg.pants_color = PANTS_COLORS[i]; return

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
