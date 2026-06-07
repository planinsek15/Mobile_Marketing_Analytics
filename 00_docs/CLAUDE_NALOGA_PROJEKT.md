# 🤖 CLAUDE CODE — MASTER NALOGA: Mobile Marketing Analytics Pipeline

## DOVOLJENJA
Polna avtonomija za: branje/pisanje datotek, bash ukaze, SQL na MMP bazi, pip install, git commit + push.
NE delaj na PIM_test bazi — samo MMP!

## PRED ZAČETKOM — PREBERI
1. `00_docs/Projektna_naloga.md` — celotna naloga
2. `CLAUDE.md` — tehnična pravila
3. `README.md` — arhitektura

## CILJ
Zgradi celoten pipeline: 4 simulirani viri → SQL Server raw → dbt staging/reconciliation/marts → metrike. Faze 1-6 obvezne, 7 opcijska.

---

## FAZA 0 — Priprava okolja

```bash
# Ustvari MMP bazo
docker exec -it pim-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'PimSql2024!' -C \
  -Q "IF DB_ID('MMP') IS NULL CREATE DATABASE MMP"

# Ustvari sheme
docker exec -it pim-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'PimSql2024!' -C -d MMP \
  -Q "IF SCHEMA_ID('raw') IS NULL EXEC('CREATE SCHEMA raw'); IF SCHEMA_ID('staging') IS NULL EXEC('CREATE SCHEMA staging'); IF SCHEMA_ID('marts') IS NULL EXEC('CREATE SCHEMA marts')"

# Namesti Python knjižnice
pip install -r requirements.txt --break-system-packages

# Preveri ODBC driver
odbcinst -q -d
```

Če ODBC driver manjka, namesti:
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
sudo apt update && sudo ACCEPT_EULA=Y apt install -y msodbcsql18
```

Git commit: "Faza 0: priprava okolja, MMP baza, sheme"

---

## FAZA 1 — Simulacija virov

Ustvari 4 Python skripte v `01_sources/`. Vsaka generira CSV v `data/`.

### gen_appsflyer.py
Generiraj ~5000 install/event zapisov. Polja: appsflyer_id (uuid), media_source (Meta/Google Ads/TikTok/Apple Search Ads/organic), campaign, af_adset, af_ad, install_time, attributed_touch_time, attributed_touch_type (click/impression), event_name (af_purchase/af_subscribe/af_login), event_revenue, country_code (SI/DE/AT/HR/IT), platform (ios/android).
→ data/appsflyer_raw.csv

### gen_singular.py
Dnevni agregat po omrežju, 30 dni. Polja: date, source, campaign, country, impressions, clicks, installs, cost.
Cost naj bo realističen (CPI 2-8 EUR).
→ data/singular_cost.csv

### gen_skan.py
SKAN postbacki (samo iOS, agregirani). Polja: ad_network_id, source_identifier (campaign), conversion_value (0-63), postback_sequence_index (0-2), redownload (bool).
Pri ~20% majhnih kampanj nastavi conversion_value = NULL (crowd anonymity).
→ data/skan_postbacks.csv

### gen_backend.py
Backend dogodki — VIR RESNICE z NAMERNIMI NESKLADJI. Polja: user_id, event, revenue, event_time.
Vgradi:
- ~5% poznih dogodkov (event_time precej za install)
- ~3% podvojenih dogodkov (isti user_id+event+time)
- ~10% dogodkov brez atribucije (ni v AppsFlyer)
- revenue ki se ~15% razlikuje od AppsFlyer event_revenue
→ data/backend_events.csv

Vsaka skripta: type hints, docstring, nastavljiv seznam zapisov, fiksni random seed za ponovljivost.

Git commit: "Faza 1: simulacija 4 virov"

---

## FAZA 2 — Ingestion v raw

Ustvari `02_ingestion/load_to_raw.py`:
- Preberi vse 4 CSV iz data/
- Ustvari raw tabele v MMP (raw.appsflyer, raw.singular, raw.skan, raw.backend)
- Naloži idempotentno: dodaj stolpec _loaded_at, in TRUNCATE+INSERT ali MERGE (ne podvoji ob ponovnem zagonu)
- Particioniraj logično po datumu
- Uporabi pyodbc ali sqlalchemy

Po nalaganju izpiši število vrstic v vsaki tabeli.

Git commit: "Faza 2: ingestion v raw shemo"

---

## FAZA 3 — dbt: Reconciliation + kakovost (JEDRO!)

Inicializiraj dbt projekt v `03_dbt/`:
```bash
cd 03_dbt
dbt init mma_dbt  # ali ročno ustvari strukturo
```

Ustvari profiles.yml (NE commitaj — je v .gitignore) za SQL Server:
```yaml
mma_dbt:
  target: dev
  outputs:
    dev:
      type: sqlserver
      driver: 'ODBC Driver 18 for SQL Server'
      server: localhost,1433
      database: MMP
      schema: staging
      user: sa
      password: PimSql2024!
      encrypt: true
      trust_cert: true
```

### Staging modeli (models/staging/)
- stg_appsflyer.sql — očisti, standardiziraj media_source
- stg_singular.sql — agregati porabe
- stg_skan.sql — SKAN, ohrani NULL conversion values
- stg_backend.sql — DEDUPLIKACIJA (ROW_NUMBER po user_id+event+time), označi pozne dogodke

### Reconciliation modeli (models/reconciliation/)
- rec_revenue_discrepancy.sql — dnevni revenue MMP vs backend po kanalu, razlika %, flag če >5%
- rec_attribution_gap.sql — dogodki v backendu brez AppsFlyer atribucije

### dbt testi (schema.yml)
- not_null, unique na ključih
- relationships
- custom testi: poraba brez installov, installi brez porabe, negativni revenue, conversion_value izven 0-63

Zaženi: dbt run && dbt test

Git commit: "Faza 3: reconciliation in data quality testi"

---

## FAZA 4 — dbt: Dimenzijski model (marts)

Ustvari v models/marts/:

### Dimenzije
- dim_date.sql — koledar
- dim_channel.sql — kanali (media_source)
- dim_campaign.sql — kampanje
- dim_geo.sql — države

### Dejstva
- fct_installs.sql — installi po kanalu/kampanji/geo/datumu
- fct_events.sql — dogodki z revenue
- fct_spend.sql — poraba iz Singular

### Unified mart
- mart_marketing_unified.sql — JOIN poraba + installi + prihodek po channel × campaign × geo × date

### Retention
- mart_retention.sql — D1/D7/D30 retention po akvizicijskih kohortah

Git commit: "Faza 4: dimenzijski model in unified mart"

---

## FAZA 5 — Metrike rasti

Ustvari models/marts/mart_growth_metrics.sql z:
- CPI = cost / installs
- CAC = cost / paying_users
- ROAS_D7 = revenue_d7 / cost
- ROAS_D30 = revenue_d30 / cost
- LTV (preprosta napoved iz zgodnjih kohort)
- Blended vs SKAN-only pogled

Git commit: "Faza 5: metrike rasti (ROAS, LTV, CAC, CPI)"

---

## FAZA 6 — Privacy-aware plast

Ustvari models/marts/mart_privacy_roas_gap.sql:
- SKAN agregati ob deterministični atribuciji
- ROAS gap = MMP ROAS - backend potrjen ROAS
- Označi kampanje z NULL conversion (crowd anonymity)

Ustvari `00_docs/Astra_izboljsave.md` (1 stran):
- Event taxonomy predlog
- SKAN conversion value shema
- Reconciliation strategija MMP vs backend
- Alerting na neskladja

Git commit: "Faza 6: privacy-aware plast + Astra dokument"

---

## FAZA 7 (opcijsko) — Dashboard

Ustvari `04_dashboard/streamlit_app.py`:
- Poveži na MMP marts shemo
- 3 vizualizacije: najboljši kanali po ROAS, MMP vs backend razhajanje, SKAN vs deterministična pokritost

Git commit: "Faza 7: Streamlit dashboard"

---

## KONČNO POROČILO
Posodobi README.md z:
- Screenshoti (če dashboard)
- Rezultati reconciliation (koliko neskladij najdeno)
- Kako zagnati

Ustvari `00_docs/PROJEKT_POROCILO.md` z opisom kaj je narejeno v vsaki fazi.

Final git commit + push: "Projekt zaključen - vse faze"

---

## NAPOTKI
- Delaj fazo po fazo, NE preskakuj
- Po vsaki fazi: git add . && git commit && git push
- Če faza ne uspe, zapiši v poročilo in nadaljuj
- Testiraj vsako Python skripto da dejansko teče
- dbt run mora uspeti brez napak
- Vsi komentarji in docstringi v slovenščini

## ZAČNI Z FAZO 0!
