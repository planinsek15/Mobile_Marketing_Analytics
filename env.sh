#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# env.sh — aktivacija okolja za Mobile Marketing Analytics Pipeline
#
# To okolje je bilo postavljeno BREZ root pravic (sudo ni bil na voljo):
#   - unixODBC + Microsoft ODBC Driver 18 sta razpakirana lokalno v ~/.local/odbc
#   - Python paketi (vključno z dbt) so v ~/.local (uporabniška namestitev)
#
# Uporaba:  source env.sh   (pred zagonom ingestiona ali dbt)
# ──────────────────────────────────────────────────────────────────────────

# Lokalni ODBC (libodbc.so.2 + libmsodbcsql-18) — nujno za pyodbc in dbt-sqlserver
if [ -f "$HOME/.local/odbc/activate.sh" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.local/odbc/activate.sh"
fi

# Uporabniško nameščeni Python skripti (dbt, streamlit, ...)
export PATH="$HOME/.local/bin:$PATH"

# Povezava na SQL Server (lahko prepišeš prek okolja)
export MMP_SERVER="${MMP_SERVER:-localhost,1433}"
export MMP_DATABASE="${MMP_DATABASE:-MMP}"
export MMP_UID="${MMP_UID:-sa}"
export MMP_PWD="${MMP_PWD:-XoXo!}"
export MMP_DRIVER="${MMP_DRIVER:-ODBC Driver 18 for SQL Server}"

echo "[env] ODBC: $(python3 -c 'import pyodbc; print(pyodbc.drivers())' 2>/dev/null)"
echo "[env] Baza: $MMP_DATABASE @ $MMP_SERVER"
