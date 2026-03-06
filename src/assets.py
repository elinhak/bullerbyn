"""
assets.py — Image Asset Loader
================================
Central place to load all PNG sprite sheets and individual frames.

Usage
-----
    from src.assets import Assets
    Assets.load()               # call once at startup in Game.__init__
    img = Assets.get("player")  # returns Surface or None if not found

Naming convention
-----------------
Drop PNGs into assets/images/<category>/ and register them in MANIFEST
below.  Each entry maps a key to a relative path and an optional target
size (w, h) in pixels.  If size is None the image is loaded at its
natural resolution.  If the file is missing, Assets.get() returns None
and the game falls back to its drawn graphics — so you can add art
incrementally without breaking anything.

Category folders
----------------
  assets/images/player/      — character sprites / walk frames
  assets/images/crops/       — crop growth stages (seed → mature)
  assets/images/tiles/       — ground tile overrides
  assets/images/ui/          — icons, panels, buttons
  assets/images/buildings/   — farmhouse, sell stall, etc.

Adding a new sprite
-------------------
1. Drop the PNG into the appropriate sub-folder.
2. Add a line to MANIFEST:
       "my_key": ("crops/my_sprite.png", (48, 48)),
3. Use it anywhere:
       img = Assets.get("my_key")
       if img:
           screen.blit(img, (x, y))
"""

import os
import pygame

# ---------------------------------------------------------------------------
# Manifest: key -> (relative path inside assets/images/, target size or None)
# ---------------------------------------------------------------------------
MANIFEST: dict[str, tuple[str, tuple[int, int] | None]] = {
    # --- Player ---
    # "player_idle":       ("player/idle.png",          (48, 96)),
    # "player_walk_down":  ("player/walk_down.png",     (48, 96)),

    # --- Crops (one image per growth stage per crop type) ---
    "potato_seed":       ("crops/potato_seed.png",    (48, 48)),
    "potato_sprout":     ("crops/potato_sprout.png",  (48, 48)),
    "potato_growing":    ("crops/potato_growing.png", (48, 48)),
    "potato_mature":     ("crops/potato_mature.png",  (48, 48)),

    # --- Tiles ---
    # "tile_grass":        ("tiles/grass.png",          (48, 48)),
    # "tile_path":         ("tiles/path.png",           (48, 48)),
    # "tile_farm":         ("tiles/farm.png",           (48, 48)),
    # "tile_water":        ("tiles/water.png",          (48, 48)),

    # --- Buildings ---
    # "farmhouse":         ("buildings/farmhouse.png",  (300, 200)),

    # --- UI icons ---
    # "icon_gold":         ("ui/gold.png",              (16, 16)),
    # "icon_seed":         ("ui/seed.png",              (16, 16)),
}

# ---------------------------------------------------------------------------
# Internal store
# ---------------------------------------------------------------------------
_images: dict[str, pygame.Surface] = {}
_base   = os.path.join(os.path.dirname(__file__), "..", "assets", "images")


class Assets:
    """Static container for loaded game images."""

    @staticmethod
    def load() -> None:
        """
        Load all images listed in MANIFEST.
        Call once after pygame.display.init() — usually in Game.__init__.
        Missing files are silently skipped; Assets.get() returns None for them.
        """
        for key, (rel_path, size) in MANIFEST.items():
            full = os.path.normpath(os.path.join(_base, rel_path))
            if not os.path.isfile(full):
                continue
            try:
                surf = pygame.image.load(full).convert_alpha()
                if size is not None:
                    surf = pygame.transform.scale(surf, size)
                _images[key] = surf
            except Exception as exc:
                print(f"[Assets] Warning: could not load '{key}' ({full}): {exc}")

    @staticmethod
    def get(key: str) -> pygame.Surface | None:
        """Return the loaded Surface for *key*, or None if it wasn't loaded."""
        return _images.get(key)

    @staticmethod
    def loaded_keys() -> list[str]:
        """Return a list of all successfully loaded asset keys."""
        return list(_images.keys())
