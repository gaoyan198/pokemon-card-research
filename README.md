# pokemon-card-research

Daily Telegram digest of undervalued Pokémon cards, plus a buy-the-dip alert on a
self-built Pokémon card index. Long-horizon thesis: accumulate quality cards when
the asset class dips, the same way you'd buy an equity index drawdown.

## How it works

```
watchlist.yaml ──> pokemontcg.io API ──> data/history.csv (grows daily)
                                              │
                            ┌─────────────────┴──────────────────┐
                            ▼                                    ▼
                   equal-weight card index             per-card signals
                   (dip alerts at -5% / -10%)          (z-score, drawdown, spread)
                            └─────────────────┬──────────────────┘
                                              ▼
                                      Telegram digest, 9am SGT daily
                                      (GitHub Actions cron)
```

- **Index** — each watchlist card normalised to 100 at first observation,
  equal-weighted. Dip alerts fire when the index falls **-5%** ("buy zone") or
  **-10%** ("strong buy zone") from its trailing high.
- **Per-card signals** — once a card has ≥8 days of history: z-score of price vs
  its 30-day mean, and drawdown vs its 90-day high. Before that (cold start):
  how far the live market price sits below TCGplayer's mid price.
- **Buy ideas** — cards scoring ≥0.5 on a normalised [0,1] undervaluation score,
  top 5 in the digest. This is *mean-reversion within cards you already believe in*,
  not fair-value appraisal — curate `watchlist.yaml` accordingly.

> **Cold-start honesty:** the free API has no historical prices, so this repo
> accumulates its own history (committed daily by the Action). Index drawdowns and
> z-scores become meaningful after ~2–4 weeks. Early digests lean on the weaker
> spread signal and say so.

## Setup (one-time, ~10 minutes)

### 1. Create the Telegram bot

1. In Telegram, message **@BotFather** → `/newbot` → pick a name and a username
   (must end in `bot`, e.g. `gy_pokemon_bot`).
2. BotFather replies with a **bot token** like `123456789:AAH...` — save it.
3. Open a chat with your new bot and send it any message (e.g. "hi").
   This is required before the bot can message you.
4. Get your **chat id**: visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   in a browser and read `result[0].message.chat.id` (a number like `5512345678`).

### 2. Get a Pokémon TCG API key (optional but recommended)

Free at <https://dev.pokemontcg.io> — raises the rate limit.

### 3. Push to GitHub and add secrets

```bash
gh repo create pokemon-card-research --private --source . --push
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
gh secret set POKEMONTCG_API_KEY
```

### 4. Test

Trigger the workflow manually: **Actions → daily-digest → Run workflow**, or locally:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in tokens
python -m pokebot validate # confirm every watchlist id resolves
python -m pokebot dry-run  # full pipeline, prints digest instead of sending
python -m pokebot run      # sends to Telegram
```

The cron then runs daily at 09:00 SGT (01:00 UTC) and commits each day's prices to
`data/history.csv`.

## Curating the watchlist

Edit `watchlist.yaml` — ids are `<set-id>-<number>` from
[pokemontcg.io](https://pokemontcg.io). Run `python -m pokebot validate` after any
edit. The index is equal-weight, so every card you add changes the dip signal;
keep it to liquid, high-conviction cards.

## Known limits & upgrade path

| Limitation | Why | Upgrade |
|---|---|---|
| Raw English singles only | Free API has no graded-slab or JP pricing | Add a `PriceChartingProvider` in `pokebot/providers.py` (~US$10/mo, includes PSA/CGC slabs, sealed, JP, **and historical prices** — would also solve cold start) |
| Raw card prices ≠ slab prices | A raw "undervalued" card may be condition-impaired in the listing | Treat signals as *research prompts*, inspect actual listings before buying |
| Mean-reversion, not valuation | A falling price can be a fair repricing (reprints, rotation) | Watchlist curation is the valuation layer — that judgement stays with you |

## Disclaimer

Research tooling, not financial advice. Collectibles are illiquid, spreads are wide
(often 10–15% after fees), and TCGplayer market price is an estimate, not an
executable quote.
