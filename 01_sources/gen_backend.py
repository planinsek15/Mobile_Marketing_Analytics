#!/usr/bin/env python3
"""Generator vira 4: Backend / in-app dogodki — VIR RESNICE z NAMERNIMI NESKLADJI.

Backend je lasten dogodkovni vir aplikacije (user_id, event, revenue, event_time).
Je "vir resnice" za prihodek, a se NE ujema popolnoma z MMP (AppsFlyer) — prav
ta neskladja so jedro reconciliation plasti projekta.

Vgrajena neskladja (glede na AppsFlyer revenue dogodke):
  * ~5 %  POZNIH dogodkov   — event_time precej za installom (čez atribucijsko okno)
  * ~3 %  PODVOJENIH        — isti user_id + event + event_time (idempotenčni test)
  * ~10 % NEATRIBUIRANIH    — user_id, ki ga v AppsFlyer sploh ni (organski/ITP/ATT)
  * REVENUE se ~15 % razlikuje od AppsFlyer (davki, vračila, drugačno priznavanje)

Backend uporablja LASTNO taksonomijo dogodkov (purchase/subscribe brez 'af_'
predpone) — reconciliation mora znati preslikati af_purchase ↔ purchase.

Najprej zaženi gen_appsflyer.py (backend se nasloni nanj).

Zagon:  python3 01_sources/gen_backend.py
Izhod:  data/backend_events.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import random
import uuid

import _common as c

# Preslikava AppsFlyer event_name → backend (lastna taksonomija).
_EVENT_MAP: dict[str, str] = {"af_purchase": "purchase", "af_subscribe": "subscribe"}


def _load_af_revenue_events() -> list[dict]:
    """Prebere AppsFlyer revenue dogodke (za povezavo backend ↔ MMP)."""
    if not os.path.exists(c.APPSFLYER_CSV):
        raise FileNotFoundError(
            f"Manjka {c.APPSFLYER_CSV}. Najprej zaženi gen_appsflyer.py.")
    events: list[dict] = []
    with open(c.APPSFLYER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["event_name"] in _EVENT_MAP and row["event_revenue"]:
                events.append(row)
    return events


def _revenue_factor(rng: random.Random) -> float:
    """Faktor odstopanja backend prihodka od MMP (~15 % povprečno neskladje).

    Backend pogosto prizna nekoliko *manj* (neto po davku/vračilih), občasno več.
    """
    factor = rng.gauss(0.90, 0.15)
    return max(0.40, min(1.60, factor))


def generate(seed: int = c.SEED) -> list[dict]:
    """Zgenerira backend dogodke z vgrajenimi neskladji.

    Returns:
        Seznam slovarjev — vrstice backend tabele.
    """
    rng = random.Random(seed + 3)
    af_events = _load_af_revenue_events()
    rows: list[dict] = []

    for ev in af_events:
        af_time = dt.datetime.fromisoformat(ev["event_time"])
        install_time = dt.datetime.fromisoformat(ev["install_time"])
        event = _EVENT_MAP[ev["event_name"]]
        revenue = round(float(ev["event_revenue"]) * _revenue_factor(rng), 2)

        # ~5 % poznih dogodkov: event_time skoči 5–25 dni naprej (pogosto čez okno).
        if rng.random() < 0.05:
            event_time = af_time + dt.timedelta(
                days=rng.randint(5, 25), hours=rng.randint(0, 23))
        else:
            # Sicer manjši zamik glede na MMP zabeleženi čas (sekunde/minute).
            event_time = af_time + dt.timedelta(seconds=rng.randint(-120, 600))
            if event_time < install_time:
                event_time = install_time + dt.timedelta(minutes=1)

        rows.append({
            "user_id": ev["appsflyer_id"],
            "event": event,
            "revenue": revenue,
            "event_time": event_time.isoformat(sep=" ", timespec="seconds"),
        })

    # ~3 % PODVOJENIH dogodkov (popoln duplikat — isti user_id+event+time+revenue).
    n_dupes = int(len(rows) * 0.03)
    for _ in range(n_dupes):
        rows.append(dict(rng.choice(rows[:len(rows)])))

    # ~10 % NEATRIBUIRANIH dogodkov — uporabniki, ki jih v AppsFlyer ni.
    n_unattr = int(len(rows) * 0.10)
    for _ in range(n_unattr):
        unknown_user = str(uuid.uuid4())
        event = rng.choices(["purchase", "subscribe"], weights=[0.7, 0.3], k=1)[0]
        revenue = round(rng.choice(c.PRICE_POINTS) * _revenue_factor(rng), 2)
        day_offset = rng.randint(0, c.WINDOW_DAYS + 10)
        event_time = dt.datetime.combine(
            c.WINDOW_START + dt.timedelta(days=day_offset),
            dt.time(rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)),
        )
        rows.append({
            "user_id": unknown_user,
            "event": event,
            "revenue": revenue,
            "event_time": event_time.isoformat(sep=" ", timespec="seconds"),
        })

    rng.shuffle(rows)
    return rows


def write_csv(rows: list[dict], path: str = c.BACKEND_CSV) -> None:
    """Zapiše zapise v CSV (idempotentno — prepiše obstoječo datoteko)."""
    c.ensure_data_dir()
    fieldnames = ["user_id", "event", "revenue", "event_time"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = generate()
    write_csv(rows)
    print(f"Backend: {len(rows)} dogodkov (z vgrajenimi neskladji: "
          f"~5 % poznih, ~3 % podvojenih, ~10 % neatribuiranih, ~15 % revenue gap)")
    print(f"  → {c.BACKEND_CSV}")


if __name__ == "__main__":
    main()
