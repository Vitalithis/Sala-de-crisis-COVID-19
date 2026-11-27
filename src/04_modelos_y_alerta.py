import warnings
import duckdb
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from statsmodels.tsa.holtwinters import Holt
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

DW_PATH = "data/dw_covid.duckdb"


def obtener_serie_territorio(territorio: str, fecha_corte: str = None, dw_path: str = DW_PATH) -> pd.DataFrame:
    """
    Devuelve la serie diaria limpia (casos nuevos, media móvil 7d, incidencia 100k)
    para un país (ej. 'Chile') o una región de Chile (ej. 'Biobio').
    Si fecha_corte se entrega, filtra ESTRICTAMENTE fecha <= fecha_corte (sin fuga de datos).
    """
    con = duckdb.connect(dw_path, read_only=True)

    # Detectar si es país o región de Chile
    es_pais = con.execute(
        "SELECT COUNT(*) FROM dim_territorio WHERE country_region = ?", [territorio]
    ).fetchone()[0] > 0

    filtro_fecha = f"AND d.fecha <= '{fecha_corte}'" if fecha_corte else ""

    if es_pais:
        # Población a nivel país (evita sumar doble entre nivel país y regiones)
        pob = con.execute("""
            SELECT COALESCE(
                MAX(CASE WHEN nivel_granularidad = 'pais' THEN population END),
                SUM(CASE WHEN nivel_granularidad = 'region_estado' THEN population END),
                SUM(population)
            )
            FROM dim_territorio WHERE country_region = ?
        """, [territorio]).fetchone()[0]

        df = con.execute(f"""
            SELECT
                CAST(d.fecha AS DATE) AS fecha,
                SUM(f.confirmed) AS confirmed,
                SUM(f.deaths) AS deaths
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE t.country_region = ? {filtro_fecha}
            GROUP BY 1 ORDER BY 1
        """, [territorio]).df()
    else:
        pob = con.execute("""
            SELECT MAX(population) FROM dim_territorio
            WHERE country_region = 'Chile' AND province_state = ?
        """, [territorio]).fetchone()[0]

        df = con.execute(f"""
            SELECT
                CAST(d.fecha AS DATE) AS fecha,
                SUM(f.confirmed) AS confirmed,
                SUM(f.deaths) AS deaths
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE t.country_region = 'Chile' AND t.province_state = ? {filtro_fecha}
            GROUP BY 1 ORDER BY 1
        """, [territorio]).df()

    con.close()

    if df.empty:
        raise ValueError(f"Sin datos para '{territorio}' hasta {fecha_corte}")

    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    # Casos diarios desde el acumulado agregado (evita artefactos al cambiar granularidad)
    df["casos_nuevos"] = df["confirmed"].diff().clip(lower=0).fillna(0)
    df["fallecidos_nuevos"] = df["deaths"].diff().clip(lower=0).fillna(0)
    df["mm7_casos"] = df["casos_nuevos"].rolling(7, min_periods=1).mean()
    df["population"] = pob if pob and pob > 0 else np.nan
    df["incidencia_100k_7d"] = (df["casos_nuevos"].rolling(7, min_periods=1).sum() / df["population"]) * 100_000
    return df


def pronosticar(territorio: str, fecha_corte: str, horizonte: int = 14, dw_path: str = DW_PATH) -> pd.DataFrame:
    """
    Pronostica casos diarios (media móvil 7d) para los próximos `horizonte` días
    usando SOLO datos <= fecha_corte. Compara 3 modelos:
      1) modelo_base: Media Móvil 7 días constante (persistencia)
      2) modelo_holt: Suavizamiento Exponencial de Holt con tendencia amortiguada
      3) modelo_arima: ARIMA(1,1,1) autorregresivo integrado de media móvil
    """
    hist = obtener_serie_territorio(territorio, fecha_corte=fecha_corte, dw_path=dw_path)
    serie = hist["mm7_casos"].tail(90).values  # ventana reciente de 90 días

    if len(serie) < 14:
        raise ValueError(f"Muy pocos datos históricos ({len(serie)} días) para pronosticar.")

    ultima_fecha = hist["fecha"].iloc[-1]
    fechas_fut = pd.date_range(ultima_fecha + pd.Timedelta(days=1), periods=horizonte, freq="D")

    # Modelo 1 (base): promedio de los últimos 7 días
    pred_base = np.full(horizonte, float(np.mean(serie[-7:])))

    # Modelo 2 (Holt amortiguado): captura tendencia reciente sin explotar exponencialmente
    try:
        ajuste = Holt(serie, damped_trend=True, initialization_method="estimated").fit(
            smoothing_level=0.4, smoothing_trend=0.2, damping_trend=0.85, optimized=False
        )
        pred_holt = np.clip(ajuste.forecast(horizonte), 0, None)
    except Exception:
        pred_holt = pred_base.copy()

    # Modelo 3 (ARIMA(1,1,1)): dinámica autorregresiva sobre serie diferenciada
    try:
        ajuste_arima = ARIMA(serie, order=(1, 1, 1)).fit()
        pred_arima = np.clip(ajuste_arima.forecast(steps=horizonte), 0, None)
    except Exception:
        pred_arima = pred_base.copy()

    return pd.DataFrame({
        "fecha": fechas_fut,
        "pred_base_mm7": np.round(pred_base, 1),
        "pred_holt": np.round(pred_holt, 1),
        "pred_arima": np.round(pred_arima, 1),
    })


def alerta(territorio: str, fecha: str, umbral_var_pct: float = 25.0, umbral_inc: float = 35.0, dw_path: str = DW_PATH) -> dict:
    """
    Indicador de alerta temprana (usando solo datos <= fecha):
    Se activa si la incidencia acumulada de 7 días por 100k habitantes supera `umbral_inc`
    Y creció al menos `umbral_var_pct` % respecto a los 7 días previos.
    """
    hist = obtener_serie_territorio(territorio, fecha_corte=fecha, dw_path=dw_path)
    if len(hist) < 15:
        return {"activa": False, "incidencia_7d": 0.0, "variacion_semanal_pct": 0.0, "motivo": "Histórico insuficiente"}

    inc_actual = float(hist["incidencia_100k_7d"].iloc[-1])
    inc_previa = float(hist["incidencia_100k_7d"].iloc[-8])
    var_pct = ((inc_actual - inc_previa) / inc_previa * 100.0) if inc_previa > 0 else 0.0

    activa = (inc_actual >= umbral_inc) and (var_pct >= umbral_var_pct)
    return {
        "territorio": territorio,
        "fecha": str(hist["fecha"].iloc[-1].date()),
        "activa": bool(activa),
        "incidencia_7d": round(inc_actual, 2),
        "variacion_semanal_pct": round(var_pct, 1),
        "umbral_inc": umbral_inc,
        "umbral_var_pct": umbral_var_pct,
    }


def ejecutar_backtesting_y_evaluacion():
    print("--- R5 / P6 · BACKTESTING EN 3 FECHAS DE CORTE (CHILE, HORIZONTE=14 DÍAS) ---")
    cortes = [
        ("2021-03-15", "Ola 2 (otoño 2021)"),
        ("2021-12-28", "P6 · Inicio Ómicron"),
        ("2022-05-15", "Ola invierno 2022"),
    ]
    real_full = obtener_serie_territorio("Chile")
    resultados_bt = []

    for corte, etiqueta in cortes:
        pred = pronosticar("Chile", corte, horizonte=14)
        comp = pred.merge(real_full[["fecha", "mm7_casos"]], on="fecha", how="inner")
        for col_m, nombre_m in [
            ("pred_base_mm7", "Base (MM7)"),
            ("pred_holt", "Holt amortiguado"),
            ("pred_arima", "ARIMA(1,1,1)"),
        ]:
            err = np.abs(comp["mm7_casos"] - comp[col_m])
            mae = float(err.mean())
            mape = float((err / comp["mm7_casos"].replace(0, np.nan)).dropna().mean() * 100)
            resultados_bt.append({
                "fecha_corte": corte,
                "escenario": etiqueta,
                "modelo": nombre_m,
                "MAE": round(mae, 1),
                "MAPE_pct": round(mape, 1),
            })

    df_bt = pd.DataFrame(resultados_bt)
    df_bt.to_csv("data/clean/backtesting_chile.csv", index=False)
    print(df_bt.to_string(index=False))

    # --- Evaluación histórica de la alerta temprana en Chile ---
    print("\n--- R5 · EVALUACIÓN DE ALERTA TEMPRANA EN CHILE ---")
    cl = real_full.copy()
    cl["inc_prev"] = cl["incidencia_100k_7d"].shift(7)
    cl["var_pct"] = np.where(cl["inc_prev"] > 0, (cl["incidencia_100k_7d"] - cl["inc_prev"]) / cl["inc_prev"] * 100, 0)
    cl["alerta_activa"] = (cl["incidencia_100k_7d"] >= 35.0) & (cl["var_pct"] >= 25.0)

    # Picos principales de olas en Chile
    olas = [
        ("Ola 1 (2020)", "2020-05-01", "2020-07-01"),
        ("Ola 2 (2021)", "2021-02-15", "2021-05-01"),
        ("Ómicron (2022)", "2021-12-15", "2022-02-20"),
        ("Invierno 2022", "2022-05-01", "2022-07-15"),
    ]
    for nombre, ini, fin in olas:
        sub = cl[(cl["fecha"] >= ini) & (cl["fecha"] <= fin)]
        fecha_pico = sub.loc[sub["mm7_casos"].idxmax(), "fecha"]
        alertas_ola = sub[(sub["alerta_activa"]) & (sub["fecha"] < fecha_pico)]
        if not alertas_ola.empty:
            primera = alertas_ola["fecha"].iloc[0]
            ant = (fecha_pico - primera).days
            print(f"  {nombre:<15} | Primera alerta: {primera.date()} | Pico: {fecha_pico.date()} | Anticipación: {ant} días")
        else:
            print(f"  {nombre:<15} | Sin alerta previa al pico ({fecha_pico.date()})")

    # Falsas alarmas: alertas donde la incidencia 14 días después fue MENOR que el día de la alerta
    cl["inc_fut14"] = cl["incidencia_100k_7d"].shift(-14)
    total_alertas = int(cl["alerta_activa"].sum())
    falsas = int((cl["alerta_activa"] & (cl["inc_fut14"] < cl["incidencia_100k_7d"])).sum())
    print(f"  Días con alerta activa: {total_alertas} | Falsas alarmas (incidencia baja a 14d): {falsas} ({falsas/max(total_alertas,1)*100:.1f} %)")


def ejecutar_segmentacion_paises():
    print("\n--- R5 / P5 · SEGMENTACIÓN K-MEANS DE PAÍSES ---")
    con = duckdb.connect(DW_PATH, read_only=True)
    df = con.execute("""
        WITH pob_pais AS (
            SELECT
                country_region,
                COALESCE(
                    MAX(CASE WHEN nivel_granularidad = 'pais' THEN population END),
                    SUM(CASE WHEN nivel_granularidad = 'region_estado' THEN population END),
                    SUM(population)
                ) AS population
            FROM dim_territorio
            WHERE NOT es_entidad_especial
            GROUP BY 1
            HAVING population >= 500000
        ),
        pais_dia AS (
            SELECT
                t.country_region,
                d.fecha,
                SUM(f.confirmed) AS confirmed,
                SUM(f.deaths) AS deaths
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE NOT t.es_entidad_especial
            GROUP BY 1, 2
        ),
        resumen AS (
            SELECT
                p.country_region,
                p.population,
                MAX(d.confirmed) AS total_casos,
                MAX(d.deaths) AS total_fallecidos
            FROM pais_dia d
            JOIN pob_pais p ON d.country_region = p.country_region
            GROUP BY 1, 2
            HAVING MAX(d.confirmed) > 5000
        ),
        vac AS (
            SELECT t.country_region, MAX(v.pct_vacunacion_completa) AS max_vac_pct
            FROM fact_vacunacion v
            JOIN (SELECT DISTINCT country_region, iso3 FROM dim_territorio WHERE iso3 IS NOT NULL) t
              ON v.iso3 = t.iso3
            GROUP BY 1
        )
        SELECT
            r.country_region,
            r.population,
            ROUND(r.total_casos * 100000.0 / r.population, 1) AS casos_100k,
            ROUND(r.total_fallecidos * 100000.0 / r.population, 1) AS fallecidos_100k,
            ROUND(r.total_fallecidos * 100.0 / NULLIF(r.total_casos, 0), 2) AS letalidad_pct,
            COALESCE(v.max_vac_pct, 0) AS max_vac_pct
        FROM resumen r
        LEFT JOIN vac v ON r.country_region = v.country_region
    """).df()
    con.close()

    features = ["casos_100k", "fallecidos_100k", "letalidad_pct", "max_vac_pct"]
    X = StandardScaler().fit_transform(df[features].fillna(0))
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X)
    df.to_csv("data/clean/segmentacion_paises.csv", index=False)

    perfil = df.groupby("cluster")[features].mean().round(1)
    perfil["n_paises"] = df.groupby("cluster")["country_region"].count()
    print(perfil.to_string())

    cl_cluster = df.loc[df["country_region"] == "Chile", "cluster"].values[0]
    pares = df[df["cluster"] == cl_cluster]["country_region"].head(10).tolist()
    print(f"\nChile quedó en el Cluster {cl_cluster}. Ejemplos del mismo grupo: {pares}")


if __name__ == "__main__":
    ejecutar_backtesting_y_evaluacion()
    ejecutar_segmentacion_paises()