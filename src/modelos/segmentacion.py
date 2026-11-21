"""R5 / P5 - Segmentacion de paises por la forma de su curva.

Sugerencia: matriz pais x semana con incidencia semanal por 100.000,
normalizada por pais; KMeans con k elegido por codo/silueta; interpretar
cada grupo y ubicar a Chile.
"""
from __future__ import annotations

import pandas as pd


def matriz_incidencia_semanal(df_pais_dia: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("TODO(R5)")


def segmentar(matriz: pd.DataFrame, k: int) -> pd.DataFrame:
    raise NotImplementedError("TODO(R5): sklearn.cluster.KMeans")
