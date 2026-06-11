"""Append-only daily price history stored as a CSV committed to the repo."""
from __future__ import annotations

import pandas as pd

from . import config

COLUMNS = [
    "date", "card_id", "name", "set_name", "variant",
    "market", "low", "mid", "high", "cm_trend", "cm_avg30",
]


def load_history() -> pd.DataFrame:
    if config.HISTORY_PATH.exists():
        return pd.read_csv(config.HISTORY_PATH, parse_dates=["date"])
    return pd.DataFrame(columns=COLUMNS)


def append_snapshot(rows: list[dict]) -> pd.DataFrame:
    """Merge today's rows into history (idempotent per date+card) and save."""
    history = load_history()
    new = pd.DataFrame(rows, columns=COLUMNS)
    new["date"] = pd.to_datetime(new["date"])
    combined = pd.concat([history, new], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined = (
        combined.drop_duplicates(subset=["date", "card_id"], keep="last")
        .sort_values(["date", "card_id"])
        .reset_index(drop=True)
    )
    config.HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = combined.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(config.HISTORY_PATH, index=False)
    return combined
