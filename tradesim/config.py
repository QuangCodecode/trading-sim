"""All tunable constants for TradeSim. Logic code imports from here — no magic numbers."""

from pathlib import Path

# Paths are built from this file's location so the game runs from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UNIVERSE_PATH = DATA_DIR / "universe.json"
EVENTS_PATH = DATA_DIR / "events.json"

# Game
STARTING_CASH = 10_000.00
FEE_PER_TRADE = 1.00          # flat $ per buy/sell
GAME_DAYS = 60

# Price model (docs/03-finance-model.md §3.2)
MIN_PRICE = 1.00              # price floor
MAX_DAILY_MOVE = 0.30         # clamp any single-day return to ±30%
ETF_BASE_VALUE = 100.00
MARKET_VOL = 0.008            # common market factor (daily σ)
SECTOR_VOL = 0.010            # common sector factor (daily σ)

# Market events (Phase 2)
EVENT_PROBABILITY = 0.15      # chance of a news event per day
EVENT_SEED_OFFSET = 1_000_003 # events use Random(seed + offset), independent of prices

# Diversification Lab (E-01)
LAB_DEFAULT_AMOUNT = 5_000.00
LAB_MIN_DAYS = 5
LAB_DEFAULT_STOCK = "NVDA"
LAB_DEFAULT_ETF = "MIX6"
LAB_VOL_RATIO = 1.5           # "swung N× harder" verdict needs at least this ratio
MONTE_CARLO_RUNS = 200
MC_LOSS_THRESHOLD = -0.20     # "lost more than 20%" in Monte Carlo lab

# Charts
CHART_HEIGHT = 12
CHART_WIDTH = 60
SPARKLINE_DAYS = 10

# Headline Lab (E-05)
JEV_API_KEY_ENV = "JEV_API_KEY"   # read with os.environ.get; never hard-code a key
JEV_TIMEOUT_S = 3                 # give up and fall back after 3 s
SENTIMENT_CACHE_PATH = DATA_DIR / "sentiment_cache.json"
NEUTRAL_BAND = 0.60               # confidence below this → shown as "neutral"
MAX_HEADLINE_LENGTH = 200
