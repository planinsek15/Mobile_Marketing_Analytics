# Projektna naloga — Mobile Marketing Analytics Pipeline

> Portfolio projekt, zasnovan natanko za vlogo "Data Engineer z izkušnjami z mobile app analitiko" (tip Astra AI). Cilj: zgraditi end-to-end podatkovno platformo, ki združi atribucijske podatke iz MMP-jev (AppsFlyer + Singular), jih uskladi z backend dogodki in odgovori na vprašanje **"kateri kanali, kampanje in segmenti res prinašajo dobičkonosno rast"** — ob upoštevanju realnosti iOS zasebnosti (SKAN).

---

## Zakaj točno ta projekt

Razpis ima tri jedrne zahteve:
1. **Mobile app tracking infrastructure** → zgradiš pipeline od virov do skladišča
2. **Kakovost podatkov med appom, MMP-ji in backendom** → zgradiš reconciliation in data quality plast (to je tvoja najmočnejša točka)
3. **Razumevanje, kateri kanali/kampanje/segmenti prinašajo rast** → zgradiš marketinški mart z metrikami ROAS/LTV/retention

Ker do pravih AppsFlyer/Singular produkcijskih podatkov nimaš dostopa, **simuliraš podatke po njihovih dokumentiranih shemah**. To je popolnoma legitimno za portfolio in hkrati dokaže, da poznaš domeno (pozna jih malo data engineerjev).

---

## Tehnološki sklad

- **Python** — simulacija virov in ingestion
- **Skladišče**: **DuckDB** (popolnoma lokalno, brezplačno) ali **BigQuery** (free tier) — DuckDB priporočam za hiter začetek
- **dbt** — transformacije, modeliranje, testi kakovosti
- **Airflow** (lokalno prek Dockerja) — orkestracija (lahko opcijsko na koncu)
- **Dashboard (opcijsko, minimalno)**: **Metabase** (samodejno generira grafe — nič UI dela) ali preprost **Streamlit**

Tvoje MS SQL znanje boš tu intenzivno uporabil — modeliranje in transformacije so čisti SQL.

---

## Arhitektura (nariši to v README)

```
AppsFlyer raw   ─┐
Singular cost   ─┤
SKAN postbacks  ─┼─► RAW (bronze) ─► STAGING/RECONCILE (silver) ─► MARTS (gold) ─► Dashboard
Backend events  ─┘        │                    │                       │
                     ingestion        data quality + reconciliation   metrike: ROAS, LTV,
                     (Python)         (dbt testi, discrepancy report)  retention, CAC, CPI
```

---

## Faze in navodila

### Faza 1 — Simulacija virov (sources)

Z Pythonom (knjižnica `Faker`) generiraj 4 vire, ki posnemajo realne sheme. Namerno vgradi **neskladja** med njimi — to je bistvo projekta.

1. **AppsFlyer raw data** (po install in event sheme): polja `appsflyer_id`, `media_source`, `campaign`, `af_adset`, `af_ad`, `install_time`, `attributed_touch_time`, `attributed_touch_type` (click/impression), `event_name` (`af_purchase`, `af_subscribe`…), `event_revenue`, `country_code`, `platform` (ios/android).
2. **Singular cost/reporting** (dnevni agregat po omrežju): `date`, `source` (Meta, Google Ads, TikTok, Apple Search Ads…), `campaign`, `country`, `impressions`, `clicks`, `installs`, `cost`.
3. **SKAN postbacks** (agregirani, brez user ID-ja — iOS realnost): `ad_network_id`, `source_identifier` (campaign), `conversion_value` (0–63 ali coarse low/med/high), `postback_sequence_index` (0–2 okno), `redownload`, brez možnosti joina na user level.
4. **Backend / in-app events** (lasten vir resnice aplikacije): `user_id`, `event`, `revenue`, `event_time`. Tu vgradi neskladja: pozni dogodki, podvojeni dogodki, kakšen dogodek brez atribucije, drugačen revenue kot pri MMP.

### Faza 2 — Ingestion v RAW (bronze)

- Python skripte naložijo vse 4 vire v `raw` shemo skladišča.
- Naloži idempotentno (ponoven zagon ne podvoji), particionirano po datumu.

### Faza 3 — Reconciliation in kakovost podatkov (jedro projekta — tvoja prednost)

To je del, ki te loči od marketinških analitikov. V dbt zgradi:

- **Discrepancy report**: dnevni revenue in installi po kanalu — **MMP vs backend** stran ob strani, z izračunom razlike (%). Označi vrstice, kjer delta presega prag (npr. 5 %).
- **Deduplikacija** backend dogodkov in obravnava **poznih dogodkov** (`attributed_touch_time` vs `install_time`).
- **Obravnava SKAN agregatov**, ki jih ni mogoče združiti na ravni uporabnika — modeliraj jih ločeno (aggregated-only).
- **dbt testi**: `not_null`, `unique`, `relationships`, **freshness**, plus custom testi: poraba brez installov, installi brez porabe, negativni revenue, conversion_value izven 0–63.

### Faza 4 — Modeliranje (silver → gold marts)

Dimenzijski model:
- Dejstvene tabele: `fct_installs`, `fct_events`, `fct_spend`
- Dimenzije: `dim_campaign`, `dim_channel`, `dim_geo`, `dim_date`
- **Unified marketing mart**: join porabe + installov + prihodka po `channel × campaign × geo × date`
- **Cohort/retention model**: D1 / D7 / D30 retention po akvizicijskih kohortah

### Faza 5 — Metrike rasti

V gold plasti izračunaj:
- **CPI** (cost per install), **CAC** (cost per paying user)
- **ROAS** D7 in D30 (prihodek / poraba)
- **LTV** (preprosta napoved iz zgodnjih kohort)
- **Blended vs SKAN-only** pogled (deterministični + agregirani)

### Faza 6 — Privacy-aware plast ("senior" pika na i)

- Postavi SKAN agregirane podatke ob deterministične in pokaži **"ROAS gap"** — razliko med tem, kar poroča MMP, in tem, kar potrjuje backend.
- Razloži vpliv **crowd anonymity** (NULL conversion values pri majhnih kampanjah) in zakaj je pri nizkem ATT opt-inu deterministična atribucija nezanesljiva.

Ta faza je največji diferenciator — pokaže, da razumeš atribucijo leta 2026, ne le ETL.

### Faza 7 (opcijsko) — Orkestracija + dashboard

- Airflow DAG: dnevno simulacija → ingestion → `dbt run` → `dbt test`.
- Dashboard (minimalen): Metabase nad gold marti — 3 vprašanja: najboljši kanali po ROAS, kje se MMP in backend razhajata, SKAN vs deterministična pokritost.

---

## Kaj predaš

GitHub repo z:
- urejenim `README.md` (arhitekturna shema, razlaga reconciliation logike, screenshoti)
- simulacijskimi skriptami, dbt projektom, (opcijsko) Airflow DAG-om in dashboardom
- kratkim dokumentom **"Kako bi izboljšal Astra tracking infrastrukturo"** (1 stran): kako bi postavil event taxonomy, SKAN conversion value shemo, reconciliation med MMP in backendom, in alerting na neskladja.

Ta zadnji dokument lahko **dobesedno priložiš prijavi** — pokaže, da razmišljaš kot nekdo, ki bo "stvari postavil na višji nivo".

---

## Kako se pozicioniraš ob prijavi

- Tvoja prednost: večina kandidatov za to vlogo pozna marketing, ampak so šibki inženirji. Ti si obratno — močan na podatkovni strani (pipeline, reconciliation, modeliranje, kakovost na skali). To poudari.
- Pošteno povej: "MMP-je sem osvojil prek tega projekta in jih hitro obvladam; moja jedrna prednost je zanesljiva podatkovna infrastruktura in kakovost podatkov med sistemi."
- Projekt + dokument = dokaz, ne obljuba.
