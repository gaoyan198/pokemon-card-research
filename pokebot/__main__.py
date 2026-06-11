"""CLI entry point.

  python -m pokebot run       # fetch -> store -> signals -> send Telegram digest
  python -m pokebot dry-run   # same pipeline but print the digest instead of sending
  python -m pokebot validate  # check every watchlist id resolves on the API
"""
from __future__ import annotations

import argparse
import logging
import sys

from . import config, digest, providers, signals, store, telegram

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pokebot")


def _load_dotenv() -> None:
    """Tiny .env loader for local runs — no extra dependency."""
    import os
    env_path = config.REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
    # re-read config values that were captured at import time
    config.POKEMONTCG_API_KEY = os.environ.get("POKEMONTCG_API_KEY", "")
    config.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    config.TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def cmd_validate() -> int:
    watchlist = providers.load_watchlist()
    provider = providers.PokemonTcgIoProvider(config.POKEMONTCG_API_KEY)
    bad = []
    for entry in watchlist:
        row = provider.fetch_card(entry["id"], variant=entry.get("variant"))
        if row is None:
            bad.append(entry["id"])
            print(f"  ✗ {entry['id']}  ({entry.get('note', '')})")
        else:
            price = row["market"] if row["market"] is not None else row["cm_trend"]
            print(f"  ✓ {entry['id']:<18} {row['name']:<24} {row['variant']:<20} ${price or 'n/a'}")
    if bad:
        print(f"\n{len(bad)} invalid id(s) — fix watchlist.yaml: {bad}")
        return 1
    print(f"\nAll {len(watchlist)} ids valid.")
    return 0


def cmd_run(send: bool) -> int:
    watchlist = providers.load_watchlist()
    provider = providers.PokemonTcgIoProvider(config.POKEMONTCG_API_KEY)
    rows = provider.fetch(watchlist)
    if not rows:
        log.error("no price data fetched — aborting (history untouched)")
        return 1
    log.info("fetched %d/%d cards", len(rows), len(watchlist))

    history = store.append_snapshot(rows)
    idx = signals.build_index(history)
    sigs = signals.card_signals(history)
    ideas = signals.buy_ideas(sigs)
    text = digest.format_digest(idx, sigs, ideas)

    if send:
        ok = telegram.send_message(text)
        return 0 if ok else 1
    print("\n----- digest (not sent) -----\n")
    print(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="pokebot")
    parser.add_argument("command", choices=["run", "dry-run", "validate"])
    args = parser.parse_args()
    _load_dotenv()
    if args.command == "validate":
        return cmd_validate()
    return cmd_run(send=(args.command == "run"))


if __name__ == "__main__":
    sys.exit(main())
