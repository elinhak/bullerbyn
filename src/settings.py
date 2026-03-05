"""
settings.py — Central configuration for Bullerbyn
===================================================
All important numbers, colors, and names live here.
Changing a value here changes it everywhere in the game,
so this is the first place to look when you want to tweak
things like player speed, crop grow times, or colors.
"""

# ---------------------------------------------------------------------------
# Window & Display
# ---------------------------------------------------------------------------
SCREEN_WIDTH  = 1280          # pixels wide
SCREEN_HEIGHT = 720           # pixels tall
FPS           = 60            # frames per second
TITLE         = "Bullerbyn"   # window title bar text

# ---------------------------------------------------------------------------
# Tile System
# ---------------------------------------------------------------------------
# The game world is divided into a grid of square "tiles".
# TILE_SIZE is how many pixels each tile occupies on screen.
# 48px gives a nice chunky pixel-art look on a 1280×720 window.
TILE_SIZE = 48   # screen pixels per tile (source art is 16px, scaled 3×)

# World size in tiles (the full scrollable map)
MAP_COLS = 60    # tiles across
MAP_ROWS = 45    # tiles tall

# Total world size in pixels (used for camera clamping)
WORLD_WIDTH  = MAP_COLS * TILE_SIZE   # 2880 px
WORLD_HEIGHT = MAP_ROWS * TILE_SIZE   # 2160 px

# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
PLAYER_SPEED = 200   # pixels per second — tweak this to make movement feel right
PLAYER_SIZE  = 32    # collision box size in pixels (slightly smaller than a tile)

# Player starting position (in pixels, top-left corner of starting tile)
# We start on the path between the house and the farm plot
PLAYER_START_COL = 10
PLAYER_START_ROW = 13

# ---------------------------------------------------------------------------
# Map Layout — key landmark positions (in tile coordinates)
# ---------------------------------------------------------------------------
# Farmhouse footprint (the building occupies these tiles — player can't walk through)
HOUSE_COL  = 2     # left edge tile column
HOUSE_ROW  = 1     # top edge tile row
HOUSE_COLS = 12    # width in tiles
HOUSE_ROWS = 9     # height in tiles

# Flagpole position (single tile column, spans several rows visually)
FLAG_COL = 15
FLAG_ROW = 2

# Farm plot (the fenced area where potatoes are grown)
FARM_COL  = 18    # left fence column
FARM_ROW  = 14    # top fence row
FARM_COLS = 14    # interior farmable width in tiles
FARM_ROWS = 10    # interior farmable height in tiles

# The farm interior starts one tile inside the fence
FARM_INNER_COL = FARM_COL + 1
FARM_INNER_ROW = FARM_ROW + 1
FARM_INNER_COLS = FARM_COLS - 2   # 12 farmable columns
FARM_INNER_ROWS = FARM_ROWS - 2   # 8 farmable rows

# ---------------------------------------------------------------------------
# Day / Night Cycle
# ---------------------------------------------------------------------------
# One in-game day = DAY_LENGTH real seconds
# 240 seconds = 4 real minutes per in-game day
DAY_LENGTH = 240

# Time-of-day thresholds (0.0 = midnight, 0.25 = 6 AM, 0.75 = 6 PM, 1.0 = midnight)
# The game starts at 6 AM (fraction 0.25)
START_TIME_FRACTION = 0.25

# Sky colour transition points
TIME_DAWN  = 0.20   # ~4:48 AM — sky begins brightening
TIME_DAY   = 0.27   # ~6:30 AM — full daylight
TIME_DUSK  = 0.73   # ~5:30 PM — sky starts dimming
TIME_NIGHT = 0.83   # ~8:00 PM — dark night

# ---------------------------------------------------------------------------
# Crops — Potato
# ---------------------------------------------------------------------------
# Stages are measured in in-game DAYS since planting.
# You can adjust these numbers to make potatoes grow faster or slower.
POTATO_DAYS_SPROUT  = 1    # tiny green shoot appears after 1 day
POTATO_DAYS_GROWING = 2    # plant gets bigger after 2 days
POTATO_DAYS_MATURE  = 4    # ready to harvest after 4 days

POTATO_SELL_PRICE = 25     # gold coins earned per harvested potato

# ---------------------------------------------------------------------------
# Crop Types
# ---------------------------------------------------------------------------
CROP_POTATO     = 0
CROP_CARROT     = 1
CROP_CORN       = 2
CROP_STRAWBERRY = 3

CROP_NAMES = {
    CROP_POTATO:     "Potato",
    CROP_CARROT:     "Carrot",
    CROP_CORN:       "Corn",
    CROP_STRAWBERRY: "Strawberry",
}

# ---------------------------------------------------------------------------
# Crops — Carrot  (grows slower than potato)
# ---------------------------------------------------------------------------
# Grow time properties are defined here in settings.py.
# The actual stage-advancement logic lives in src/crops.py → Crop.advance_day()
CARROT_DAYS_SPROUT  = 2    # days until tiny green shoots appear
CARROT_DAYS_GROWING = 4    # days until feathery tops are visible
CARROT_DAYS_MATURE  = 6    # days until carrot body is ready

CARROT_SELL_PRICE   = 40   # gold per harvested carrot

# ---------------------------------------------------------------------------
# Crops — Corn  (grows slower than carrot)
# ---------------------------------------------------------------------------
CORN_DAYS_SPROUT    = 3
CORN_DAYS_GROWING   = 6
CORN_DAYS_MATURE    = 9

CORN_SELL_PRICE     = 60   # gold per harvested corn

# ---------------------------------------------------------------------------
# Crops — Strawberry  (grows slowest)
# ---------------------------------------------------------------------------
STRAWBERRY_DAYS_SPROUT  = 3
STRAWBERRY_DAYS_GROWING = 7
STRAWBERRY_DAYS_MATURE  = 12

STRAWBERRY_SELL_PRICE   = 90   # gold per harvested strawberry

# ---------------------------------------------------------------------------
# Seed buy prices (purchased at the market stall)
# ---------------------------------------------------------------------------
POTATO_SEED_PRICE     = 15
CARROT_SEED_PRICE     = 25
CORN_SEED_PRICE       = 40
STRAWBERRY_SEED_PRICE = 65

# ---------------------------------------------------------------------------
# Inventory / Items
# ---------------------------------------------------------------------------
STARTING_GOLD       = 0    # start with nothing — earn through farming!
STARTING_SEEDS      = 5    # potato seeds given at the start

# Tool IDs — these match the hotbar slot numbers (1-4 keys on keyboard)
TOOL_HAND     = 0   # pick up items, interact
TOOL_HOE      = 1   # till the soil
TOOL_WATER    = 2   # water tilled soil
TOOL_SEEDS    = 3   # plant potato seeds

TOOL_NAMES = {
    TOOL_HAND:  "Hand",
    TOOL_HOE:   "Hoe",
    TOOL_WATER: "Watering Can",
    TOOL_SEEDS: "Seeds",
}

# ---------------------------------------------------------------------------
# Colors (R, G, B) — Swedish 1920s inspired palette
# ---------------------------------------------------------------------------

# Sky / atmosphere
C_SKY_NIGHT  = (  15,  20,  55)   # deep blue night
C_SKY_DAWN   = ( 220, 140,  80)   # warm orange dawn
C_SKY_DAY    = ( 110, 185, 230)   # clear Swedish summer sky
C_SKY_DUSK   = ( 200,  90,  60)   # red-orange sunset

# Ground tiles
C_GRASS_1    = (  75, 148,  62)   # main grass colour
C_GRASS_2    = (  60, 128,  50)   # slightly darker grass (checkerboard variation)
C_GRASS_EDGE = (  55, 115,  45)   # even darker for depth
C_PATH       = ( 178, 148,  95)   # packed earth path
C_PATH_DARK  = ( 155, 125,  75)   # path shadow variant
C_DIRT_DRY   = ( 145,  95,  45)   # untilled farmable soil
C_DIRT_TILLED= ( 100,  58,  20)   # freshly tilled furrows
C_DIRT_WET   = (  65,  35,  10)   # watered soil (dark, moist)
C_WATER      = (  80, 160, 210)   # water / pond
C_WATER_DARK = (  55, 125, 175)   # deeper water

# Building — Swedish Farmhouse
C_HOUSE_RED  = ( 168,  30,  34)   # Falurött — the iconic Swedish red
C_HOUSE_TRIM = ( 238, 232, 215)   # warm white for corners, window frames, edges
C_ROOF       = ( 100,  18,  20)   # very dark red/brown roof
C_ROOF_EDGE  = (  75,  12,  15)   # roof edge shadow
C_CHIMNEY    = ( 110,  95,  80)   # stone chimney
C_FOUNDATION = ( 130, 120, 110)   # stone foundation
C_WINDOW     = ( 160, 215, 240)   # light blue glass
C_DOOR       = ( 100,  65,  30)   # dark wood door
C_DOOR_FRAME = ( 238, 232, 215)   # white door frame

# Vegetation
C_TREE_TRUNK = ( 100,  65,  30)   # tree bark
C_TREE_DARK  = (  45, 100,  38)   # dark leaf canopy
C_TREE_MID   = (  60, 130,  50)   # mid leaf canopy
C_TREE_LIGHT = (  85, 160,  68)   # light leaf highlight
C_BUSH       = (  55, 115,  42)   # small bushes
C_FLOWERS_R  = ( 210,  70,  60)   # red wildflowers
C_FLOWERS_Y  = ( 220, 185,  50)   # yellow wildflowers

# Fence
C_FENCE      = ( 188, 155,  90)   # light wood fence
C_FENCE_DARK = ( 145, 110,  55)   # fence shadow side

# Crop colours per growth stage
C_CROP_SEED    = ( 120,  80,  30)   # barely visible seed bump
C_CROP_SPROUT  = (  90, 175,  60)   # little green shoot
C_CROP_GROWING = (  55, 145,  45)   # leafy young plant
C_CROP_MATURE  = ( 185, 170,  35)   # golden-green, ready to harvest

# Swedish flag colours
C_FLAG_BLUE   = (  0,  82, 158)    # Swedish flag blue
C_FLAG_YELLOW = ( 252, 189,  25)   # Swedish flag yellow/gold
C_POLE        = ( 110, 100,  85)   # wooden pole

# UI elements
C_UI_BG       = (  35,  25,  15)   # dark panel background
C_UI_BORDER   = ( 110,  85,  50)   # warm gold/brown border
C_UI_TEXT     = ( 220, 200, 155)   # warm off-white text
C_UI_GOLD     = ( 220, 175,  45)   # gold coin colour
C_UI_GREEN    = (  90, 185,  80)   # positive/good indicator
C_UI_SELECT   = ( 230, 185,  90)   # selected hotbar slot highlight
C_UI_SLOT     = (  55,  40,  25)   # empty hotbar slot
C_NOTIF_BG    = (  30,  22,  12, 200)  # notification background (with alpha)

# Night overlay (drawn on top of everything to darken the screen)
C_NIGHT_OVERLAY = (  10,  10,  40)  # dark blue-black tint

# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
SAVE_FILE = "saves/save.json"

# How close the player must be to a tile to interact with it (pixels)
INTERACT_RANGE = TILE_SIZE * 1.5
