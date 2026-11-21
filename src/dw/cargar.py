"""R3 - ETL de la capa limpia (Parquet) al modelo en estrella de PostgreSQL.

Uso:  python -m src.dw.cargar
Orden: crear esquema -> dim_fecha -> dim_territorio -> fact_covid_diario
       -> fuente externa -> vistas -> conciliacion -> exportar a data/dw/
"""
from __future__ import annotations

import pandas as pd

from src import config, db

SQL = config.RAIZ / "sql"


def construir_dim_fecha() -> pd.DataFrame:
    f = pd.date_range(config.FECHA_INICIO, config.FECHA_FIN, freq="D")
    return pd.DataFrame({
        "fecha_key": f.strftime("%Y%m%d").astype(int),
        "fecha": f.date,
        "anio": f.year,
        "trimestre": f.quarter,
        "mes": f.month,
        "nombre_mes": f.strftime("%B"),
        "semana_iso": f.isocalendar().week.to_numpy(),
        "anio_semana_iso": f.isocalendar().year.to_numpy(),
        "dia_semana": f.dayofweek + 1,   # 1 = lunes
        "es_fin_semana": f.dayofweek >= 5,
    })


def construir_dim_territorio() -> pd.DataFrame:
    """Desde la tabla UID: jerarquia pais -> region/estado -> condado, con poblacion.

    TODO(R3):
      - Mapear cada clave_territorio de los reportes a un UID (por combined_key o por
        country/province/admin2). Informar cuantas filas quedan sin UID.
      - Manejar Chile nacional (hasta may-2020) vs 16 regiones + Unknown (excelente R3).
      - Decidir entidades especiales (cruceros, olimpiadas) junto con R2.
    """
    uid = pd.read_csv(config.RAW / "UID_ISO_FIPS_LookUp_Table.csv", dtype={"FIPS": str})
    dim = pd.DataFrame({
        "uid": uid["UID"],
        "iso3": uid["iso3"],
        "pais": uid["Country_Region"],
        "region": uid["Province_State"],
        "condado": uid["Admin2"],
        "combined_key": uid["Combined_Key"],
        "lat": uid["Lat"],
        "long": uid["Long_"],
        "poblacion": uid["Population"],
    })
    dim["nivel"] = "pais"
    dim.loc[dim["region"].notna(), "nivel"] = "region"
    dim.loc[dim["condado"].notna(), "nivel"] = "condado"
    dim.insert(0, "territorio_key", range(1, len(dim) + 1))
    return dim


def construir_fact(df: pd.DataFrame, dim_territorio: pd.DataFrame) -> pd.DataFrame:
    """Grano: territorio x dia. Acumulados + nuevos diarios + banderas de calidad.

    TODO(R3):
      - Asignar territorio_key (ver construir_dim_territorio).
      - casos_nuevos = diff del acumulado por territorio (ordenado por fecha).
      - retrocede = casos_nuevos < 0  (MARCAR, no borrar ni imputar).
      - Conservar archivo_origen y fila_origen (linaje).
    """
    raise NotImplementedError


def conciliar() -> pd.DataFrame:
    """Compara filas y suma de acumulados entre Parquet y DW (como en el taller S10)."""
    raise NotImplementedError("TODO(R3)")


def exportar_dw() -> None:
    """Exporta cada tabla del DW a data/dw/<tabla>.parquet para la entrega."""
    for t in ("dim_fecha", "dim_territorio", "fact_covid_diario", "fact_vacunacion"):
        db.consultar(f"SELECT * FROM {t}").to_parquet(config.DW_EXPORT / f"{t}.parquet", index=False)


def cargar_todo() -> None:
    db.ejecutar_sql(SQL / "01_esquema.sql")
    db.copiar_df(construir_dim_fecha(), "dim_fecha")
    dim_t = construir_dim_territorio()
    db.copiar_df(dim_t, "dim_territorio")
    df = pd.read_parquet(config.PARQUET_UNIFICADO)
    db.copiar_df(construir_fact(df, dim_t), "fact_covid_diario")
    # TODO(R3): cargar fact_vacunacion desde src.externas.owid
    db.ejecutar_sql(SQL / "02_vistas.sql")
    print(conciliar())


if __name__ == "__main__":
    cargar_todo()
