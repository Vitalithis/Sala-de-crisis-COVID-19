"""Our World in Data - vacunacion (llave: iso_code = iso3).

Es la unica fuente que entrega el % de vacunados que pide P3.
Si el equipo agrega una segunda fuente (nivel excelente R3), crear un modulo
hermano (oxcgrt.py o banco_mundial.py) con la misma interfaz.
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.ingesta.descargar import descargar_archivo

URL = (
    "https://raw.githubusercontent.com/owid/covid-19-data/master/"
    "public/data/vaccinations/vaccinations.csv"
)
DESTINO = config.RAW_EXTERNAS / "owid_vaccinations.csv"


def descargar() -> None:
    descargar_archivo(URL, DESTINO)


def cargar() -> pd.DataFrame:
    df = pd.read_csv(DESTINO, parse_dates=["date"])
    # Los agregados de OWID (continentes, ingresos) usan codigos OWID_*: no son paises
    df = df[~df["iso_code"].str.startswith("OWID_", na=False)]
    return df.rename(columns={"iso_code": "iso3", "date": "fecha"})


def tasa_de_cruce(iso3_jhu: pd.Series, iso3_externa: pd.Series) -> dict:
    """R3: cuantos territorios cruzan y cuales no (el 'por que' se documenta)."""
    a, b = set(iso3_jhu.dropna()), set(iso3_externa.dropna())
    return {
        "territorios_jhu": len(a),
        "cruzan": len(a & b),
        "tasa_cruce_pct": round(100 * len(a & b) / max(len(a), 1), 1),
        "solo_jhu": sorted(a - b),
        "solo_externa": sorted(b - a),
    }
