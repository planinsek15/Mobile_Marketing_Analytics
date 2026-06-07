# 📱 Mobile Marketing Analytics Pipeline

End-to-end podatkovna platforma, ki združi atribucijske podatke iz MMP-jev (AppsFlyer + Singular), jih uskladi z backend dogodki in odgovori na vprašanje: **kateri kanali, kampanje in segmenti res prinašajo dobičkonosno rast** — ob upoštevanju realnosti iOS zasebnosti (SKAN).

> Portfolio projekt za vlogo Data Engineer z mobile app analitiko.

---

## 🎯 Kaj projekt dokazuje

1. **Mobile app tracking infrastructure** — pipeline od virov do skladišča
2. **Kakovost podatkov** med appom, MMP-ji in backendom — reconciliation + data quality plast
3. **Marketinški vpogled** — mart z metrikami ROAS / LTV / retention

---

## 🏗️ Arhitektura

```
AppsFlyer raw   ─┐
Singular cost   ─┤
SKAN postbacks  ─┼─► RAW (bronze) ─► STAGING/RECONCILE (silver) ─► MARTS (gold) ─► Dashboard
Backend events  ─┘        │                    │                       │
                     ingestion        data quality + reconciliation   metrike: ROAS, LTV,
                     (Python)         (dbt testi, discrepancy report)  retention, CAC, CPI
```

### Medallion arhitektura
| Plast | Shema | Vsebina |
|-------|-------|---------|
| 🥉 Bronze | `raw` | Surovi podatki iz 4 virov, idempotentno naloženi (`_loaded_at`) |
| 🥈 Silver | `staging` | Očiščeni, standardizirani, **deduplicirani** (backend) |
| 🥇 Gold | `marts` | Reconciliation, dimenzijski model, metrike rasti, privacy plast |

---

## 🛠️ Tehnološki sklad

| Orodje | Namen |
|--------|-------|
| **Python** (Faker) | Simulacija 4 virov + ingestion |
| **SQL Server 2019** | Podatkovno skladišče (raw/staging/marts) |
| **dbt** (dbt-sqlserver) | Transformacije, modeliranje, testi kakovosti |
| **Streamlit** | Dashboard (opcijsko) |
| **Airflow** | Orkestracija (opcijsko) |

---

## 📂 Struktura projekta

```
Mobile_Marketing_Analytics/
├── 00_docs/              Dokumentacija + Astra izboljšave dokument
├── 01_sources/          Faza 1: simulacija 4 virov (Python)
├── 02_ingestion/        Faza 2: nalaganje v SQL Server raw shemo
├── 03_dbt/              Faze 3-5: transformacije, reconciliation, marts
│   └── models/
│       ├── staging/         (silver)
│       ├── reconciliation/  (data quality)
│       └── marts/           (gold)
├── 04_dashboard/        Faza 7: Streamlit dashboard
└── data/                Začasne CSV datoteke (git ignorira)
```

---

## 🚀 Zagon

### Predpogoji
- Python 3.10+ (razvito in testirano na **Python 3.14**)
- SQL Server 2019 — Docker container `pim-sqlserver`, baza **MMP**
- ODBC Driver 18 for SQL Server

> **Opomba o okolju:** to okolje teče na Python 3.14 brez root pravic. Pinani stari
> paketi nimajo wheel-ov za 3.14, zato `requirements.txt` uporablja ohlapne verzije
> (dejanske zaklenjene so v `requirements.lock.txt`). unixODBC + ODBC Driver 18 sta
> razpakirana lokalno v `~/.local/odbc` (brez sudo); aktivira ju `source env.sh`.

### Namestitev
```bash
pip install -r requirements.txt --break-system-packages
source env.sh        # aktivira lokalni ODBC + nastavi MMP_* spremenljivke
```

### Pipeline (od začetka do konca)
```bash
# 0. Baza + sheme (enkratno)
docker exec pim-sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa \
  -P 'PimSql2024!' -C -Q "IF DB_ID('MMP') IS NULL CREATE DATABASE MMP"

# 1. Generiraj vse 4 vire (fiksni seed → ponovljivo)
python 01_sources/generate_all.py

# 2. Naloži v raw (idempotentno)
python 02_ingestion/load_to_raw.py

# 3. Transformiraj + testi kakovosti
cd 03_dbt && export DBT_PROFILES_DIR="$PWD"
dbt run && dbt test && dbt source freshness

# 4. Dashboard (opcijsko)
cd .. && streamlit run 04_dashboard/streamlit_app.py
```

---

## 📊 Rezultati (zadnji zagon)

| Plast | Rezultat |
|-------|----------|
| **Viri** | AppsFlyer 5.340 · Singular 1.154 · SKAN 1.355 · Backend 2.084 vrstic |
| **dbt** | 18 modelov, **60 testov PASS** / 1 WARN (po dizajnu) / 0 ERROR, freshness 4 PASS |
| **Reconciliation** | 206 / 249 kanal×dan vrstic z neskladjem > 5 % |
| **Revenue gap** | MMP precenjuje prihodek za **~10–14 %** glede na backend (vir resnice) |
| **Attribution gap** | 189 backend dogodkov (7.266 €) brez MMP atribucije |
| **Crowd anonymity** | 4 kampanje s 100 % NULL `conversion_value` (SKAN privacy) |

### Ključne metrike (po kanalu)
| Kanal | Poraba | CPI | CAC | ROAS D30 |
|-------|-------:|----:|----:|---------:|
| Google Ads | 64.285 € | 74,92 € | 221,67 € | 0,25 |
| Meta | 59.165 € | 61,50 € | 176,61 € | 0,31 |
| TikTok | 26.560 € | 57,74 € | 146,74 € | 0,34 |
| Apple Search Ads | 16.876 € | 50,68 € | 141,82 € | 0,39 |
| organic | 0 € | — | — | — |

> Metrike: **CPI** (cost/install), **CAC** (cost/paying user), **ROAS** D7/D30,
> **LTV** (napoved iz kohort), **Retention** D1/D7/D30, **ROAS gap** (MMP vs backend).

---

## 🔍 Diferenciator: Reconciliation & Privacy

Jedro projekta je **data quality + reconciliation plast** (`03_dbt/models/reconciliation/`
in `mart_privacy_roas_gap`):
- MMP (AppsFlyer) prihodek **vs** backend prihodek po kanalu × dan, z delta % in zastavico (>5 %)
- Deduplikacija backend dogodkov (`ROW_NUMBER`) + obravnava poznih dogodkov (`is_late_event`)
- Attribution gap: backend dogodki brez MMP atribucije (napihnejo ROAS, če jih ignoriramo)
- SKAN agregati modelirani **ločeno** (brez user-level joina); crowd-anonymity (NULL cv) eksplicitno označen
- Tri-perspektivni ROAS: MMP vs backend vs SKAN drug ob drugem

Glej tudi `00_docs/Astra_izboljsave.md` (event taxonomy · SKAN cv shema · reconciliation · alerting)
in `00_docs/PROJEKT_POROCILO.md` (opis vseh faz).

---

*Portfolio projekt | 2026*
