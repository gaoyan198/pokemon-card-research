"""Format the daily Telegram digest (HTML parse mode)."""
from __future__ import annotations

import html

import pandas as pd

from . import config


def _pct(x) -> str:
    return "–" if pd.isna(x) else f"{x:+.1%}"


def _esc(s) -> str:
    return html.escape(str(s))


def format_digest(index: pd.DataFrame, signals: pd.DataFrame, ideas: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("<b>🃏 Pokémon Card Daily</b>")

    # --- Index section ---
    if index.empty or len(index) < 2:
        lines.append("\n<b>Index:</b> building history — index needs a few days of data.")
    else:
        latest = index.iloc[-1]
        lines.append(
            f"\n<b>Index:</b> {latest['level']:.1f} "
            f"(1d {_pct(latest['chg_1d'])}, 7d {_pct(latest['chg_7d'])}, 30d {_pct(latest['chg_30d'])})"
        )
        dd = latest["drawdown"]
        if dd <= config.INDEX_DIP_STRONG:
            lines.append(f"🟢🟢 <b>STRONG BUY ZONE</b> — index {dd:.1%} off its high.")
        elif dd <= config.INDEX_DIP_MILD:
            lines.append(f"🟢 <b>Buy zone</b> — index {dd:.1%} off its high.")
        else:
            lines.append(f"Drawdown from high: {dd:.1%} — no dip signal.")

    # --- Buy ideas ---
    if ideas is None or ideas.empty:
        lines.append("\n<b>Undervalued today:</b> nothing clears the bar. Patience.")
    else:
        lines.append("\n<b>Undervalued today:</b>")
        for _, r in ideas.iterrows():
            detail = (
                f"z {r['zscore']:+.1f}, dd {_pct(r['drawdown'])}"
                if r["regime"] == "history"
                else f"mkt {_pct(r['spread'])} below mid (cold-start signal)"
            )
            lines.append(
                f"• <b>{_esc(r['name'])}</b> ({_esc(r['set_name'])}) — "
                f"${r['price']:,.2f} | score {r['score']:.2f} | {detail}"
            )

    # --- Footnote on data maturity ---
    if not signals.empty:
        cold = (signals["regime"] == "cold-start").sum()
        if cold:
            lines.append(
                f"\n<i>{cold}/{len(signals)} cards still on cold-start signals; "
                f"time-series signals activate after {config.MIN_HISTORY_DAYS} days of history.</i>"
            )
    return "\n".join(lines)
