import duckdb
import pandas as pd

DW_PATH = "data/dw_covid.duckdb"
PARQUET_PATH = "data/clean/reportes_unificados.parquet"
UID_PATH = "data/raw/UID_ISO_FIPS_LookUp_Table.csv"
OWID_PATH = "data/raw/owid_vaccinations.csv"


def construir_dw():
    con = duckdb.connect(DW_PATH)

    print("1/5 · Generando dim_fecha...")
    fechas = pd.date_range("2020-01-22", "2023-03-09", freq="D")
    dim_fecha = pd.DataFrame({
        "fecha_key": fechas.strftime("%Y%m%d").astype(int),
        "fecha": fechas.strftime("%Y-%m-%d"),
        "anio": fechas.year,
        "mes": fechas.month,
        "anio_mes": fechas.strftime("%Y-%m"),
        "trimestre": "T" + fechas.quarter.astype(str),
        "semana_anio": fechas.isocalendar().week.astype(int).values,
        "dia_semana": fechas.dayofweek,
        "es_fin_semana": (fechas.dayofweek >= 5).astype(int),
    })
    con.execute("CREATE OR REPLACE TABLE dim_fecha AS SELECT * FROM dim_fecha")

    print("2/5 · Generando dim_territorio (desde tabla UID + territorios no listados)...")
    con.execute(f"""
        CREATE OR REPLACE TABLE stg_uid AS
        SELECT
            TRIM(Combined_Key) AS combined_key,
            TRIM(Country_Region) AS country_region,
            NULLIF(TRIM(Province_State), '') AS province_state,
            NULLIF(TRIM(Admin2), '') AS admin2,
            NULLIF(TRIM(iso3), '') AS iso3,
            TRY_CAST(Population AS BIGINT) AS population,
            TRY_CAST(Lat AS DOUBLE) AS lat,
            TRY_CAST(Long_ AS DOUBLE) AS long,
            TRUE AS en_uid
        FROM read_csv_auto('{UID_PATH}', all_varchar=TRUE)
    """)

    # Unir territorios presentes en los reportes que puedan faltar en UID
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_territorio AS
        WITH reportes_terr AS (
            SELECT DISTINCT
                TRIM(combined_key) AS combined_key,
                FIRST(country_region) AS country_region,
                FIRST(province_state) AS province_state,
                FIRST(admin2) AS admin2,
                FIRST(lat) AS lat,
                FIRST(long) AS long
            FROM read_parquet('{PARQUET_PATH}')
            WHERE combined_key IS NOT NULL
            GROUP BY TRIM(combined_key)
        ),
        unidos AS (
            SELECT
                r.combined_key,
                COALESCE(u.country_region, r.country_region) AS country_region,
                COALESCE(u.province_state, r.province_state) AS province_state,
                COALESCE(u.admin2, r.admin2) AS admin2,
                u.iso3,
                u.population,
                COALESCE(u.lat, r.lat) AS lat,
                COALESCE(u.long, r.long) AS long,
                COALESCE(u.en_uid, FALSE) AS en_uid
            FROM reportes_terr r
            LEFT JOIN stg_uid u ON r.combined_key = u.combined_key
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY combined_key) AS territorio_key,
            *,
            CASE
                WHEN admin2 IS NOT NULL THEN 'condado'
                WHEN province_state IS NOT NULL THEN 'region_estado'
                ELSE 'pais'
            END AS nivel_granularidad,
            CASE
                WHEN country_region IN ('Diamond Princess', 'MS Zaandam', 'Summer Olympics 2020', 'Winter Olympics 2022', 'Antarctica')
                     OR province_state IN ('Diamond Princess', 'Grand Princess', 'Unknown')
                THEN TRUE ELSE FALSE
            END AS es_entidad_especial
        FROM unidos
    """)

    print("3/5 · Construyendo fact_covid (grano: territorio x día)...")
    # Deduplicar si en un mismo reporte diario aparece el mismo combined_key más de una vez
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_covid AS
        WITH base AS (
            SELECT
                CAST(REPLACE(r.fecha_reporte, '-', '') AS INTEGER) AS fecha_key,
                r.fecha_reporte,
                t.territorio_key,
                r.esquema,
                MAX(r.confirmed) AS confirmed,
                MAX(r.deaths) AS deaths,
                MAX(r.recovered) AS recovered,
                MAX(r.active) AS active,
                MAX(r.incident_rate) AS incident_rate,
                MAX(r.case_fatality_ratio) AS case_fatality_ratio
            FROM read_parquet('{PARQUET_PATH}') r
            JOIN dim_territorio t ON TRIM(r.combined_key) = t.combined_key
            GROUP BY 1, 2, 3, 4
        ),
        con_deltas AS (
            SELECT
                *,
                confirmed - LAG(confirmed) OVER (PARTITION BY territorio_key ORDER BY fecha_key) AS casos_nuevos,
                deaths - LAG(deaths) OVER (PARTITION BY territorio_key ORDER BY fecha_key) AS fallecidos_nuevos
            FROM base
        )
        SELECT
            fecha_key,
            territorio_key,
            esquema,
            confirmed,
            deaths,
            recovered,
            active,
            casos_nuevos,
            fallecidos_nuevos,
            CASE WHEN casos_nuevos < 0 THEN TRUE ELSE FALSE END AS retrocede_casos,
            CASE WHEN fallecidos_nuevos < 0 THEN TRUE ELSE FALSE END AS retrocede_fallecidos,
            incident_rate,
            case_fatality_ratio
        FROM con_deltas
    """)

    print("4/5 · Integrando fuente externa OWID (vacunación) por código ISO3...")
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_vacunacion AS
        SELECT
            CAST(REPLACE(date, '-', '') AS INTEGER) AS fecha_key,
            TRIM(iso_code) AS iso3,
            location,
            TRY_CAST(total_vaccinations AS DOUBLE) AS total_vaccinations,
            TRY_CAST(people_vaccinated AS DOUBLE) AS people_vaccinated,
            TRY_CAST(people_fully_vaccinated AS DOUBLE) AS people_fully_vaccinated,
            TRY_CAST(people_vaccinated_per_hundred AS DOUBLE) AS pct_vacunados_1_dosis,
            TRY_CAST(people_fully_vaccinated_per_hundred AS DOUBLE) AS pct_vacunacion_completa
        FROM read_csv_auto('{OWID_PATH}', all_varchar=TRUE)
        WHERE date BETWEEN '2020-01-22' AND '2023-03-09'
          AND iso_code NOT LIKE 'OWID_%'
    """)

    print("5/5 · Conciliación de carga y tasa de cruce ISO3...")
    raw_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    fact_rows = con.execute("SELECT COUNT(*) FROM fact_covid").fetchone()[0]
    retro_casos = con.execute("SELECT COUNT(*) FROM fact_covid WHERE retrocede_casos").fetchone()[0]

    # Tasa de cruce a nivel de países distintos en dim_territorio vs OWID
    paises_dw = con.execute("""
        SELECT COUNT(DISTINCT country_region) FROM dim_territorio
    """).fetchone()[0]
    paises_cruzan = con.execute("""
        SELECT COUNT(DISTINCT t.country_region)
        FROM dim_territorio t
        INNER JOIN fact_vacunacion v ON t.iso3 = v.iso3
    """).fetchone()[0]
    sin_cruce = con.execute("""
        SELECT DISTINCT t.country_region, t.iso3
        FROM dim_territorio t
        LEFT JOIN (SELECT DISTINCT iso3 FROM fact_vacunacion) v ON t.iso3 = v.iso3
        WHERE v.iso3 IS NULL
        ORDER BY t.country_region
    """).df()

    print("\n--- RESUMEN R3 (Conciliación y Cruce ISO3) ---")
    print(f"Filas en Parquet unificado  : {raw_rows:,}")
    print(f"Filas en fact_covid         : {fact_rows:,} (duplicados consolidados: {raw_rows - fact_rows:,})")
    print(f"Días con acumulado que baja : {retro_casos:,}")
    print(f"Países/entidades en DW      : {paises_dw}")
    print(f"Cruzan con OWID por ISO3    : {paises_cruzan} ({paises_cruzan/paises_dw*100:.1f} %)")
    print(f"Sin cruce ({len(sin_cruce)}): {sin_cruce['country_region'].tolist()}")

    con.execute("DROP TABLE IF EXISTS stg_uid")
    con.close()
    print(f"\n[LISTO] Data Warehouse guardado en: {DW_PATH}")


if __name__ == "__main__":
    construir_dw()