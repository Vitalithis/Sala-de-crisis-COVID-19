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


REGLAS: list[Regla] = [
    Regla("pais_nulo", "completitud", "% de filas sin country_region", 0.0,
          lambda d: _pct(d["country_region"].isna())),
    Regla("confirmados_nulos", "completitud", "% de filas sin confirmed", 1.0,
          lambda d: _pct(d["confirmed"].isna())),
    Regla("duplicados_territorio_dia", "unicidad",
          "% de filas duplicadas por (fecha_reporte, clave_territorio)", 0.0,
          lambda d: _pct(d.duplicated(["fecha_reporte", "clave_territorio"]))),
    Regla("acumulados_negativos", "validez", "% de filas con confirmed o deaths < 0", 0.0,
          lambda d: _pct((d["confirmed"] < 0) | (d["deaths"] < 0))),
    Regla("coordenadas_fuera_rango", "validez", "% de filas con lat/long fuera de rango", 0.0,
          lambda d: _pct((d["lat"].abs() > 90) | (d["long"].abs() > 180))),
    Regla("fallecidos_mayor_casos", "consistencia", "% de filas con deaths > confirmed", 0.0,
          lambda d: _pct(d["deaths"] > d["confirmed"])),
    # TODO(R2): exactitud -> diferencia entre las series de tiempo y la suma de reportes diarios
    # TODO(R2): oportunidad -> % de dias sin reporte por pais (sobre todo 2022, reportes semanales)
    # TODO(R2): consistencia -> % de dias con acumulado que retrocede (requiere nuevos diarios)
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
