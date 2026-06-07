# Projektno poročilo — Mobile Marketing Analytics Pipeline

End-to-end podatkovni pipeline za mobilno marketinško analitiko: 4 simulirani viri →
SQL Server `raw` → dbt `staging`/`reconciliation`/`marts` → metrike rasti in privacy plast.
Spodaj je opis vsake faze z rezultati zadnjega zagona.

---

## Faza 0 — Priprava okolja

- Ustvarjena baza **MMP** (preimenovana iz MMA) v Docker containerju `pim-sqlserver`
  (SQL Server 2019) s shemami `raw`, `staging`, `marts`.
- **Izziv okolja:** sistem teče na **Python 3.14** brez root pravic. Pinani stari paketi
  (numpy 2.1, pandas 2.2, dbt 1.8, pyodbc 5.2) nimajo wheel-ov za 3.14 → uporabljene novejše
  verzije (pandas 3.0, dbt-core 1.11 / dbt-sqlserver 1.9.2, pyodbc 5.3). `mashumaro` nadgrajen
  na 3.22 (sicer dbt na 3.14 crasha pri uvozu).
- **ODBC brez sudo:** unixODBC + Microsoft ODBC Driver 18 razpakiran lokalno iz `.deb`-ov v
  `~/.local/odbc`; aktivira ga `source env.sh` (nastavi `LD_LIBRARY_PATH`, `ODBCSYSINI`, `MMP_*`).
- Zaklenjene verzije v `requirements.lock.txt`.

## Faza 1 — Simulacija 4 virov (`01_sources/`)

Vsi generatorji uporabljajo skupni `_common.py` (deljene dimenzije + join logika), fiksni seed.

| Vir | Datoteka | Vrstic | Opis |
|-----|----------|-------:|------|
| AppsFlyer | `appsflyer_raw.csv` | 5.340 | install + revenue dogodki, `appsflyer_id` kot join ključ |
| Singular | `singular_cost.csv` | 1.154 | dnevni agregat porabe, CPI 2–8 € |
| SKAN | `skan_postbacks.csv` | 1.355 | iOS postbacki, cv 0–63, 470 NULL (crowd anonymity) |
| Backend | `backend_events.csv` | 2.084 | vir resnice z **namernimi neskladji** |

**Namerna neskladja v backendu** (jedro projekta): ~5 % poznih dogodkov, ~3 % popolnih dvojnikov,
~9 % neatribuiranih (user brez AppsFlyer zapisa), revenue ~15 % drugačen od MMP.

## Faza 2 — Ingestion v raw (`02_ingestion/load_to_raw.py`)

- pyodbc bulk insert (`fast_executemany`) v 4 raw tabele z eksplicitnim DDL.
- **Idempotentno** (TRUNCATE + INSERT — ponoven zagon ne podvoji), stolpec `_loaded_at`,
  datumski indeksi (logična particija). Potrjeno: ponoven zagon → enako število vrstic.

## Faza 3 — dbt reconciliation + kakovost (JEDRO)

- **Staging (5 modelov):** standardizacija kanala (`standardize_channel` macro), SKAN ohrani
  NULL cv, **backend deduplikacija** (`ROW_NUMBER` po user_id+event+time) + obogatitev z
  atribucijo + `is_late_event` flag.
- **Reconciliation (2 modela):**
  - `rec_revenue_discrepancy` — MMP vs backend prihodek po kanalu × dan, delta %, flag >5 %.
    → **206 / 249** vrstic z neskladjem; MMP precenjuje za ~9 % skupno.
  - `rec_attribution_gap` — neatribuiran prihodek: **189 dogodkov, 7.266 €**.
- **Testi (custom):** cv izven 0–63, negativni revenue, preostali dvojniki, poraba brez
  installov (warn), installi brez porabe (warn) + `not_null`/`unique`/`relationships`/
  `accepted_values` + **source freshness**.

## Faza 4 — Dimenzijski model (`marts`)

- **Dimenzije:** `dim_date` (tally iz `sys.all_objects` — brez prepovedanih funkcij),
  `dim_channel`, `dim_campaign`, `dim_geo`.
- **Dejstva:** `fct_installs` (device-grain), `fct_events` (event-grain), `fct_spend` (agregat).
- **`mart_marketing_unified`** — FULL OUTER JOIN poraba + installi + prihodek po
  channel × campaign × geo × date (1.997 vrstic).
- **`mart_retention`** — D1/D7/D30 po akvizicijskih kohortah (D1 ~34 %, D7 ~27 %, monoton).
- Relationships testi dejstva → dimenzije (vsi PASS).

## Faza 5 — Metrike rasti (`mart_growth_metrics`)

Po kanalu × kampanji: **CPI, CAC, ROAS D7/D30** (kohortno), **ARPU/ARPPU, naivna LTV D90**,
ter **blended (deterministični) vs SKAN-only** signali ob strani.

| Kanal | Poraba | CPI | CAC | ROAS D30 |
|-------|-------:|----:|----:|---------:|
| Google Ads | 64.285 € | 74,92 | 221,67 | 0,25 |
| Meta | 59.165 € | 61,50 | 176,61 | 0,31 |
| TikTok | 26.560 € | 57,74 | 146,74 | 0,34 |
| Apple Search Ads | 16.876 € | 50,68 | 141,82 | 0,39 |

## Faza 6 — Privacy-aware plast (`mart_privacy_roas_gap`)

- Tri perspektive ene kampanje: **MMP vs backend vs SKAN**.
- **ROAS gap** = MMP ROAS − backend potrjeni ROAS; MMP precenjuje prihodek za **~10–14 %**.
- `has_crowd_anonymity` flag — **4 kampanje** s 100 % NULL `conversion_value`.
- Dokument `00_docs/Astra_izboljsave.md`: event taxonomy, SKAN cv shema, reconciliation, alerting.

## Faza 7 (opcijsko) — Streamlit dashboard (`04_dashboard/`)

3 vizualizacije nad `marts`: najboljši kanali po ROAS, MMP vs backend razhajanje,
SKAN vs deterministična pokritost. Preverjeno: zažene se (HTTP 200), poizvedbe OK.

---

## Skupni rezultat

- **18 dbt modelov**, **60 testov PASS** / 1 WARN (po dizajnu) / 0 ERROR, freshness 4 PASS.
- Celoten pipeline ponovljiv (`generate_all.py` → `load_to_raw.py` → `dbt run/test`).
- Vsa 4 namerna neskladja zaznana in kvantificirana v reconciliation plasti.

## Možne nadgradnje

- Airflow DAG za dnevno orkestracijo (`simulacija → ingestion → dbt → alert`).
- Incremental modeli + snapshots za zgodovinske kohorte.
- LTV napoved z dejanskim modelom (trenutno naivni faktor).
- CI: `dbt build` + linting event sheme ob vsakem PR.
