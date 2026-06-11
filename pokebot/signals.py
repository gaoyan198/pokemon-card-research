"""Index construction and per-card undervaluation signals.

Two regimes per card:
  * >= MIN_HISTORY_DAYS of our own history: time-series signals —
    z-score of price vs a rolling mean, and drawdown from the trailing high.
  * cold start (fewer days): cross-sectional proxy — how far the live market
    price sits below TCGplayer's mid price ("spread"). Weak, but available
    from day 1; history-based signals take over automatically as data accrues.

Undervaluation score is normalised to [0, 1]; higher = cheaper vs its own
recent past. This is mean-reversion logic, not fair-value appraisal — it finds
dips in cards you already believe in, which matches a buy-the-dip mandate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _price_series(df: pd.DataFrame) -> pd.Series:
    """Daily price per card: TCGplayer market, falling back to Cardmarket trend."""
    return df["market"].fillna(df["cm_trend"])


def build_index(history: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight index: each card normalised to 100 at its first observation,
    averaged across cards per day. Returns a frame with index level, change and
    drawdown columns; empty frame if there is not enough data yet."""
    if history.empty:
        return pd.DataFrame()
    df = history.copy()
    df["price"] = _price_series(df)
    pivot = df.pivot_table(index="date", columns="card_id", values="price").sort_index()
    pivot = pivot.ffill()
    normed = pivot / pivot.apply(lambda col: col.loc[col.first_valid_index()])
    out = pd.DataFrame({"level": normed.mean(axis=1) * 100.0})
    out["chg_1d"] = out["level"].pct_change(1)
    out["chg_7d"] = out["level"].pct_change(7)
    out["chg_30d"] = out["level"].pct_change(30)
    out["drawdown"] = out["level"] / out["level"].cummax() - 1.0
    return out


def card_signals(history: pd.DataFrame) -> pd.DataFrame:
    """One row per card with latest price, signal components, and score."""
    if history.empty:
        return pd.DataFrame()
    df = history.copy()
    df["price"] = _price_series(df)
    rows = []
    for card_id, g in df.sort_values("date").groupby("card_id"):
        g = g.dropna(subset=["price"])
        if g.empty:
            continue
        latest = g.iloc[-1]
        price = latest["price"]
        n_days = g["date"].nunique()

        zscore = np.nan
        drawdown = np.nan
        if n_days >= config.MIN_HISTORY_DAYS:
            window = g["price"].tail(config.ZSCORE_WINDOW)
            if window.std() > 0:
                zscore = (price - window.mean()) / window.std()
            trail_high = g["price"].tail(config.DRAWDOWN_WINDOW).max()
            drawdown = price / trail_high - 1.0

        spread = np.nan
        if pd.notna(latest.get("mid")) and latest["mid"] > 0 and pd.notna(latest.get("market")):
            spread = (latest["mid"] - latest["market"]) / latest["mid"]

        # --- score in [0, 1] ---
        if not np.isnan(zscore) or not np.isnan(drawdown):
            z_comp = float(np.clip(-zscore, 0, 3) / 3) if not np.isnan(zscore) else 0.0
            dd_comp = float(np.clip(-drawdown, 0, 0.3) / 0.3) if not np.isnan(drawdown) else 0.0
            score = 0.6 * z_comp + 0.4 * dd_comp
            regime = "history"
        elif not np.isnan(spread):
            score = float(np.clip(spread, 0, 0.3) / 0.3)
            regime = "cold-start"
        else:
            score, regime = 0.0, "no-signal"

        rows.append({
            "card_id": card_id,
            "name": latest["name"],
            "set_name": latest["set_name"],
            "price": price,
            "n_days": n_days,
            "zscore": zscore,
            "drawdown": drawdown,
            "spread": spread,
            "score": round(score, 3),
            "regime": regime,
        })
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


def buy_ideas(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        return signals
    ideas = signals[signals["score"] >= config.BUY_SCORE_THRESHOLD]
    return ideas.head(config.TOP_N_IDEAS)
