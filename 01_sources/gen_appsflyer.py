#!/usr/bin/env python3
"""Generator vira 1: AppsFlyer raw (install + in-app event zapisi).

AppsFlyer je MMP (mobile measurement partner), ki atribuira installe in dogodke
na ravni naprave (appsflyer_id). Generiramo dve vrsti zapisov v isti tabeli
(kot v realnem AppsFlyer raw exportu):

  * install  — en zapis ob namestitvi (event_name = 'install', brez prihodka)
  * in-app   — dogodki s prihodkom (af_purchase / af_subscribe)

appsflyer_id se kasneje uporabi kot join ključ proti backend.user_id.

Zagon:  python3 01_sources/gen_appsflyer.py [stevilo_uporabnikov]
Izhod:  data/appsflyer_raw.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import random
import sys
import uuid

import _common as c


def _attribution_touch(rng: random.Random, install_time: dt.datetime,
                       channel: str) -> tuple[str | None, str | None]:
    """Vrne (attributed_touch_time, attributed_touch_type) za dani kanal.

    Organski installi nimajo atribucijskega dotika. Plačani kanali imajo
    click ali impression nekaj minut do nekaj ur pred installom.
    """
    if channel == "organic":
        return None, None
    touch_type = "click" if rng.random() < 0.8 else "impression"
    # Dotik je pred installom (CTIT — click-to-install time).
    delta_min = rng.randint(2, 60 * 12)
    touch_time = install_time - dt.timedelta(minutes=delta_min)
    return touch_time.isoformat(sep=" ", timespec="seconds"), touch_type


def generate(n_users: int = 3500, seed: int = c.SEED) -> list[dict]:
    """Zgenerira seznam AppsFlyer zapisov (installi + revenue dogodki).

    Args:
        n_users: število unikatnih uporabnikov/naprav (installov).
        seed: random seme za ponovljivost.

    Returns:
        Seznam slovarjev — vsak je ena vrstica AppsFlyer raw tabele.
    """
    rng = random.Random(seed)
    rows: list[dict] = []

    channels = list(c.CHANNEL_WEIGHTS.keys())
    channel_w = list(c.CHANNEL_WEIGHTS.values())

    for _ in range(n_users):
        af_id = str(uuid.uuid4())
        channel = rng.choices(channels, weights=channel_w, k=1)[0]
        campaign = rng.choice(c.CAMPAIGNS[channel])
        platform = c.platform_for_channel(rng, channel)
        country = rng.choices(c.COUNTRIES, weights=c.COUNTRY_WEIGHTS, k=1)[0]

        # Install znotraj 30-dnevnega okna ob naključni uri.
        day_offset = rng.randint(0, c.WINDOW_DAYS - 1)
        install_dtm = dt.datetime.combine(
            c.WINDOW_START + dt.timedelta(days=day_offset),
            dt.time(rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)),
        )
        touch_time, touch_type = _attribution_touch(rng, install_dtm, channel)

        # adset / ad sta None za organski promet.
        if channel == "organic":
            af_adset = af_ad = None
        else:
            af_adset = f"{campaign}_adset_{rng.randint(1, 4)}"
            af_ad = f"{campaign}_ad_{rng.randint(1, 6)}"

        base = {
            "appsflyer_id": af_id,
            "media_source": channel,
            "campaign": campaign,
            "af_adset": af_adset,
            "af_ad": af_ad,
            "install_time": install_dtm.isoformat(sep=" ", timespec="seconds"),
            "attributed_touch_time": touch_time,
            "attributed_touch_type": touch_type,
            "country_code": country,
            "platform": platform,
        }

        # 1) Install zapis.
        rows.append({**base, "event_name": "install", "event_revenue": None})

        # 2) Revenue dogodki — ~35 % uporabnikov je plačnikov (1–3 dogodki).
        if rng.random() < 0.35:
            n_events = rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1], k=1)[0]
            for _ in range(n_events):
                event_name = rng.choices(c.REVENUE_EVENTS, weights=[0.75, 0.25], k=1)[0]
                revenue = rng.choice(c.PRICE_POINTS)
                # Dogodek nastopi 0–20 dni po installu.
                ev_dtm = install_dtm + dt.timedelta(
                    days=rng.randint(0, 20),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )
                rows.append({
                    **base,
                    "event_name": event_name,
                    "event_revenue": round(revenue, 2),
                    # Pri dogodkih AppsFlyer ohrani install/touch atribucijo,
                    # 'event_time' nosi sam install_time stolpec ni — uporabimo
                    # poseben stolpec spodaj prek event_time.
                    "install_time": install_dtm.isoformat(sep=" ", timespec="seconds"),
                    "attributed_touch_time": touch_time,
                    "event_time": ev_dtm.isoformat(sep=" ", timespec="seconds"),
                })

    return rows


def write_csv(rows: list[dict], path: str = c.APPSFLYER_CSV) -> None:
    """Zapiše zapise v CSV (idempotentno — prepiše obstoječo datoteko)."""
    c.ensure_data_dir()
    fieldnames = [
        "appsflyer_id", "media_source", "campaign", "af_adset", "af_ad",
        "install_time", "attributed_touch_time", "attributed_touch_type",
        "event_name", "event_revenue", "event_time", "country_code", "platform",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fieldnames})


def main() -> None:
    n_users = int(sys.argv[1]) if len(sys.argv) > 1 else 3500
    rows = generate(n_users=n_users)
    write_csv(rows)
    installs = sum(1 for r in rows if r["event_name"] == "install")
    events = len(rows) - installs
    print(f"AppsFlyer: {len(rows)} vrstic  ({installs} installov + {events} revenue dogodkov)")
    print(f"  → {c.APPSFLYER_CSV}")


if __name__ == "__main__":
    main()
