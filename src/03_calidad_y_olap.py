import duckdb
import pandas as pd
import numpy as np

DW_PATH = "data/dw_covid.duckdb"
PARQUET_PATH = "data/clean/reportes_unificados.parquet"
TS_CONFIRMED = "data/raw/time_series/confirmed_global.csv"


def evaluar_calidad():
    con = duckdb.connect(DW_PATH, read_only=True)

    total_filas = con.execute("SELECT COUNT(*) FROM fact_covid").fetchone()[0]

    # 1. COMPLETITUD: nulos en lat/long o population en territorios activos
    nulos_pob = con.execute("""
        SELECT COUNT(*) FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        WHERE t.population IS NULL OR t.population <= 0
    """).fetchone()[0]

    # 2. UNICIDAD: duplicados de (fecha_reporte, combined_key) en la capa unificada
    duplicados = con.execute(f"""
        SELECT COUNT(*) - COUNT(DISTINCT (fecha_reporte || '|' || combined_key))
        FROM read_parquet('{PARQUET_PATH}')
    """).fetchone()[0]

    # 3. VALIDEZ: coordenadas fuera de rango geográfico o negativos en acumulados
    fuera_rango = con.execute("""
        SELECT COUNT(*) FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        WHERE f.confirmed < 0 OR f.deaths < 0
           OR t.lat < -90 OR t.lat > 90
           OR t.long < -180 OR t.long > 180
    """).fetchone()[0]

    # 4. CONSISTENCIA: fallecidos mayores que casos confirmados
    muertes_gt_casos = con.execute("""
        SELECT COUNT(*) FROM fact_covid WHERE deaths > confirmed
    """).fetchone()[0]

    # 5. EXACTITUD: acumulados que retroceden (casos_nuevos < 0)
    retrocede_casos = con.execute("""
        SELECT COUNT(*) FROM fact_covid WHERE retrocede_casos
    """).fetchone()[0]

    # Picos por rezagos (> 5x media móvil 14d y > 500 casos)
    picos_rezago = con.execute("""
        WITH stats AS (
            SELECT
                territorio_key,
                fecha_key,
                casos_nuevos,
                AVG(CASE WHEN casos_nuevos >= 0 THEN casos_nuevos END)
                    OVER (PARTITION BY territorio_key ORDER BY fecha_key ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS media_14d
            FROM fact_covid
        )
        SELECT COUNT(*) FROM stats
        WHERE casos_nuevos > 500 AND media_14d > 0 AND casos_nuevos > 5 * media_14d
    """).fetchone()[0]

    # 6. OPORTUNIDAD: días sin reporte (2022-2023, países >100k casos)
    dias_sin_reporte = con.execute("""
        WITH pais_dia AS (
            SELECT
                t.country_region,
                d.anio,
                f.fecha_key,
                SUM(f.casos_nuevos) AS nuevos,
                SUM(f.confirmed) AS acum
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE NOT t.es_entidad_especial
            GROUP BY 1, 2, 3
        )
        SELECT COUNT(*) FROM pais_dia
        WHERE anio >= 2022 AND acum > 100000 AND nuevos = 0
    """).fetchone()[0]

    reglas = [
        ("Completitud", "Territorios sin población en UID", nulos_pob, total_filas, 5.0, False),
        ("Unicidad", "Duplicados (fecha × territorio) en crudo", duplicados, total_filas, 0.01, True),
        ("Validez", "Acumulados negativos o coords fuera de rango", fuera_rango, total_filas, 0.1, True),
        ("Consistencia", "Fallecidos mayores que confirmados", muertes_gt_casos, total_filas, 0.05, True),
        ("Exactitud", "Días con acumulado que retrocede", retrocede_casos, total_filas, 1.0, False),
        ("Exactitud", "Picos bruscos por acumulación de rezagos", picos_rezago, total_filas, 0.5, False),
        ("Oportunidad", "Días sin reporte (0 nuevos en 2022-23)", dias_sin_reporte, total_filas, 1.0, False),
    ]

    df_reglas = pd.DataFrame([
        {
            "dimension": dim,
            "regla": r,
            "filas_afectadas": n,
            "pct": round(n / tot * 100, 4),
            "umbral_pct": umb,
            "estado": ("RECHAZA" if crit else "ALERTA") if (n / tot * 100) > umb else "OK",
        }
        for dim, r, n, tot, umb, crit in reglas
    ])
    df_reglas.to_csv("data/clean/reglas_calidad.csv", index=False)

    print("\n--- R2 · TABLA DE REGLAS EJECUTABLES (6 DIMENSIONES) ---")
    print(df_reglas.to_string(index=False))

    # --- Diferencias entre time_series y suma de daily_reports (al último día: 2023-03-09) ---
    ts = pd.read_csv(TS_CONFIRMED)
    ts_pais = ts.groupby("Country/Region")["3/9/23"].sum().reset_index()
    ts_pais.columns = ["country_region", "confirmed_ts"]

    dr_pais = con.execute("""
        SELECT t.country_region, SUM(f.confirmed) AS confirmed_dr
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        WHERE f.fecha_key = 20230309
        GROUP BY 1
    """).df()

    diff_df = ts_pais.merge(dr_pais, on="country_region", how="outer").fillna(0)
    diff_df["diferencia"] = (diff_df["confirmed_dr"] - diff_df["confirmed_ts"]).abs()
    paises_con_diff = diff_df[diff_df["diferencia"] > 0].sort_values("diferencia", ascending=False)
    print(f"\n--- R2 · CRUCE TIME_SERIES VS DAILY_REPORTS (2023-03-09) ---")
    print(f"Países con diferencia > 0: {len(paises_con_diff)} | Diferencia máx.: {paises_con_diff['diferencia'].max():,.0f}")
    if len(paises_con_diff) > 0:
        print(paises_con_diff.head(5).to_string(index=False))

    # --- Índice de calidad por país (0 a 100) para P4 ---
    indice = con.execute("""
        WITH pais_dia AS (
            SELECT
                t.country_region,
                f.fecha_key,
                SUM(f.confirmed) AS confirmed,
                SUM(f.deaths) AS deaths,
                SUM(f.casos_nuevos) AS casos_nuevos,
                MAX(CASE WHEN f.deaths > f.confirmed THEN 1 ELSE 0 END) AS flag_inconsistente
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            WHERE NOT t.es_entidad_especial
            GROUP BY 1, 2
        ),
        resumen AS (
            SELECT
                country_region,
                COUNT(*) AS dias_reportados,
                SUM(CASE WHEN casos_nuevos < 0 THEN 1 ELSE 0 END) AS dias_retrocede,
                SUM(CASE WHEN casos_nuevos = 0 AND confirmed > 100 THEN 1 ELSE 0 END) AS dias_sin_cambio,
                SUM(flag_inconsistente) AS dias_inconsistentes,
                MAX(confirmed) AS max_confirmed
            FROM pais_dia
            GROUP BY 1
            HAVING MAX(confirmed) >= 1000
        )
        SELECT
            country_region,
            dias_reportados,
            dias_retrocede,
            dias_sin_cambio,
            dias_inconsistentes,
            ROUND(100.0
                - (dias_retrocede * 100.0 / dias_reportados) * 3.0
                - (dias_sin_cambio * 100.0 / dias_reportados) * 0.5
                - (dias_inconsistentes * 100.0 / dias_reportados) * 5.0
                - ((1143 - LEAST(dias_reportados, 1143)) * 100.0 / 1143) * 0.5
            , 2) AS indice_calidad
        FROM resumen
        ORDER BY indice_calidad ASC
    """).df()
    indice["indice_calidad"] = indice["indice_calidad"].clip(0, 100)
    indice.to_csv("data/clean/indice_calidad_paises.csv", index=False)

    print("\n--- P4 · TOP 10 PAÍSES CON PEOR ÍNDICE DE CALIDAD ---")
    print(indice.head(10).to_string(index=False))

    # --- R3 · Consultas OLAP sobre el DW ---
    print("\n--- R3 · CONSULTAS OLAP SOBRE DUCKDB ---")
    # 1. ROLL-UP: casos nuevos globales por año y trimestre
    rollup = con.execute("""
        SELECT d.anio, d.trimestre, CAST(SUM(GREATEST(f.casos_nuevos, 0)) AS BIGINT) AS casos_nuevos
        FROM fact_covid f
        JOIN dim_fecha d ON f.fecha_key = d.fecha_key
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    print("\n[OLAP · Roll-up] Casos nuevos por año y trimestre (primeros 6):")
    print(rollup.head(6).to_string(index=False))

    # 2. SLICE: solo Chile por año
    slice_cl = con.execute("""
        SELECT d.anio,
               CAST(SUM(GREATEST(f.casos_nuevos, 0)) AS BIGINT) AS casos_nuevos,
               CAST(SUM(GREATEST(f.fallecidos_nuevos, 0)) AS BIGINT) AS fallecidos_nuevos
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        JOIN dim_fecha d ON f.fecha_key = d.fecha_key
        WHERE t.country_region = 'Chile'
        GROUP BY 1 ORDER BY 1
    """).df()
    print("\n[OLAP · Slice] Chile por año:")
    print(slice_cl.to_string(index=False))

    # 3. DRILL-DOWN + DICE: Regiones de Chile en invierno 2021 (jun-ago 2021)
    dice_cl = con.execute("""
        SELECT t.province_state AS region,
               t.population,
               CAST(SUM(GREATEST(f.casos_nuevos, 0)) AS BIGINT) AS casos_inv_2021,
               ROUND(SUM(GREATEST(f.casos_nuevos, 0)) * 100000.0 / NULLIF(t.population, 0), 1) AS tasa_100k
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        JOIN dim_fecha d ON f.fecha_key = d.fecha_key
        WHERE t.country_region = 'Chile'
          AND t.province_state IS NOT NULL
          AND t.province_state <> 'Unknown'
          AND d.anio = 2021 AND d.mes IN (6, 7, 8)
        GROUP BY 1, 2
        ORDER BY tasa_100k DESC
        LIMIT 8
    """).df()
    print("\n[OLAP · Dice + Drill-down] Top regiones de Chile · Invierno 2021 (tasa por 100k):")
    print(dice_cl.to_string(index=False))

    con.close()


if __name__ == "__main__":
    evaluar_calidad()