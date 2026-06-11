"""Central config: paths, env vars, signal parameters."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = REPO_ROOT / "watchlist.yaml"
HISTORY_PATH = REPO_ROOT / "data" / "history.csv"

POKEMONTCG_API_KEY = os.environ.get("POKEMONTCG_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Signal parameters ---
MIN_HISTORY_DAYS = 8       # below this, fall back to cross-sectional (spread) signal
ZSCORE_WINDOW = 30         # rolling window for price z-score
DRAWDOWN_WINDOW = 90       # trailing high lookback for per-card drawdown
BUY_SCORE_THRESHOLD = 0.5  # undervaluation score in [0, 1]; >= this flags a buy idea
TOP_N_IDEAS = 5            # max cards listed in the daily digest

# Index dip-alert thresholds (drawdown from trailing high)
INDEX_DIP_MILD = -0.05     # "buy zone"
INDEX_DIP_STRONG = -0.10   # "strong buy zone"
