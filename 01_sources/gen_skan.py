#!/usr/bin/env python3
"""Generator vira 3: SKAdNetwork (SKAN) postbacki — iOS realnost zasebnosti.

SKAN je Applov privacy-safe atribucijski okvir: omrežja prejmejo *agregirane*
postbacke brez user/device ID-ja, zato join na ravni uporabnika NI mogoč.
Zrno postbacka:
    ad_network_id × source_identifier (campaign) × conversion_value × seq_index

Posebnosti, ki jih modeliramo:
  * samo iOS,
  * conversion_value 0–63 (6-bitni) ali NULL,
  * postback_sequence_index 0–2 (tri časovna okna),
  * redownload (bool),
  * CROWD ANONYMITY: pri majhnih kampanjah Apple zadrži conversion_value
    (postane NULL), ker je premalo installov za k-anonimnost.

SKAN se nasloni na dejanske iOS plačane installe iz AppsFlyer, da so
kampanjske porazdelitve realne. Zato najprej zaženi gen_appsflyer.py.

Zagon:  python3 01_sources/gen_skan.py
Izhod:  data/skan_postbacks.csv
"""
from __future__ import annotations

import csv
import os
import random
from collections import Counter

import _common as c

# Preslikava kanala v SKAdNetwork ID (poenostavljeno, a v realnem formatu).
_AD_NETWORK_ID: dict[str, str] = {
    "Meta": "v9wttpbfk9.skadnetwork",
    "Google Ads": "cstr6suwn9.skadnetwork",
    "TikTok": "238da6jt44.skadnetwork",
    "Apple Search Ads": "com.apple.AppStore",
}

# Apple prag privatnosti: kampanje z manj kot toliko postbacki so "majhne".
_PRIVACY_THRESHOLD = 15


def _load_ios_paid_campaigns() -> Counter:
    """Prebere AppsFlyer CSV in prešteje iOS plačane installe po (kanal, kampanja).

    Returns:
        Counter s ključi (media_source, campaign) → število iOS installov.
    """
    if not os.path.exists(c.APPSFLYER_CSV):
        raise FileNotFoundError(
            f"Manjka {c.APPSFLYER_CSV}. Najprej zaženi gen_appsflyer.py.")
    counts: Counter = Counter()
    with open(c.APPSFLYER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["event_name"] == "install"
                    and row["platform"] == "ios"
                    and row["media_source"] in c.PAID_CHANNELS):
                counts[(row["media_source"], row["campaign"])] += 1
    return counts


def _conversion_value(rng: random.Random) -> int:
    """Vrne SKAN conversion_value (0–63) z realistično porazdelitvijo.

    Večina installov ne konvertira (cv=0); manjšina ima nizke/srednje/visoke
    vrednosti, ki kodirajo prihodek ali angažma.
    """
    r = rng.random()
    if r < 0.55:
        return 0                       # ni dogodka po installu
    if r < 0.80:
        return rng.randint(1, 15)      # nizka vrednost (npr. registracija)
    if r < 0.95:
        return rng.randint(16, 39)     # srednja (npr. prvi nakup)
    return rng.randint(40, 63)         # visoka (npr. naročnina)


def generate(seed: int = c.SEED) -> list[dict]:
    """Zgenerira agregirane SKAN postback zapise.

    Returns:
        Seznam slovarjev — vrstice SKAN tabele.
    """
    rng = random.Random(seed + 2)
    install_counts = _load_ios_paid_campaigns()
    rows: list[dict] = []

    for (channel, campaign), n_installs in install_counts.items():
        network = _AD_NETWORK_ID[channel]
        is_small = n_installs < _PRIVACY_THRESHOLD
        # Crowd anonymity: vse majhne kampanje (pod pragom) + ~20 % ostalih
        # dobijo zadržan (NULL) conversion_value — Apple ne razkrije vrednosti,
        # kadar je premalo installov za k-anonimnost.
        crowd_anon = is_small or (rng.random() < 0.20)
        # Vsak iOS install proži ~1 postback (del tudi 2. ali 3. okno).
        for _ in range(n_installs):
            seq = rng.choices([0, 1, 2], weights=[0.7, 0.2, 0.1], k=1)[0]
            redownload = rng.random() < 0.07
            if crowd_anon:
                cv = None
            else:
                cv = _conversion_value(rng)
            rows.append({
                "ad_network_id": network,
                "source_identifier": campaign,
                "conversion_value": cv,
                "postback_sequence_index": seq,
                "redownload": redownload,
            })
    return rows


def write_csv(rows: list[dict], path: str = c.SKAN_CSV) -> None:
    """Zapiše zapise v CSV (idempotentno — prepiše obstoječo datoteko)."""
    c.ensure_data_dir()
    fieldnames = ["ad_network_id", "source_identifier", "conversion_value",
                  "postback_sequence_index", "redownload"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            out = dict(r)
            out["redownload"] = "1" if r["redownload"] else "0"
            if r["conversion_value"] is None:
                out["conversion_value"] = ""  # NULL (crowd anonymity)
            writer.writerow(out)


def main() -> None:
    rows = generate()
    write_csv(rows)
    null_cv = sum(1 for r in rows if r["conversion_value"] is None)
    print(f"SKAN: {len(rows)} postbackov, {null_cv} z NULL conversion_value "
          f"(crowd anonymity, {100*null_cv/max(len(rows),1):.1f} %)")
    print(f"  → {c.SKAN_CSV}")


if __name__ == "__main__":
    main()
