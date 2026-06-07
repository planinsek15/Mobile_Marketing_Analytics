#!/usr/bin/env python3
"""Zaženi vse štiri generatorje virov v pravilnem vrstnem redu.

Vrstni red je pomemben: gen_skan in gen_backend bereta AppsFlyer CSV za
povezavo (join), zato mora gen_appsflyer teči prvi.

Zagon:  python3 01_sources/generate_all.py
"""
from __future__ import annotations

import gen_appsflyer
import gen_singular
import gen_skan
import gen_backend


def main() -> None:
    print("── Simulacija virov ──────────────────────────────")
    gen_appsflyer.main()
    gen_singular.main()
    gen_skan.main()
    gen_backend.main()
    print("── Vsi 4 viri zgenerirani v data/ ────────────────")


if __name__ == "__main__":
    main()
