"""Conexion a PostgreSQL y utilidades de carga masiva."""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src import config

_engine: Engine | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(config.url_postgres())
    return _engine


def ejecutar_sql(ruta: str | Path) -> None:
    """Ejecuta un archivo .sql completo (DDL, vistas)."""
    sql = Path(ruta).read_text(encoding="utf-8")
    with engine().begin() as con:
        con.exec_driver_sql(sql)


def consultar(sql: str, **params) -> pd.DataFrame:
    with engine().connect() as con:
        return pd.read_sql(text(sql), con, params=params)


def copiar_df(df: pd.DataFrame, tabla: str) -> int:
    """Carga un DataFrame con COPY (mucho mas rapido que to_sql para 4M filas).

    Las columnas del DataFrame deben llamarse igual que en la tabla destino.
    """
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    columnas = ", ".join(df.columns)
    raw = engine().raw_connection()
    try:
        with raw.cursor() as cur:
            with cur.copy(f"COPY {tabla} ({columnas}) FROM STDIN WITH (FORMAT csv)") as cp:
                cp.write(buf.getvalue())
        raw.commit()
    finally:
        raw.close()
    return len(df)
