"""All tunable constants for TradeSim. Logic code imports from here — no magic numbers."""

from pathlib import Path

# Paths are built from this file's location so the game runs from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# SQLite (D-46): the committed reference data and the player's own games
REFERENCE_DB_PATH = DATA_DIR / "reference.db"
PLAYER_DB_PATH = PROJECT_ROOT / "saves" / "player.db"
DB_VERSION = 1                # stored in the player database; a different number means "start fresh"
WEB_SLOT = "web"              # the game the web app autosaves and resumes

# Web app v2 (D-37): a real web server + hand-written HTML/CSS/JS front end
WEB_HOST = "127.0.0.1"        # localhost only: the game is for the player on this computer
WEB_PORT = 8000
WEB_MAX_NOTICES = 200         # toasts remembered for the page to fetch
WEB_MAX_BODY = 10_000         # bytes: longest request body the server will read
WEB_CANDLE_TICKS = 3          # the 1-day chart draws 15-minute candles (3 ticks each)
WEB_INDEX_CARDS = ["MKT100", "TECHX", "FINX", "HLTHX", "ENRGX", "CONSX", "COMMX", "INDUX",
                   "MATX", "UTILX", "REITX"]
WEB_CHART_RANGES = {"1M": 21, "3M": 63, "6M": 126, "ALL": 10_000}   # days of daily candles
WEB_OUTLOOKS_SHOWN = 8        # Robo-analyst: most bullish/bearish symbols listed
GAME_START_DATE = "2026-01-05"  # a Monday: day 0 on the charts (weekends are skipped)

# Game
STARTING_CASH = 10_000.00
FEE_PER_TRADE = 1.00          # flat $ per buy/sell
GAME_DAYS = 60

# Price model (docs/03-finance-model.md §3.2)
MIN_PRICE = 1.00              # price floor
MAX_DAILY_MOVE = 0.30         # clamp any single-day return to ±30%
ETF_BASE_VALUE = 100.00
MARKET_VOL = 0.0072           # common market factor (daily σ) in a "normal" mood
SECTOR_VOL = 0.0055           # common sector factor (daily σ)
TRADING_DAYS_PER_YEAR = 252   # used to turn daily numbers into yearly ones

# Real-life trends (finance model §3.2): market moods, volatility memory, company stories
REGIME_SEED_OFFSET = 2_000_003  # the moods use Random(seed + offset), separate from noise
STORM_KICK = 0.10             # GARCH α: how much yesterday's surprise raises today's nervousness
STORM_MEMORY = 0.85           # GARCH β: how slowly nervousness fades
STORY_SPREAD = 0.0006         # σ of each company's extra daily drift for one game (good/bad year)

# Intraday sessions (finance model §3.12): the market ticks every 5 minutes, 9:30 → 16:00
TICKS_PER_DAY = 78            # 6.5 trading hours of 5-minute bars
MINUTES_PER_TICK = 5
OPENING_BELL = 9 * 60 + 30    # minutes after midnight (9:30 am)
OPEN_GAP_SHARE = 0.2          # share of a day's variance that happens overnight (the opening gap)
VOLUME_SMILE = 1.5            # trading is this much busier at the open and close than at lunch
TICK_DOLLAR_VOLUME = 2_000_000.0  # $ traded per stock per tick on a normal day
ETF_VOLUME_SHARE = 0.5        # ETFs trade half as many dollars as a stock
BOOK_STEP = 0.0005            # gap between order-book price levels (0.05% of the price)
INTRADAY_SEED_OFFSET = 3_000_017  # each day's session uses Random(seed × stride + day + offset)
DAY_SEED_STRIDE = 100_003     # bigger than any game length, so no two (seed, day) pairs collide
PREHISTORY_DAYS = 120         # ~6 months of price history before day 0, for the charts
PREHISTORY_SEED_OFFSET = 4_000_037  # the history comes from a warm-up market with this seed offset

# Margin trading / leverage (finance model §3.13)
MAX_LEVERAGE = 5              # most a player may borrow up to: holdings ≤ 5 × own money
MAINTENANCE_SHARE = 0.5       # margin call once half of the starting cushion is lost (25% at 2×)
MARGIN_RATE = 0.08            # yearly interest on borrowed money, charged every night
LEVERAGE_LAB_LEVELS = (1, 2, 3, 5)  # margin levels the Leverage Lab compares
LEVERAGE_LAB_DAYS = 60        # the lab replays (up to) the last 60 days, history included
MARGIN_DANGER = 0.10          # coach warns when a fall this small would trigger a margin call
PREHISTORY_TICKS = 26         # the warm-up history only needs daily candles: 15-minute ticks

# Market events (Phase 2)
EVENT_PROBABILITY = 0.25      # chance of a news event per day (100 stocks need more news)
EVENT_SEED_OFFSET = 1_000_003 # events use Random(seed + offset), independent of prices
EVENT_REPEAT_GAP = 40         # the same headline can't come back within 40 days

# Diversification Lab (E-01)
LAB_DEFAULT_AMOUNT = 5_000.00
LAB_MIN_DAYS = 5
LAB_DEFAULT_STOCK = "NVDA"
LAB_DEFAULT_ETF = "MIX6"
LAB_VOL_RATIO = 1.5           # "swung N× harder" verdict needs at least this ratio
MONTE_CARLO_RUNS = 200
MC_LOSS_THRESHOLD = -0.20     # "lost more than 20%" in Monte Carlo lab

# Robo-analyst (E-06): a tiny logistic-regression model that reads charts
ROBO_MODEL_PATH = DATA_DIR / "robo_model.json"   # trained by tools/train_robo.py
MARKET_INDEX = "MKT100"        # the "whole market" the model (and the benchmark) looks at
ROBO_LOOKBACK = 20            # days of history the model reads
ROBO_HORIZON = 5              # it predicts: higher or lower 5 days from now?
ROBO_SAMPLE_EVERY = 3         # use every 3rd day when building training data (less overlap)
ROBO_EPOCHS = 200             # gradient-descent passes over the training data
ROBO_LEARNING_RATE = 1.0      # how big each nudge to the weights is
ROBO_STRONG = 0.55            # P(up) ≥ this → "Leaning up"; ≤ 1 − this → "Leaning down"
ROBO_DANGER = 0.60            # P(downturn) ≥ this → "Downturn likely"
ROBO_SAFE = 0.30              # P(downturn) ≤ this → "Looks healthy"
ROBO_TRAIN_SEED = 50_000_000  # training markets use seeds far from any player's game
ROBO_TRAIN_MARKETS = 40       # markets in the training set
ROBO_TEST_MARKETS = 20        # fresh markets for the honest test score
ROBO_TRAIN_DAYS = 250         # length of each training market

# Trade Coach (E-03)
CONCENTRATION_LIMIT = 0.50    # one stock above this share of equity → warning
PANIC_DROP = 0.08             # sold at a loss after a fall this big …
PANIC_WINDOW_DAYS = 3         # … over this many days → "panic selling" tip
OVERTRADE_PER_DAY = 5         # this many trades in one day → fees tip
CHASE_RISE = 0.12             # bought after a rise this big …
CHASE_WINDOW_DAYS = 5         # … over this many days → "chasing" tip
IDLE_CASH_LIMIT = 0.80        # more than this share in cash …
IDLE_CASH_GRACE_DAYS = 10     # … after this day → "cash doesn't grow" tip
FEE_TIP_MIN = 10.00           # fees tip only once fees reach $10 …
FEE_SHARE_LIMIT = 0.25        # … and are more than 25% of the profit/loss
GOOD_MAX_WEIGHT = 0.30        # "nicely diversified" praise: no stock above 30%
GOOD_MIN_SECTORS = 3
MAX_TIPS_AFTER_TRADE = 2      # so the coach isn't naggy

# What-if Replay (E-04)
DIP_TRIGGER = 0.02            # Buy-the-dip: the fund's daily fall that triggers a buy …
DIP_TRANCHE = 0.20            # … investing 20% of starting cash each time
DCA_INTERVAL_DAYS = 5         # Steady saver: invest every 5 days
CHASE_EVERY_DAYS = 5          # Chase the winner: switch into last week's best stock every 5 days

FEAR_CALM = 15                # fear gauge bands, like the real VIX: below 15 calm …
FEAR_UNEASY = 22              # … below 22 uneasy …
FEAR_PANIC = 30               # … below 30 nervous, above it panic
GRADE_SMALL_LOSS = -0.05      # report grade C down to a 5% loss, D below
BEAT_MARGIN = 0.01            # "beating the market" needs at least 1 percentage point

# Headline Lab (E-05)
MAX_HEADLINE_LENGTH = 200
