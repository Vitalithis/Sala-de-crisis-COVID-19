"""Rutas y parametros compartidos por todo el proyecto.

Regla del equipo: ninguna ruta ni credencial se escribe "a mano" en notebooks o
scripts; todo se importa desde aqui.
"""
from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv es opcional: si no esta, se usan variables de entorno
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

RAIZ = Path(__file__).resolve().parents[1]

# Capas de datos (R1)
DATA = RAIZ / "data"
RAW = DATA / "raw"                    # capa cruda: CSV tal cual (no se sube)
RAW_DIARIOS = RAW / "daily_reports"
RAW_SERIES = RAW / "time_series"
RAW_EXTERNAS = RAW / "externas"
CLEAN = DATA / "clean"                # capa limpia: Parquet
DW_EXPORT = DATA / "dw"               # exportacion del DW (Parquet por tabla)

REPORTS = RAIZ / "reports"
FIGURAS = REPORTS / "figuras"

# Fuente principal (JHU CSSE, archivada)
JHU_BASE = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/"
)
FECHA_INICIO = "2020-01-22"
FECHA_FIN = "2023-03-09"

# Archivo unificado de la capa limpia
PARQUET_UNIFICADO = CLEAN / "reportes_diarios_unificados.parquet"

# PostgreSQL (capa analitica)
PG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "sala_crisis"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", "postgres"),
}


def url_postgres() -> str:
    """URL de conexion para SQLAlchemy (driver psycopg 3)."""
    return (
        f"postgresql+psycopg://{PG['user']}:{PG['password']}"
        f"@{PG['host']}:{PG['port']}/{PG['dbname']}"
    )


def crear_carpetas() -> None:
    for p in (RAW_DIARIOS, RAW_SERIES, RAW_EXTERNAS, CLEAN, DW_EXPORT, FIGURAS):
        p.mkdir(parents=True, exist_ok=True)
