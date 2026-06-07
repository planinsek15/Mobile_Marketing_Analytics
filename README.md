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
| 🥉 Bronze | `raw` | Surovi podatki iz 4 virov, idempotentno naloženi |
| 🥈 Silver | `staging` | Očiščeni, deduplicirani, reconciliation |
| 🥇 Gold | `marts` | Dimenzijski model, metrike rasti |

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
- Python 3.10+
- SQL Server 2019 (dostopen)
- ODBC Driver 18 for SQL Server

### Namestitev
```bash
pip install -r requirements.txt
```

### Pipeline
```bash
# 1. Generiraj vire
python 01_sources/gen_appsflyer.py
python 01_sources/gen_singular.py
python 01_sources/gen_skan.py
python 01_sources/gen_backend.py

# 2. Naloži v raw
python 02_ingestion/load_to_raw.py

# 3. Transformiraj
cd 03_dbt && dbt run && dbt test

# 4. Dashboard (opcijsko)
streamlit run 04_dashboard/streamlit_app.py
```

---

## 📊 Ključne metrike

- **CPI** — Cost Per Install
- **CAC** — Cost per paying user
- **ROAS** — Return on Ad Spend (D7, D30)
- **LTV** — Lifetime Value (napoved iz kohort)
- **Retention** — D1 / D7 / D30
- **ROAS gap** — razlika MMP vs backend (privacy-aware)

---

## 🔍 Diferenciator: Reconciliation

Jedro projekta je **data quality plast** ki primerja:
- MMP (AppsFlyer) prihodek vs backend prihodek
- Označi neskladja nad pragom (5%)
- Obravnava pozne in podvojene dogodke
- SKAN agregati modelirani ločeno (brez user-level joina)

---

*Portfolio projekt | 2026*
