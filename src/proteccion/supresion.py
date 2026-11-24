"""R6 - Control de divulgacion: supresion de celdas pequenas.

Regla base: si un territorio tiene poblacion pequena y el conteo esta entre
1 y 4, el valor se muestra como "<5" en el tablero. El tablero DEBE pasar sus
tablas por `suprimir` antes de mostrarlas.
"""
from __future__ import annotations

import pandas as pd

CONTEO_MIN, CONTEO_MAX = 1, 4
POBLACION_PEQUENA = 5_000   # Umbral estricto para condados de EE.UU. (50_000 en tablero general)


def suprimir(
    df: pd.DataFrame,
    columnas: list[str],
    col_poblacion: str = "poblacion",
    umbral_poblacion: int = POBLACION_PEQUENA,
) -> pd.DataFrame:
    """Suprime conteos entre 1 y 4 en territorios con poblacion menor al umbral."""
    out = df.copy()
    pequeno = out[col_poblacion] < umbral_poblacion
    for c in columnas:
        mask = pequeno & out[c].between(CONTEO_MIN, CONTEO_MAX)
        out[c] = out[c].astype("object")
        out.loc[mask, c] = "<5"
    return out


def informacion_perdida(
    df: pd.DataFrame,
    columnas: list[str],
    col_poblacion: str = "poblacion",
    umbral_poblacion: int = POBLACION_PEQUENA,
) -> pd.DataFrame:
    """Calcula el numero y porcentaje de celdas suprimidas por columna."""
    total = len(df)
    pequeno = df[col_poblacion] < umbral_poblacion
    filas = []
    for c in columnas:
        suprimidas = int((pequeno & df[c].between(CONTEO_MIN, CONTEO_MAX)).sum())
        filas.append({
            "columna": c,
            "total_filas": total,
            "celdas_suprimidas": suprimidas,
            "pct_perdida": round(100.0 * suprimidas / max(total, 1), 3),
        })
    return pd.DataFrame(filas)
