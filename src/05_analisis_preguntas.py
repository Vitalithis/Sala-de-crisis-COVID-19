import os
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DW_PATH = "data/dw_covid.duckdb"
FIG_DIR = "docs/figuras"
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def ejecutar_analisis():
    con = duckdb.connect(DW_PATH, read_only=True)

    # =========================================================================
    # P1 · Chile frente a Sudamérica (tasas por 100.000 habitantes)
    # =========================================================================
    sudamerica = [
        "Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
        "Ecuador", "Paraguay", "Peru", "Uruguay", "Venezuela",
    ]
    placeholders = ",".join([f"'{p}'" for p in sudamerica])

    p1 = con.execute(f"""
        WITH pob AS (
            SELECT country_region,
                   COALESCE(
                       MAX(CASE WHEN nivel_granularidad = 'pais' THEN population END),
                       SUM(CASE WHEN nivel_granularidad = 'region_estado' THEN population END),
                       SUM(population)
                   ) AS population
            FROM dim_territorio
            WHERE country_region IN ({placeholders}) AND NOT es_entidad_especial
            GROUP BY 1
        ),
        ult AS (
            SELECT t.country_region,
                   SUM(f.confirmed) AS confirmed,
                   SUM(f.deaths) AS deaths
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            WHERE f.fecha_key = 20230309 AND t.country_region IN ({placeholders})
            GROUP BY 1
        )
        SELECT u.country_region, p.population, u.confirmed, u.deaths,
               ROUND(u.confirmed * 100000.0 / p.population, 1) AS casos_100k,
               ROUND(u.deaths * 100000.0 / p.population, 1) AS fallecidos_100k
        FROM ult u JOIN pob p ON u.country_region = p.country_region
        ORDER BY fallecidos_100k DESC
    """).df()

    print("\n--- P1 · CHILE FRENTE A SUDAMÉRICA (al 2023-03-09) ---")
    print(p1.to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    p1_c = p1.sort_values("casos_100k")
    colores_c = ["#D00120" if x == "Chile" else "#4A5F7A" for x in p1_c["country_region"]]
    axes[0].barh(p1_c["country_region"], p1_c["casos_100k"], color=colores_c)
    axes[0].set_title("Casos acumulados por 100.000 hab.")
    axes[0].set_xlabel("Casos por 100.000 habitantes")
    axes[0].grid(alpha=0.3, axis="x")

    p1_f = p1.sort_values("fallecidos_100k")
    colores_f = ["#D00120" if x == "Chile" else "#4A5F7A" for x in p1_f["country_region"]]
    axes[1].barh(p1_f["country_region"], p1_f["fallecidos_100k"], color=colores_f)
    axes[1].set_title("Fallecidos acumulados por 100.000 hab.")
    axes[1].set_xlabel("Fallecidos por 100.000 habitantes")
    axes[1].grid(alpha=0.3, axis="x")

    fig.suptitle("P1 · Chile fue 2° en casos y 2° en mortalidad por 100.000 hab. en Sudamérica", fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/p1_sudamerica.png", dpi=150)
    plt.close(fig)

    # =========================================================================
    # P2 · Regiones de Chile más golpeadas (desde junio 2020) y posición de Biobío
    # =========================================================================
    p2 = con.execute("""
        SELECT t.province_state AS region,
               t.population,
               SUM(f.confirmed) AS confirmed,
               SUM(f.deaths) AS deaths,
               ROUND(SUM(f.confirmed) * 100000.0 / NULLIF(t.population, 0), 1) AS casos_100k,
               ROUND(SUM(f.deaths) * 100000.0 / NULLIF(t.population, 0), 1) AS fallecidos_100k
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        WHERE t.country_region = 'Chile'
          AND t.province_state IS NOT NULL
          AND t.province_state <> 'Unknown'
          AND f.fecha_key = 20230309
        GROUP BY 1, 2
        ORDER BY casos_100k DESC
    """).df()

    p2["rank_casos"] = range(1, len(p2) + 1)
    p2["rank_fallecidos"] = p2["fallecidos_100k"].rank(ascending=False).astype(int)
    print("\n--- P2 · REGIONES DE CHILE (al 2023-03-09) ---")
    print(p2.to_string(index=False))

    biobio = p2[p2["region"] == "Biobio"].iloc[0]
    print(f"\n>>> Posición de Biobío: #{biobio['rank_casos']} en casos/100k ({biobio['casos_100k']}) "
          f"y #{biobio['rank_fallecidos']} en fallecidos/100k ({biobio['fallecidos_100k']})")

    fig, ax = plt.subplots(figsize=(9, 5))
    p2_ord = p2.sort_values("casos_100k")
    colores_r = ["#D00120" if r == "Biobio" else "#4A5F7A" for r in p2_ord["region"]]
    ax.barh(p2_ord["region"], p2_ord["casos_100k"], color=colores_r)
    ax.set_title("P2 · Incidencia acumulada por región de Chile (Biobío destacado en rojo)")
    ax.set_xlabel("Casos acumulados por 100.000 habitantes")
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/p2_regiones_chile.png", dpi=150)
    plt.close(fig)

    # =========================================================================
    # P3 · Letalidad aparente mensual vs % vacunación (Chile + 3 países)
    # =========================================================================
    paises_p3 = ["Chile", "Argentina", "Peru", "Uruguay"]
    ph3 = ",".join([f"'{p}'" for p in paises_p3])

    p3 = con.execute(f"""
        WITH cov_mes AS (
            SELECT t.country_region, d.anio_mes,
                   SUM(GREATEST(f.casos_nuevos, 0)) AS casos_mes,
                   SUM(GREATEST(f.fallecidos_nuevos, 0)) AS muertes_mes
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE t.country_region IN ({ph3})
              AND d.fecha BETWEEN '2020-04-01' AND '2022-12-31'
            GROUP BY 1, 2
        ),
        vac_mes AS (
            SELECT t.country_region, d.anio_mes,
                   MAX(v.pct_vacunacion_completa) AS pct_vac
            FROM fact_vacunacion v
            JOIN dim_fecha d ON v.fecha_key = d.fecha_key
            JOIN (SELECT DISTINCT country_region, iso3 FROM dim_territorio WHERE iso3 IS NOT NULL) t
              ON v.iso3 = t.iso3
            WHERE t.country_region IN ({ph3})
            GROUP BY 1, 2
        )
        SELECT c.country_region, c.anio_mes, c.casos_mes, c.muertes_mes,
               ROUND(c.muertes_mes * 100.0 / NULLIF(c.casos_mes, 0), 2) AS letalidad_pct,
               COALESCE(v.pct_vac, 0) AS pct_vac
        FROM cov_mes c
        LEFT JOIN vac_mes v ON c.country_region = v.country_region AND c.anio_mes = v.anio_mes
        ORDER BY 1, 2
    """).df()

    # Resumen pre vs post 50% vacunación
    print("\n--- P3 · LETALIDAD APARENTE ANTES VS DESPUÉS DE 50% VACUNACIÓN COMPLETA ---")
    for pais in paises_p3:
        sub = p3[p3["country_region"] == pais]
        antes = sub[sub["pct_vac"] < 50]["letalidad_pct"].median()
        despues = sub[sub["pct_vac"] >= 50]["letalidad_pct"].median()
        print(f"  {pais:<10} | Mediana letalidad (<50% vac): {antes:.2f}%  →  (>=50% vac): {despues:.2f}%")

    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for ax, pais in zip(axes.flat, paises_p3):
        sub = p3[p3["country_region"] == pais].copy()
        sub["dt"] = pd.to_datetime(sub["anio_mes"] + "-01")
        ax.plot(sub["dt"], sub["letalidad_pct"].clip(upper=12), color="#D00120", linewidth=2, label="Letalidad aparente (%)")
        ax.set_ylabel("Letalidad (%)", color="#D00120")
        ax.set_title(pais)
        ax.grid(alpha=0.3)

        ax2 = ax.twinx()
        ax2.fill_between(sub["dt"], sub["pct_vac"], alpha=0.2, color="#1B7F5C", label="% Vacunación completa")
        ax2.set_ylim(0, 105)
        ax2.set_ylabel("% Vacunación", color="#1B7F5C")

    fig.suptitle("P3 · La letalidad aparente cae al avanzar la vacunación (sujeta a cambios en testeo)", fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/p3_letalidad_vacunacion.png", dpi=150)
    plt.close(fig)

    # =========================================================================
    # P7 · Pregunta propia (OWID): ¿Mayor vacunación al cierre de 2021 se asocia
    #      con menor mortalidad por 100.000 habitantes durante 2022?
    # =========================================================================
    p7 = con.execute("""
        WITH pob AS (
            SELECT country_region,
                   MAX(iso3) AS iso3,
                   COALESCE(
                       MAX(CASE WHEN nivel_granularidad = 'pais' THEN population END),
                       SUM(CASE WHEN nivel_granularidad = 'region_estado' THEN population END),
                       SUM(population)
                   ) AS population
            FROM dim_territorio
            WHERE NOT es_entidad_especial AND iso3 IS NOT NULL
            GROUP BY 1
            HAVING population >= 1000000
        ),
        vac_2021 AS (
            SELECT iso3, MAX(pct_vacunacion_completa) AS vac_dic_2021
            FROM fact_vacunacion
            WHERE fecha_key <= 20211231
            GROUP BY 1
        ),
        muertes_2022 AS (
            SELECT t.country_region,
                   SUM(GREATEST(f.fallecidos_nuevos, 0)) AS muertes_2022
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE d.anio = 2022 AND NOT t.es_entidad_especial
            GROUP BY 1
        )
        SELECT p.country_region, p.population,
               ROUND(v.vac_dic_2021, 1) AS vac_dic_2021,
               ROUND(m.muertes_2022 * 100000.0 / p.population, 1) AS mortalidad_2022_100k,
               ROUND(w.pct_pob_65mas, 1) AS pct_pob_65mas
        FROM pob p
        JOIN vac_2021 v ON p.iso3 = v.iso3
        JOIN muertes_2022 m ON p.country_region = m.country_region
        LEFT JOIN dim_indicadores_wb w ON p.iso3 = w.iso3
        WHERE v.vac_dic_2021 IS NOT NULL
    """).df()

    corr = p7["vac_dic_2021"].corr(p7["mortalidad_2022_100k"])
    corr_edad = p7["pct_pob_65mas"].corr(p7["mortalidad_2022_100k"])
    corr_vac_edad = p7["vac_dic_2021"].corr(p7["pct_pob_65mas"])
    print(f"\n--- P7 · VACUNACIÓN AL CIERRE 2021 VS MORTALIDAD 2022 (n={len(p7)} países >= 1M hab.) ---")
    print(f"Correlación de Pearson vacunación vs mortalidad 2022: r = {corr:.3f}")
    print(f"Factor de confusión (Banco Mundial): % pob >=65 años vs mortalidad 2022: r = {corr_edad:.3f} | vacunación vs >=65 años: r = {corr_vac_edad:.3f}")

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.scatter(p7["vac_dic_2021"], p7["mortalidad_2022_100k"], alpha=0.65, color="#4A5F7A")
    cl_row = p7[p7["country_region"] == "Chile"]
    if not cl_row.empty:
        ax.scatter(cl_row["vac_dic_2021"], cl_row["mortalidad_2022_100k"], color="#D00120", s=80, label="Chile", zorder=5)
        ax.annotate("Chile", (cl_row["vac_dic_2021"].values[0] + 1, cl_row["mortalidad_2022_100k"].values[0] + 2), color="#D00120", fontweight="bold")
    ax.set_title(f"P7 · Vacunación a dic-2021 vs. Mortalidad 2022 (r = {corr:.2f}, n = {len(p7)} países)")
    ax.set_xlabel("% Población con vacunación completa al 31-dic-2021 (OWID)")
    ax.set_ylabel("Fallecidos en 2022 por 100.000 habitantes")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/p7_vacunacion_vs_mortalidad.png", dpi=150)
    plt.close(fig)

    # =========================================================================
    # R6 · Medición de control de divulgación (celdas pequeñas: pob < 50k y 1..4)
    # =========================================================================
    r6 = con.execute("""
        SELECT
            COUNT(*) AS total_filas_pob_conocida,
            SUM(CASE WHEN t.population < 50000 AND f.casos_nuevos BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS celdas_suprimidas_casos,
            SUM(CASE WHEN t.population < 50000 AND f.fallecidos_nuevos BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS celdas_suprimidas_muertes,
            COUNT(DISTINCT CASE WHEN t.country_region = 'US' AND t.nivel_granularidad = 'condado' AND t.population < 5000 THEN t.territorio_key END) AS condados_us_bajo_5k
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        WHERE t.population > 0
    """).df()
    print("\n--- R6 · CONTROL DE DIVULGACIÓN (CELDAS PEQUEÑAS 1-4 EN POB < 50.000) ---")
    print(r6.to_string(index=False))

    con.close()
    print(f"\n[LISTO] Gráficos guardados en {FIG_DIR}/")


if __name__ == "__main__":
    ejecutar_analisis()