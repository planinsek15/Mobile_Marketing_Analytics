#!/usr/bin/env python3
"""Faza 7 (opcijsko): Streamlit dashboard nad MMP marts shemo.

Tri vprašanja, ki jih dashboard odgovori:
  1. Kateri kanali so najboljši po ROAS (in kakšen je njihov CPI/CAC)?
  2. Kje se MMP in backend razhajata (reconciliation neskladja)?
  3. SKAN vs deterministična pokritost (crowd anonymity, ROAS gap)?

ZAGON:
    source env.sh           # nujno za lokalni ODBC driver
    streamlit run 04_dashboard/streamlit_app.py
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import pyodbc
import streamlit as st


def get_connection() -> pyodbc.Connection:
    """Povezava na MMP bazo iz okoljskih spremenljivk (glej env.sh)."""
    server = os.environ.get("MMP_SERVER", "localhost,1433")
    database = os.environ.get("MMP_DATABASE", "MMP")
    uid = os.environ.get("MMP_UID", "sa")
    pwd = os.environ.get("MMP_PWD", "PimSql2024!")
    driver = os.environ.get("MMP_DRIVER", "ODBC Driver 18 for SQL Server")
    cs = (f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
          f"UID={uid};PWD={pwd};Encrypt=yes;TrustServerCertificate=yes")
    return pyodbc.connect(cs, timeout=30)


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    """Izvede SQL in vrne DataFrame (rezultat predpomnjen 5 min)."""
    with get_connection() as cn:
        return pd.read_sql(sql, cn)


# ── Poizvedbe ───────────────────────────────────────────────────────────────
Q_ROAS = """
SELECT channel_key AS channel,
       SUM(cost)         AS cost,
       SUM(installs)     AS installs,
       SUM(paying_users) AS paying_users,
       SUM(revenue_d30)  AS revenue_d30,
       CAST(SUM(revenue_d30)/NULLIF(SUM(cost),0) AS decimal(10,4)) AS roas_d30,
       CAST(SUM(cost)/NULLIF(SUM(installs),0)    AS decimal(10,2)) AS cpi,
       CAST(SUM(cost)/NULLIF(SUM(paying_users),0) AS decimal(10,2)) AS cac
FROM marts.mart_growth_metrics
GROUP BY channel_key
ORDER BY roas_d30 DESC
"""

Q_DISCREPANCY = """
SELECT channel,
       SUM(mmp_revenue)     AS mmp_revenue,
       SUM(backend_revenue) AS backend_revenue,
       SUM(CASE WHEN is_discrepancy_flag=1 THEN 1 ELSE 0 END) AS flagged_days,
       COUNT(*)             AS total_days
FROM marts.rec_revenue_discrepancy
GROUP BY channel
ORDER BY mmp_revenue DESC
"""

Q_PRIVACY = """
SELECT channel_key AS channel,
       SUM(installs)        AS installs,
       SUM(ios_installs)    AS ios_installs,
       SUM(skan_postbacks)  AS skan_postbacks,
       SUM(skan_null_cv)    AS skan_null_cv,
       SUM(has_crowd_anonymity) AS campaigns_anonymized,
       CAST(SUM(mmp_revenue_d30)/NULLIF(SUM(cost),0)     AS decimal(10,4)) AS mmp_roas,
       CAST(SUM(backend_revenue_d30)/NULLIF(SUM(cost),0) AS decimal(10,4)) AS backend_roas
FROM marts.mart_privacy_roas_gap
GROUP BY channel_key
ORDER BY installs DESC
"""


def main() -> None:
    st.set_page_config(page_title="Mobile Marketing Analytics", layout="wide")
    st.title("📱 Mobile Marketing Analytics")
    st.caption("MMP (AppsFlyer) + Singular + SKAN + backend → reconciliation & ROAS")

    try:
        roas = run_query(Q_ROAS)
        disc = run_query(Q_DISCREPANCY)
        priv = run_query(Q_PRIVACY)
    except Exception as e:  # noqa: BLE001
        st.error(f"Napaka pri povezavi na MMP bazo: {e}\n\n"
                 "Si pognal `source env.sh` pred zagonom streamlita?")
        return

    # ── KPI vrstica ──────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Skupna poraba", f"{roas['cost'].sum():,.0f} €")
    c2.metric("Installi", f"{int(roas['installs'].sum()):,}")
    c3.metric("Prihodek D30 (MMP)", f"{roas['revenue_d30'].sum():,.0f} €")
    overstate = 100 * (disc['mmp_revenue'].sum() - disc['backend_revenue'].sum()) / disc['mmp_revenue'].sum()
    c4.metric("MMP precenjevanje vs backend", f"{overstate:.1f} %")

    # ── 1) Najboljši kanali po ROAS ──────────────────────────────────────
    st.subheader("1️⃣ Najboljši kanali po ROAS (D30)")
    paid = roas[roas["roas_d30"].notna()].copy()
    fig1 = px.bar(paid, x="channel", y="roas_d30", color="channel",
                  text="roas_d30", labels={"roas_d30": "ROAS D30", "channel": "Kanal"})
    fig1.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)
    st.dataframe(roas, use_container_width=True, hide_index=True)

    # ── 2) MMP vs backend razhajanje ─────────────────────────────────────
    st.subheader("2️⃣ Kje se MMP in backend razhajata")
    melt = disc.melt(id_vars="channel", value_vars=["mmp_revenue", "backend_revenue"],
                     var_name="vir", value_name="prihodek")
    fig2 = px.bar(melt, x="channel", y="prihodek", color="vir", barmode="group",
                  labels={"prihodek": "Prihodek (€)", "channel": "Kanal", "vir": "Vir"})
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Označeni dnevi z neskladjem > 5 %:")
    st.dataframe(disc, use_container_width=True, hide_index=True)

    # ── 3) SKAN vs deterministična pokritost ─────────────────────────────
    st.subheader("3️⃣ SKAN vs deterministična pokritost (privacy)")
    colA, colB = st.columns(2)
    with colA:
        fig3 = px.bar(priv, x="channel", y=["ios_installs", "skan_postbacks"],
                      barmode="group", labels={"value": "Število", "channel": "Kanal"})
        fig3.update_layout(title="iOS installi (deterministični) vs SKAN postbacki")
        st.plotly_chart(fig3, use_container_width=True)
    with colB:
        fig4 = px.bar(priv, x="channel", y=["mmp_roas", "backend_roas"],
                      barmode="group", labels={"value": "ROAS", "channel": "Kanal"})
        fig4.update_layout(title="MMP ROAS vs backend potrjeni ROAS")
        st.plotly_chart(fig4, use_container_width=True)
    st.caption("skan_null_cv = postbacki z zadržano vrednostjo (crowd anonymity):")
    st.dataframe(priv, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
