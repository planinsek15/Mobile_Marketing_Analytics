#!/usr/bin/env python3
"""Generator vira 2: Singular cost/reporting (dnevni agregat porabe).

Singular je agregator marketinških stroškov, ki dnevno poroča porabo po
omrežjih (network-reported), neodvisno od MMP atribucije. Zrno:
    date × source (kanal) × campaign × country

Namerno se installi/poraba *ne* ujemajo natanko z AppsFlyer atribucijo —
to je realnost (network-reported vs MMP-attributed) in vir reconciliation
neskladij. Samo plačani kanali (organski nima porabe).

Zagon:  python3 01_sources/gen_singular.py
Izhod:  data/singular_cost.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import random

import _common as c

# Tipičen dnevni obseg prikazov na (kanal, kampanja, država) — groba lestvica.
_CHANNEL_SCALE: dict[str, float] = {
    "Meta": 1.0,
    "Google Ads": 0.9,
    "TikTok": 0.6,
    "Apple Search Ads": 0.4,
}


def generate(seed: int = c.SEED) -> list[dict]:
    """Zgenerira dnevne agregirane zapise porabe za vse plačane kanale.

    Returns:
        Seznam slovarjev — vrstice Singular tabele.
    """
    rng = random.Random(seed + 1)  # drug seed kot AppsFlyer
    rows: list[dict] = []

    for day in range(c.WINDOW_DAYS):
        date = c.WINDOW_START + dt.timedelta(days=day)
        for channel in c.PAID_CHANNELS:
            scale = _CHANNEL_SCALE[channel]
            for campaign in c.CAMPAIGNS[channel]:
                for country in c.COUNTRIES:
                    # Nekatere kombinacije (kampanja×država) so neaktivne.
                    if rng.random() < 0.25:
                        continue
                    impressions = int(rng.uniform(2000, 40000) * scale)
                    if impressions < 200:
                        continue
                    # CTR 0.8–4 %.
                    ctr = rng.uniform(0.008, 0.04)
                    clicks = max(1, int(impressions * ctr))
                    # Conversion rate klik→install 3–12 %.
                    cvr = rng.uniform(0.03, 0.12)
                    installs = int(clicks * cvr)
                    # CPI 2–8 EUR → cost iz installov; če 0 installov, le poraba na klike.
                    cpi = rng.uniform(2.0, 8.0)
                    if installs > 0:
                        cost = installs * cpi
                    else:
                        cost = clicks * rng.uniform(0.10, 0.40)
                    rows.append({
                        "date": date.isoformat(),
                        "source": channel,
                        "campaign": campaign,
                        "country": country,
                        "impressions": impressions,
                        "clicks": clicks,
                        "installs": installs,
                        "cost": round(cost, 2),
                    })
    return rows


def write_csv(rows: list[dict], path: str = c.SINGULAR_CSV) -> None:
    """Zapiše zapise v CSV (idempotentno — prepiše obstoječo datoteko)."""
    c.ensure_data_dir()
    fieldnames = ["date", "source", "campaign", "country",
                  "impressions", "clicks", "installs", "cost"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = generate()
    write_csv(rows)
    total_cost = sum(r["cost"] for r in rows)
    total_inst = sum(r["installs"] for r in rows)
    print(f"Singular: {len(rows)} vrstic, skupna poraba {total_cost:,.0f} EUR, "
          f"{total_inst} network-reported installov")
    print(f"  → {c.SINGULAR_CSV}")


if __name__ == "__main__":
    main()
