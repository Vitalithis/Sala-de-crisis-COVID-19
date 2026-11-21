"""R5 - pronosticar(territorio, fecha_corte, horizonte=14) y backtesting.

Minimo: dos modelos (uno base) evaluados en >= 3 fechas de corte con MAE y MAPE.
Excelente: mas de dos modelos o variables externas (vacunacion).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.modelos.datos import serie_territorio


def modelo_media_movil(y: pd.Series, horizonte: int) -> np.ndarray:
    """Modelo base: repite la media de los ultimos 7 dias."""
    return np.repeat(y.tail(7).mean(), horizonte)


def modelo_holt(y: pd.Series, horizonte: int) -> np.ndarray:
    """TODO(R5): suavizamiento exponencial (statsmodels ExponentialSmoothing)."""
    raise NotImplementedError


MODELOS = {"media_movil": modelo_media_movil, "holt": modelo_holt}


def pronosticar(territorio: str, fecha_corte: str, horizonte: int = 14,
                modelo: str = "media_movil", variable: str = "casos_nuevos") -> pd.DataFrame:
    hist = serie_territorio(territorio, fecha_corte)          # nada posterior al corte
    y = hist[variable].clip(lower=0).fillna(0)
    pred = MODELOS[modelo](y, horizonte)
    fechas = pd.date_range(pd.Timestamp(fecha_corte) + pd.Timedelta(days=1), periods=horizonte)
    return pd.DataFrame({"fecha": fechas, "pronostico": np.clip(pred, 0, None), "modelo": modelo})


def mae(real, pred) -> float:
    return float(np.mean(np.abs(np.asarray(real) - np.asarray(pred))))


def mape(real, pred) -> float:
    real, pred = np.asarray(real, float), np.asarray(pred, float)
    m = real != 0
    return float(np.mean(np.abs((real[m] - pred[m]) / real[m])) * 100) if m.any() else np.nan


def backtesting(territorio: str, cortes: list[str], modelos: list[str] | None = None,
                horizonte: int = 14) -> pd.DataFrame:
    """TODO(R5): para cada corte y modelo, comparar el pronostico con lo ocurrido."""
    raise NotImplementedError
