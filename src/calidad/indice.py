"""R2 / P4 - Indice de calidad por pais.

Propuesta de partida (el responsable decide y documenta la formula final en
docs/decisiones_calidad.md):

    indice = 100 - (w1 * %dias_retrocede + w2 * %dias_sin_reporte
                    + w3 * %picos_rezago + w4 * %fallecidos_mayor_casos
                    + w5 * |diferencia_series_vs_diarios|)
"""
from __future__ import annotations

import pandas as pd


PESOS_DEFAULT: dict[str, float] = {
    "pct_dias_retrocede": 3.0,
    "pct_dias_sin_reporte": 0.5,
    "pct_inconsistentes": 5.0,
    "pct_dias_faltantes": 0.5,
}
TOTAL_DIAS_SERIE = 1143


def problemas_por_pais(df_pais_dia: pd.DataFrame) -> pd.DataFrame:
    """Cuantifica los problemas de R2 por pais.

    Entrada: tabla pais x dia con columnas pais (o country_region), fecha,
    confirmados_acum (o confirmed), fallecidos_acum (o deaths) y casos_nuevos.
    """
    df = df_pais_dia.copy()
    col_pais = "pais" if "pais" in df.columns else "country_region"
    col_conf = "confirmados_acum" if "confirmados_acum" in df.columns else "confirmed"
    col_fall = "fallecidos_acum" if "fallecidos_acum" in df.columns else "deaths"

    df = df.sort_values([col_pais, "fecha"])
    if "casos_nuevos" not in df.columns:
        df["casos_nuevos"] = df.groupby(col_pais, sort=False)[col_conf].diff().fillna(0)

    df["_retrocede"] = df["casos_nuevos"] < 0
    df["_sin_reporte"] = (df["casos_nuevos"] == 0) & (df[col_conf] > 100)
    df["_inconsistente"] = df[col_fall] > df[col_conf]

    resumen = (
        df.groupby(col_pais, as_index=False)
        .agg(
            dias_reportados=("fecha", "count"),
            dias_retrocede=("_retrocede", "sum"),
            dias_sin_reporte=("_sin_reporte", "sum"),
            dias_inconsistentes=("_inconsistente", "sum"),
            max_confirmed=(col_conf, "max"),
        )
        .rename(columns={col_pais: "pais"})
    )
    resumen = resumen[resumen["max_confirmed"] >= 1000].copy()
    resumen["pct_dias_retrocede"] = 100.0 * resumen["dias_retrocede"] / resumen["dias_reportados"]
    resumen["pct_dias_sin_reporte"] = 100.0 * resumen["dias_sin_reporte"] / resumen["dias_reportados"]
    resumen["pct_inconsistentes"] = 100.0 * resumen["dias_inconsistentes"] / resumen["dias_reportados"]
    resumen["pct_dias_faltantes"] = (
        100.0 * (TOTAL_DIAS_SERIE - resumen["dias_reportados"].clip(upper=TOTAL_DIAS_SERIE)) / TOTAL_DIAS_SERIE
    )
    return resumen.reset_index(drop=True)


def indice_calidad(problemas: pd.DataFrame, pesos: dict[str, float] | None = None) -> pd.DataFrame:
    """Combina los indicadores de problemas por pais en un indice 0-100 y ordena de peor a mejor."""
    w = pesos or PESOS_DEFAULT
    out = problemas.copy()
    penalizacion = sum(out[col] * peso for col, peso in w.items() if col in out.columns)
    out["indice_calidad"] = (100.0 - penalizacion).clip(0.0, 100.0).round(2)
    return out.sort_values("indice_calidad", ascending=True).reset_index(drop=True)
