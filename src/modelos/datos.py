"""Acceso a series para modelos: UNICO punto donde se aplica la fecha de corte.

Regla del desafio en vivo: pronosticar() y alerta() nunca leen datos
posteriores a fecha_corte. Toda serie que usen los modelos pasa por aqui.
"""
from __future__ import annotations

import pandas as pd


def recortar(serie: pd.DataFrame, fecha_corte: str | pd.Timestamp) -> pd.DataFrame:
    """Deja solo filas con fecha <= fecha_corte. Columna obligatoria: 'fecha'."""
    corte = pd.Timestamp(fecha_corte)
    out = serie[pd.to_datetime(serie["fecha"]) <= corte].copy()
    assert out.empty or pd.to_datetime(out["fecha"]).max() <= corte
    return out


def serie_territorio(territorio: str, fecha_corte: str | pd.Timestamp) -> pd.DataFrame:
    """Serie diaria de un territorio hasta fecha_corte (inclusive), desde el DW.

    Columnas esperadas: fecha, casos_nuevos, fallecidos_nuevos, poblacion.
    `territorio` es un pais ('Chile') o una region de Chile ('Biobio').
    """
    from src import db

    sql = """
        SELECT fecha, casos_nuevos, fallecidos_nuevos, poblacion
        FROM vw_territorio_dia
        WHERE territorio = :t AND fecha <= :corte
        ORDER BY fecha
    """
    df = db.consultar(sql, t=territorio, corte=pd.Timestamp(fecha_corte).date())
    return recortar(df, fecha_corte)
