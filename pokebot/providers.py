"""Price providers.

v1 ships PokemonTcgIoProvider (free, raw English singles via TCGplayer/
Cardmarket market prices). The Provider interface exists so graded slabs and
Japanese cards can be added later via PriceCharting without touching the
pipeline — implement fetch() returning the same row dicts.
"""
from __future__ import annotations

import logging
import time
from datetime import date

import requests
import yaml

from . import config

log = logging.getLogger(__name__)

# TCGplayer price variants in preference order — chase cards are usually holos.
# Unlimited before 1st Edition: 1st Ed WOTC prints are a different (much pricier,
# less liquid) asset; pin `variant: 1stEditionHolofoil` in watchlist.yaml if you
# specifically want to track those.
VARIANT_PREFERENCE = [
    "holofoil",
    "unlimitedHolofoil",
    "reverseHolofoil",
    "normal",
    "unlimited",
    "1stEditionHolofoil",
    "1stEdition",
]


def load_watchlist(path=config.WATCHLIST_PATH) -> list[dict]:
    with open(path) as f:
        doc = yaml.safe_load(f)
    return doc["cards"]


class PokemonTcgIoProvider:
    BASE = "https://api.pokemontcg.io/v2/cards/{card_id}"

    def __init__(self, api_key: str = ""):
        self.session = requests.Session()
        if api_key:
            self.session.headers["X-Api-Key"] = api_key

    def fetch_card(self, card_id: str, variant: str | None = None) -> dict | None:
        """Return one snapshot row for a card, or None on failure.

        `variant` pins a specific TCGplayer variant (from watchlist.yaml);
        otherwise VARIANT_PREFERENCE order applies."""
        url = self.BASE.format(card_id=card_id)
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 404:
                    log.warning("card id not found: %s", card_id)
                    return None
                resp.raise_for_status()
                return self._to_row(resp.json()["data"], preferred=variant)
            except (requests.RequestException, KeyError) as exc:
                log.warning("fetch %s attempt %d failed: %s", card_id, attempt + 1, exc)
                time.sleep(2 * (attempt + 1))
        return None

    @staticmethod
    def _to_row(card: dict, preferred: str | None = None) -> dict:
        tcg = (card.get("tcgplayer") or {}).get("prices") or {}
        variant, prices = None, {}
        if preferred:
            if preferred in tcg:
                variant, prices = preferred, tcg[preferred]
            else:
                log.warning(
                    "%s: pinned variant %r not in API response (has %s) — falling back",
                    card["id"], preferred, list(tcg),
                )
        if variant is None:
            for v in VARIANT_PREFERENCE:
                if v in tcg:
                    variant, prices = v, tcg[v]
                    break
        if variant is None and tcg:  # unknown variant name — take the first
            variant, prices = next(iter(tcg.items()))

        cm = (card.get("cardmarket") or {}).get("prices") or {}
        return {
            "date": date.today().isoformat(),
            "card_id": card["id"],
            "name": card.get("name", ""),
            "set_name": (card.get("set") or {}).get("name", ""),
            "variant": variant or "",
            "market": prices.get("market"),      # USD, TCGplayer market price
            "low": prices.get("low"),
            "mid": prices.get("mid"),
            "high": prices.get("high"),
            "cm_trend": cm.get("trendPrice"),    # EUR, Cardmarket trend
            "cm_avg30": cm.get("avg30"),
        }

    def fetch(self, watchlist: list[dict]) -> list[dict]:
        rows = []
        for entry in watchlist:
            row = self.fetch_card(entry["id"], variant=entry.get("variant"))
            if row is not None:
                rows.append(row)
            time.sleep(0.5)  # be polite to the free API
        return rows
