"""R2 - Reglas ejecutables para las seis dimensiones de calidad.

Cada regla devuelve un valor medido; se compara con su umbral y se marca
OK / ALERTA. `ejecutar_reglas` se llama en cada carga (ver src/pipeline.py).

Las reglas marcadas TODO son el trabajo pendiente del responsable de R2.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class Regla:
    nombre: str
    dimension: str      # completitud | unicidad | validez | consistencia | exactitud | oportunidad
    descripcion: str
    umbral: float       # valor maximo aceptable (en % salvo que se indique)
    medir: Callable[[pd.DataFrame], float]


def _pct(serie_bool: pd.Series) -> float:
    return round(100 * serie_bool.mean(), 3) if len(serie_bool) else 0.0


def _col_territorio(d: pd.DataFrame) -> str:
    return "clave_territorio" if "clave_territorio" in d.columns else "combined_key"


def _medir_retrocesos(d: pd.DataFrame) -> float:
    col_terr = _col_territorio(d)
    ordenado = d.sort_values([col_terr, "fecha_reporte"])
    diffs = ordenado.groupby(col_terr, sort=False)["confirmed"].diff()
    return _pct(diffs < 0)


def _medir_dias_sin_reporte(d: pd.DataFrame) -> float:
    col_terr = _col_territorio(d)
    ordenado = d.sort_values([col_terr, "fecha_reporte"])
    diffs = ordenado.groupby(col_terr, sort=False)["confirmed"].diff()
    anio = pd.to_datetime(ordenado["fecha_reporte"]).dt.year
    mask = (anio >= 2022) & (ordenado["confirmed"] > 100_000) & (diffs == 0)
    return _pct(mask)


def _medir_picos_rezago(d: pd.DataFrame) -> float:
    col_terr = _col_territorio(d)
    ordenado = d.sort_values([col_terr, "fecha_reporte"])
    diffs = ordenado.groupby(col_terr, sort=False)["confirmed"].diff().clip(lower=0)
    media_14d = diffs.groupby(ordenado[col_terr], sort=False).transform(
        lambda s: s.shift(1).rolling(14, min_periods=1).mean()
    )
    mask = (diffs > 500) & (media_14d > 0) & (diffs > 5 * media_14d)
    return _pct(mask)


REGLAS: list[Regla] = [
    Regla("pais_nulo", "completitud", "% de filas sin country_region", 0.0,
          lambda d: _pct(d["country_region"].isna())),
    Regla("confirmados_nulos", "completitud", "% de filas sin confirmed", 1.0,
          lambda d: _pct(d["confirmed"].isna())),
    Regla("duplicados_territorio_dia", "unicidad",
          "% de filas duplicadas por (fecha_reporte, territorio)", 0.0,
          lambda d: _pct(d.duplicated(["fecha_reporte", _col_territorio(d)]))),
    Regla("acumulados_negativos", "validez", "% de filas con confirmed o deaths < 0", 0.0,
          lambda d: _pct((d["confirmed"] < 0) | (d["deaths"] < 0))),
    Regla("coordenadas_fuera_rango", "validez", "% de filas con lat/long fuera de rango", 0.0,
          lambda d: _pct((d["lat"].abs() > 90) | (d["long"].abs() > 180))),
    Regla("fallecidos_mayor_casos", "consistencia", "% de filas con deaths > confirmed", 0.0,
          lambda d: _pct(d["deaths"] > d["confirmed"])),
    Regla("acumulados_retroceden", "consistencia",
          "% de filas con acumulado confirmed menor al día anterior", 1.0,
          _medir_retrocesos),
    Regla("picos_por_rezago", "exactitud",
          "% de filas con picos > 5x media móvil 14d (y > 500 casos)", 0.5,
          _medir_picos_rezago),
    Regla("dias_sin_reporte_2022_23", "oportunidad",
          "% de filas sin variación en 2022-2023 para territorios > 100k casos", 1.0,
          _medir_dias_sin_reporte),
]


def ejecutar_reglas(df: pd.DataFrame, reglas: list[Regla] = REGLAS) -> pd.DataFrame:
    filas = []
    for r in reglas:
        valor = r.medir(df)
        filas.append({
            "regla": r.nombre, "dimension": r.dimension, "descripcion": r.descripcion,
            "valor": valor, "umbral": r.umbral,
            "estado": "OK" if valor <= r.umbral else "ALERTA",
        })
    return pd.DataFrame(filas)


if __name__ == "__main__":
    from src import config

    print(ejecutar_reglas(pd.read_parquet(config.PARQUET_UNIFICADO)).to_string(index=False))
