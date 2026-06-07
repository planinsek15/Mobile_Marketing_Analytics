# 🤖 CLAUDE.md — Navodila za Claude Code
# Projekt: Mobile Marketing Analytics Pipeline

## KONTEKST PROJEKTA
End-to-end podatkovni pipeline za mobilno marketinško analitiko. Združuje atribucijske podatke iz MMP-jev (AppsFlyer, Singular), SKAN postbacke in backend dogodke. Cilj: portfolio projekt za vlogo Data Engineer.

Polna navodila: `00_docs/Projektna_naloga.md` — VEDNO preberi najprej.

## TEHNOLOŠKI SKLAD
- Python 3.10+ (Faker za simulacijo)
- SQL Server 2019 (Docker container `pim-sqlserver`)
- dbt z dbt-sqlserver adapterjem
- Streamlit (dashboard, opcijsko)

## SQL SERVER POVEZAVA
- Strežnik: localhost,1433 (Docker)
- Login: sa
- Geslo: PimSql2024!
- Baza za projekt: MMP (ustvari novo, NE PIM_test!)

### Ustvari bazo MMP na začetku:
```
docker exec -it pim-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'PimSql2024!' -C \
  -Q "IF DB_ID('MMP') IS NULL CREATE DATABASE MMP"
```

### Test ukaz:
```
docker exec -it pim-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'PimSql2024!' -C -d MMP
```

## SQL SERVER 2019 PRAVILA
- NE uporabljaj: LEAST(), GREATEST(), GENERATE_SERIES(), JSON_ARRAY(), JSON_OBJECT(), IS DISTINCT FROM
- Sheme: raw, staging, marts (medallion arhitektura)

## STRUKTURA MAP
- 00_docs/         dokumentacija
- 01_sources/      Python generatorji virov
- 02_ingestion/    nalaganje v SQL Server raw
- 03_dbt/          dbt transformacije
- 04_dashboard/    Streamlit
- data/            začasni CSV (git ignorira)

## PRAVILA KODIRANJA
- Python: type hints, docstrings v slovenščini
- SQL: komentarji v slovenščini
- Vsaka skripta naj bo samostojno zagonljiva
- Idempotentnost: ponoven zagon ne podvoji podatkov

## GIT
- Po vsaki fazi git commit
- Format: "Faza X: kratek opis"
- Push na GitHub po vsakem večjem koraku

## VIRI (4) — sheme polj
1. AppsFlyer: appsflyer_id, media_source, campaign, af_adset, af_ad, install_time, attributed_touch_time, attributed_touch_type, event_name, event_revenue, country_code, platform
2. Singular: date, source, campaign, country, impressions, clicks, installs, cost
3. SKAN: ad_network_id, source_identifier, conversion_value (0-63), postback_sequence_index (0-2), redownload
4. Backend: user_id, event, revenue, event_time (z namernimi neskladji!)

## NAMERNA NESKLADJA (bistvo projekta!)
V backend vir vgradi: pozne dogodke, podvojene dogodke, dogodke brez atribucije, drugačen revenue kot MMP. To je osnova za reconciliation plast.
