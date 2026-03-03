"""
main.py — Bullerbyn Entry Point
================================
Run this file to start the game:

    python main.py

Requirements:
    pip install pygame

What this file does:
  1. Initialises pygame (must happen before anything else)
  2. Creates the game window
  3. Creates the Game object (which sets up everything else)
  4. Runs the main game loop until the player closes the window

The main game loop runs roughly 60 times per second.
Each iteration ("frame") does three things:
  A. handle_events()  — check keyboard/mouse input
  B. update(dt)       — advance all game logic (movement, timers, etc.)
  C. draw()           — render everything to the screen

"dt" (delta time) is the time in seconds since the last frame.
Using dt makes the game run at the same SPEED regardless of whether
the computer draws 30 or 120 frames per second.
"""

import sys
import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from src.game     import Game


def main():
    # -------------------------------------------------------------------
    # 1. Initialise pygame
    # -------------------------------------------------------------------
    pygame.init()

    # -------------------------------------------------------------------
    # 2. Create the window
    # -------------------------------------------------------------------
    # pygame.RESIZABLE lets the player resize the window (optional).
    # Remove that flag if you want a fixed-size window.
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)

    # Set window icon — a simple coloured square since we have no icon file
    icon = pygame.Surface((32, 32))
    icon.fill((168, 30, 34))          # Swedish red
    pygame.draw.rect(icon, (252, 189, 25), (10, 6, 4, 20))   # yellow vertical bar
    pygame.draw.rect(icon, (252, 189, 25), (6, 14, 20, 4))   # yellow horizontal bar
    pygame.display.set_icon(icon)

    # -------------------------------------------------------------------
    # 3. Create the Game object
    # -------------------------------------------------------------------
    game = Game(screen)

    # -------------------------------------------------------------------
    # 4. Main game loop
    # -------------------------------------------------------------------
    clock = pygame.time.Clock()

    while True:
        # Measure elapsed time since last frame (in milliseconds → convert to seconds)
        dt = clock.tick(FPS) / 1000.0

        # Cap dt so that if the game freezes briefly (e.g. loading a file),
        # the physics/timers don't jump wildly forward.
        dt = min(dt, 0.1)

        # A. Process keyboard/mouse/window events
        game.handle_events()

        # B. Update game state (player, crops, day timer, etc.)
        game.update(dt)

        # C. Render everything to the back buffer
        game.draw()

        # Flip the back buffer to the screen (show what we just drew)
        pygame.display.flip()


if __name__ == "__main__":
    main()
