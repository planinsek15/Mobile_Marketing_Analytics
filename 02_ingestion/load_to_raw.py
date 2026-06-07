#!/usr/bin/env python3
"""Faza 2: Ingestion 4 CSV virov v raw shemo SQL Serverja (MMP).

Naloži vsak CSV iz data/ v ustrezno raw tabelo (raw.appsflyer, raw.singular,
raw.skan, raw.backend). Lastnosti:

  * DDL z eksplicitnimi tipi (CREATE, če tabela še ne obstaja),
  * idempotentnost: TRUNCATE + INSERT (ponoven zagon NE podvoji podatkov),
  * stolpec _loaded_at (datetime2) z časom nalaganja,
  * logična particija po datumu — indeks na naravnem datumskem stolpcu,
  * bulk insert prek pyodbc fast_executemany.

Povezava se bere iz okoljskih spremenljivk (glej env.sh) z razumnimi privzetki.
PRED ZAGONOM:  source env.sh   (za lokalni ODBC driver)

Zagon:  python3 02_ingestion/load_to_raw.py
"""
from __future__ import annotations

import csv
import datetime as dt
import os
from typing import Any, Callable

import pyodbc

# ── Poti ────────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_BASE, "data")


def connect() -> pyodbc.Connection:
    """Vzpostavi povezavo na MMP bazo iz okoljskih spremenljivk."""
    server = os.environ.get("MMP_SERVER", "localhost,1433")
    database = os.environ.get("MMP_DATABASE", "MMP")
    uid = os.environ.get("MMP_UID", "sa")
    pwd = os.environ.get("MMP_PWD", "PimSql2024!")
    driver = os.environ.get("MMP_DRIVER", "ODBC Driver 18 for SQL Server")
    cs = (f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
          f"UID={uid};PWD={pwd};Encrypt=yes;TrustServerCertificate=yes")
    return pyodbc.connect(cs, timeout=30)


# ── Pomožne pretvorbe ───────────────────────────────────────────────────────
def _s(v: str | None) -> str | None:
    """Prazen niz → None, sicer ostane niz."""
    return v if v not in (None, "") else None


def _f(v: str | None) -> float | None:
    """Niz → float ali None."""
    return float(v) if v not in (None, "") else None


def _i(v: str | None) -> int | None:
    """Niz → int ali None."""
    return int(v) if v not in (None, "") else None


# ── Definicije tabel ────────────────────────────────────────────────────────
# Vsaka: DDL (CREATE), indeks (logična particija po datumu), branje vrstic iz CSV.

def _rows_appsflyer(path: str) -> list[tuple]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((
                _s(r["appsflyer_id"]), _s(r["media_source"]), _s(r["campaign"]),
                _s(r["af_adset"]), _s(r["af_ad"]), _s(r["install_time"]),
                _s(r["attributed_touch_time"]), _s(r["attributed_touch_type"]),
                _s(r["event_name"]), _f(r["event_revenue"]), _s(r["event_time"]),
                _s(r["country_code"]), _s(r["platform"]),
            ))
    return out


def _rows_singular(path: str) -> list[tuple]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((
                _s(r["date"]), _s(r["source"]), _s(r["campaign"]), _s(r["country"]),
                _i(r["impressions"]), _i(r["clicks"]), _i(r["installs"]), _f(r["cost"]),
            ))
    return out


def _rows_skan(path: str) -> list[tuple]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((
                _s(r["ad_network_id"]), _s(r["source_identifier"]),
                _i(r["conversion_value"]), _i(r["postback_sequence_index"]),
                _i(r["redownload"]),
            ))
    return out


def _rows_backend(path: str) -> list[tuple]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((
                _s(r["user_id"]), _s(r["event"]), _f(r["revenue"]), _s(r["event_time"]),
            ))
    return out


# (tabela, csv, ddl, insert_cols, index_ddl, reader)
TABLES: list[dict[str, Any]] = [
    {
        "name": "raw.appsflyer",
        "csv": "appsflyer_raw.csv",
        "ddl": """
            CREATE TABLE raw.appsflyer (
                appsflyer_id          varchar(64)   NOT NULL,
                media_source          varchar(64)   NULL,
                campaign              varchar(128)  NULL,
                af_adset              varchar(128)  NULL,
                af_ad                 varchar(128)  NULL,
                install_time          datetime2(0)  NULL,
                attributed_touch_time datetime2(0)  NULL,
                attributed_touch_type varchar(20)   NULL,
                event_name            varchar(40)   NULL,
                event_revenue         decimal(12,2) NULL,
                event_time            datetime2(0)  NULL,
                country_code          char(2)       NULL,
                platform              varchar(10)   NULL,
                _loaded_at            datetime2(3)  NOT NULL
            )""",
        "cols": ("appsflyer_id, media_source, campaign, af_adset, af_ad, "
                 "install_time, attributed_touch_time, attributed_touch_type, "
                 "event_name, event_revenue, event_time, country_code, platform, _loaded_at"),
        "nparams": 13,
        "index": "CREATE INDEX ix_appsflyer_install ON raw.appsflyer(install_time)",
        "reader": _rows_appsflyer,
    },
    {
        "name": "raw.singular",
        "csv": "singular_cost.csv",
        "ddl": """
            CREATE TABLE raw.singular (
                [date]      date          NOT NULL,
                source      varchar(64)   NULL,
                campaign    varchar(128)  NULL,
                country     char(2)       NULL,
                impressions int           NULL,
                clicks      int           NULL,
                installs    int           NULL,
                cost        decimal(14,2) NULL,
                _loaded_at  datetime2(3)  NOT NULL
            )""",
        "cols": "[date], source, campaign, country, impressions, clicks, installs, cost, _loaded_at",
        "nparams": 8,
        "index": "CREATE INDEX ix_singular_date ON raw.singular([date])",
        "reader": _rows_singular,
    },
    {
        "name": "raw.skan",
        "csv": "skan_postbacks.csv",
        "ddl": """
            CREATE TABLE raw.skan (
                ad_network_id           varchar(64)  NULL,
                source_identifier       varchar(128) NULL,
                conversion_value        tinyint      NULL,
                postback_sequence_index tinyint      NULL,
                redownload              bit          NULL,
                _loaded_at              datetime2(3) NOT NULL
            )""",
        "cols": ("ad_network_id, source_identifier, conversion_value, "
                 "postback_sequence_index, redownload, _loaded_at"),
        "nparams": 5,
        "index": "CREATE INDEX ix_skan_campaign ON raw.skan(source_identifier)",
        "reader": _rows_skan,
    },
    {
        "name": "raw.backend",
        "csv": "backend_events.csv",
        "ddl": """
            CREATE TABLE raw.backend (
                user_id    varchar(64)   NOT NULL,
                event      varchar(40)   NULL,
                revenue    decimal(12,2) NULL,
                event_time datetime2(0)  NULL,
                _loaded_at datetime2(3)  NOT NULL
            )""",
        "cols": "user_id, event, revenue, event_time, _loaded_at",
        "nparams": 4,
        "index": "CREATE INDEX ix_backend_event_time ON raw.backend(event_time)",
        "reader": _rows_backend,
    },
]


def _table_exists(cur: pyodbc.Cursor, full_name: str) -> bool:
    schema, table = full_name.split(".")
    cur.execute(
        "SELECT 1 FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id "
        "WHERE s.name=? AND t.name=?", schema, table)
    return cur.fetchone() is not None


def load_table(cur: pyodbc.Cursor, spec: dict[str, Any], loaded_at: dt.datetime) -> int:
    """Ustvari (če treba), izprazni in napolni eno raw tabelo. Vrne št. vrstic."""
    name = spec["name"]
    # 1) DDL + indeks samo ob prvem zagonu.
    if not _table_exists(cur, name):
        cur.execute(spec["ddl"])
        cur.execute(spec["index"])
        print(f"  [{name}] tabela ustvarjena")
    # 2) Idempotentnost: izprazni.
    cur.execute(f"TRUNCATE TABLE {name}")
    # 3) Preberi CSV in dodaj _loaded_at vsaki vrstici.
    path = os.path.join(DATA_DIR, spec["csv"])
    rows = spec["reader"](path)
    rows = [r + (loaded_at,) for r in rows]
    # 4) Bulk insert.
    placeholders = ", ".join(["?"] * (spec["nparams"] + 1))  # +1 za _loaded_at
    sql = f"INSERT INTO {name} ({spec['cols']}) VALUES ({placeholders})"
    cur.fast_executemany = True
    if rows:
        cur.executemany(sql, rows)
    return len(rows)


def main() -> None:
    print("── Ingestion v raw shemo (MMP) ───────────────────")
    loaded_at = dt.datetime.now()
    cn = connect()
    cur = cn.cursor()
    counts: dict[str, int] = {}
    try:
        for spec in TABLES:
            counts[spec["name"]] = load_table(cur, spec, loaded_at)
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cur.close()
        cn.close()

    print("── Naloženo (število vrstic) ─────────────────────")
    for name, n in counts.items():
        print(f"  {name:<16} {n:>7,}")
    print("── Ingestion končan ──────────────────────────────")


if __name__ == "__main__":
    main()
