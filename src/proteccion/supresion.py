"""R6 - Control de divulgacion: supresion de celdas pequenas.

Regla base: si un territorio tiene poblacion pequena y el conteo esta entre
1 y 4, el valor se muestra como "<5" en el tablero. El tablero DEBE pasar sus
tablas por `suprimir` antes de mostrarlas.
"""
from __future__ import annotations

import pandas as pd

CONTEO_MIN, CONTEO_MAX = 1, 4
POBLACION_PEQUENA = 5_000   # TODO(R6): justificar el umbral en docs/proteccion_datos.md


def suprimir(df: pd.DataFrame, columnas: list[str], col_poblacion: str = "poblacion") -> pd.DataFrame:
    out = df.copy()
    pequeno = out[col_poblacion] < POBLACION_PEQUENA
    for c in columnas:
        mask = pequeno & out[c].between(CONTEO_MIN, CONTEO_MAX)
        out[c] = out[c].astype("object")
        out.loc[mask, c] = "<5"
    return out


def informacion_perdida(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """TODO(R6, excelente): % de celdas suprimidas (condados de EE.UU.)."""
    raise NotImplementedError
