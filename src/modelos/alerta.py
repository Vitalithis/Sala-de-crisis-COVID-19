"""R5 - Alerta temprana: alerta(territorio, fecha).

Indicador sugerido por el enunciado: variacion semanal de la incidencia por
100.000 habitantes. El umbral se fija y se muestra en el tablero.
"""
from __future__ import annotations

import pandas as pd

from src.modelos.datos import serie_territorio

UMBRAL_VARIACION_PCT = 30.0     # TODO(R5): calibrar con la historia de Chile
INCIDENCIA_MINIMA = 10.0        # por 100.000 en 7 dias; evita alarmas con conteos bajos


def indicador(serie: pd.DataFrame) -> pd.DataFrame:
    s = serie.copy()
    s["inc_7d_100k"] = s["casos_nuevos"].clip(lower=0).rolling(7).sum() / s["poblacion"] * 1e5
    s["variacion_semanal_pct"] = s["inc_7d_100k"].pct_change(7) * 100
    return s


def alerta(territorio: str, fecha: str) -> dict:
    ind = indicador(serie_territorio(territorio, fecha)).iloc[-1]
    activa = bool(ind["variacion_semanal_pct"] > UMBRAL_VARIACION_PCT
                  and ind["inc_7d_100k"] > INCIDENCIA_MINIMA)
    return {
        "territorio": territorio, "fecha": fecha, "activa": activa,
        "inc_7d_100k": round(float(ind["inc_7d_100k"]), 2),
        "variacion_semanal_pct": round(float(ind["variacion_semanal_pct"]), 1),
        "umbral_pct": UMBRAL_VARIACION_PCT,
    }


def evaluar_alerta_chile(olas: list[tuple[str, str]]) -> pd.DataFrame:
    """TODO(R5): dias de anticipacion por ola y numero de falsas alarmas (P6)."""
    raise NotImplementedError
