"""Skupne definicije za simulacijo virov (Mobile Marketing Analytics).

Vsi štirje generatorji uvozijo ta modul, da uporabljajo *iste* dimenzije
(kanali, kampanje, države, časovno okno). Le tako je reconciliation med
MMP-ji in backendom smiseln — ključi se morajo ujemati.

Join logika med viri:
    AppsFlyer.appsflyer_id  ==  Backend.user_id   (za atribuirane uporabnike)
    AppsFlyer.media_source  ==  Singular.source   (kanal)
    AppsFlyer.campaign      ==  Singular.campaign / SKAN.source_identifier
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Final

# ── Reproducibilnost ────────────────────────────────────────────────────────
SEED: Final[int] = 42

# ── Časovno okno simulacije ─────────────────────────────────────────────────
# 30-dnevno akvizicijsko okno; dogodki (in pozni dogodki) lahko segajo čez konec.
WINDOW_START: Final[dt.date] = dt.date(2026, 5, 1)
WINDOW_DAYS: Final[int] = 30
WINDOW_END: Final[dt.date] = WINDOW_START + dt.timedelta(days=WINDOW_DAYS - 1)

# ── Kanali (media_source) ───────────────────────────────────────────────────
# organski kanal nima porabe (Singular/SKAN ga ne pokrivata).
PAID_CHANNELS: Final[list[str]] = ["Meta", "Google Ads", "TikTok", "Apple Search Ads"]
ALL_CHANNELS: Final[list[str]] = PAID_CHANNELS + ["organic"]

# Verjetnostna utež dodelitve uporabnika kanalu (organski je velik delež).
CHANNEL_WEIGHTS: Final[dict[str, float]] = {
    "Meta": 0.27,
    "Google Ads": 0.24,
    "TikTok": 0.14,
    "Apple Search Ads": 0.10,
    "organic": 0.25,
}

# ── Kampanje na kanal ───────────────────────────────────────────────────────
CAMPAIGNS: Final[dict[str, list[str]]] = {
    "Meta": ["meta_uac_prospecting", "meta_retargeting", "meta_lookalike_SI"],
    "Google Ads": ["gads_uac_install", "gads_search_brand", "gads_discovery"],
    "TikTok": ["tt_spark_ads", "tt_topview_HR"],
    "Apple Search Ads": ["asa_brand", "asa_generic_keywords"],
    "organic": ["organic"],
}

# ── Geografije ──────────────────────────────────────────────────────────────
COUNTRIES: Final[list[str]] = ["SI", "DE", "AT", "HR", "IT"]
COUNTRY_WEIGHTS: Final[list[float]] = [0.30, 0.25, 0.15, 0.18, 0.12]

# ── Platforme ───────────────────────────────────────────────────────────────
# Apple Search Ads je samo iOS; ostali mešano.
PLATFORMS: Final[list[str]] = ["ios", "android"]

# ── Dogodki in prihodki ─────────────────────────────────────────────────────
REVENUE_EVENTS: Final[list[str]] = ["af_purchase", "af_subscribe"]
# Cenovne točke (EUR) za nakupe in naročnine.
PRICE_POINTS: Final[list[float]] = [4.99, 9.99, 19.99, 49.99, 99.99]

# ── Poti do izhodnih datotek ────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR: Final[str] = os.path.join(_BASE, "data")

APPSFLYER_CSV: Final[str] = os.path.join(DATA_DIR, "appsflyer_raw.csv")
SINGULAR_CSV: Final[str] = os.path.join(DATA_DIR, "singular_cost.csv")
SKAN_CSV: Final[str] = os.path.join(DATA_DIR, "skan_postbacks.csv")
BACKEND_CSV: Final[str] = os.path.join(DATA_DIR, "backend_events.csv")


def ensure_data_dir() -> None:
    """Ustvari mapo data/, če še ne obstaja."""
    os.makedirs(DATA_DIR, exist_ok=True)


def platform_for_channel(rng, channel: str) -> str:
    """Vrne platformo glede na kanal (Apple Search Ads je samo iOS)."""
    if channel == "Apple Search Ads":
        return "ios"
    # iOS delež ~45 % (realno za EU mobilni promet).
    return "ios" if rng.random() < 0.45 else "android"
