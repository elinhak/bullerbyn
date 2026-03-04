"""
camera.py — The Camera / Viewport
===================================
The game world is much larger than the screen.
The Camera keeps track of which part of the world is currently visible.

Think of the camera as a window you hold up to the world:
  - The world stays fixed in place
  - The camera window moves around to follow the player
  - Everything we draw gets "shifted" by the camera offset so it
    appears in the right place on screen

Key concept:
  world_x, world_y  →  the actual position in the game world (pixels)
  screen_x, screen_y →  where that appears on the monitor (pixels)

  screen_x = world_x - camera.x
  screen_y = world_y - camera.y
"""

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT


class Camera:
    """
    Follows the player and lets us convert world coordinates to screen coordinates.

    Usage:
        camera = Camera()
        camera.center_on(player.rect.centerx, player.rect.centery)
        screen_pos = camera.apply(world_x, world_y)
    """

    def __init__(self):
        # Camera offset — how many pixels the view has scrolled from the top-left
        # of the world.  When camera.x=0, camera.y=0 you see the top-left corner.
        self.x = 0
        self.y = 0

        # Effective viewport size — shrinks when zoomed in so clamping and
        # culling remain correct at every zoom level.
        self.view_w = SCREEN_WIDTH
        self.view_h = SCREEN_HEIGHT

    def center_on(self, world_x: float, world_y: float):
        """
        Move the camera so that the given world position is in the centre of
        the screen.  We then clamp so the camera never goes outside the world.
        """
        # Put world_x/y in the middle of the viewport
        self.x = world_x - self.view_w // 2
        self.y = world_y - self.view_h // 2

        # Clamp: don't scroll past the left or top edge of the world
        self.x = max(0, self.x)
        self.y = max(0, self.y)

        # Clamp: don't scroll past the right or bottom edge of the world
        self.x = min(self.x, WORLD_WIDTH  - self.view_w)
        self.y = min(self.y, WORLD_HEIGHT - self.view_h)

    def apply(self, world_x: float, world_y: float) -> tuple:
        """
        Convert a world-space position to a screen-space position.

        Example:
            An object at world (500, 300) with camera offset (200, 100)
            appears at screen position (300, 200).
        """
        return (world_x - self.x, world_y - self.y)

    def apply_rect(self, rect) -> tuple:
        """
        Convert a pygame.Rect's world position to a screen (x, y) pair.
        Returns (screen_x, screen_y) for the top-left corner of the rect.
        """
        return (rect.x - self.x, rect.y - self.y)

    def is_visible(self, world_x: float, world_y: float,
                   width: float = 0, height: float = 0) -> bool:
        """
        Return True if the rectangle at (world_x, world_y) with the given
        size overlaps the current camera view.

        Used for culling — no point drawing things you can't see!
        A small margin (TILE_SIZE) accounts for partially-visible edge tiles.
        """
        margin = 64   # a little extra so edge tiles never pop in/out
        return (
            world_x + width  >= self.x - margin and
            world_x          <= self.x + self.view_w + margin and
            world_y + height >= self.y - margin and
            world_y          <= self.y + self.view_h + margin
        )
