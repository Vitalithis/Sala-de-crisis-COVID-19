import os
import importlib.util
import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Sala de Crisis COVID-19 · IN1232C",
    page_icon="🦠",
    layout="wide",
)

DW_PATH = "data/dw_covid.duckdb"

# Cargar funciones pronosticar() y alerta() desde src/04_modelos_y_alerta.py
spec = importlib.util.spec_from_file_location("modelos", os.path.join("src", "04_modelos_y_alerta.py"))
modelos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modelos)


@st.cache_data(show_spinner=False)
def cargar_listas_territorios():
    con = duckdb.connect(DW_PATH, read_only=True)
    paises = con.execute("""
        SELECT DISTINCT country_region FROM dim_territorio
        WHERE NOT es_entidad_especial ORDER BY 1
    """).df()["country_region"].tolist()
    regiones_cl = con.execute("""
        SELECT DISTINCT province_state FROM dim_territorio
        WHERE country_region = 'Chile'
          AND province_state IS NOT NULL
          AND province_state <> 'Unknown'
        ORDER BY 1
    """).df()["province_state"].tolist()
    con.close()
    return paises, regiones_cl


@st.cache_data(show_spinner=False)
def cargar_mapa_mundial(fecha_corte: str):
    con = duckdb.connect(DW_PATH, read_only=True)
    df = con.execute(f"""
        WITH pob AS (
            SELECT country_region,
                   COALESCE(
                       MAX(CASE WHEN nivel_granularidad = 'pais' THEN population END),
                       SUM(CASE WHEN nivel_granularidad = 'region_estado' THEN population END),
                       SUM(population)
                   ) AS population,
                   AVG(lat) AS lat,
                   AVG(long) AS long
            FROM dim_territorio
            WHERE NOT es_entidad_especial
            GROUP BY 1
        ),
        ult AS (
            SELECT t.country_region,
                   SUM(f.confirmed) AS confirmed,
                   SUM(f.deaths) AS deaths
            FROM fact_covid f
            JOIN dim_territorio t ON f.territorio_key = t.territorio_key
            JOIN dim_fecha d ON f.fecha_key = d.fecha_key
            WHERE d.fecha = '{fecha_corte}' AND NOT t.es_entidad_especial
            GROUP BY 1
        )
        SELECT u.country_region, u.confirmed, u.deaths, p.population, p.lat, p.long,
               ROUND(u.confirmed * 100000.0 / NULLIF(p.population, 0), 1) AS incidencia_100k,
               ROUND(u.deaths * 100000.0 / NULLIF(p.population, 0), 1) AS mortalidad_100k
        FROM ult u
        JOIN pob p ON u.country_region = p.country_region
        WHERE p.population > 0 AND p.lat IS NOT NULL AND p.long IS NOT NULL
    """).df()
    con.close()
    return df


@st.cache_data(show_spinner=False)
def cargar_mapa_chile(fecha_corte: str):
    con = duckdb.connect(DW_PATH, read_only=True)
    df = con.execute(f"""
        SELECT t.province_state AS region,
               t.population, t.lat, t.long,
               SUM(f.confirmed) AS confirmed,
               SUM(f.deaths) AS deaths,
               ROUND(SUM(f.confirmed) * 100000.0 / NULLIF(t.population, 0), 1) AS incidencia_100k,
               ROUND(SUM(f.deaths) * 100000.0 / NULLIF(t.population, 0), 1) AS mortalidad_100k
        FROM fact_covid f
        JOIN dim_territorio t ON f.territorio_key = t.territorio_key
        JOIN dim_fecha d ON f.fecha_key = d.fecha_key
        WHERE t.country_region = 'Chile'
          AND t.province_state IS NOT NULL
          AND t.province_state <> 'Unknown'
          AND d.fecha = '{fecha_corte}'
        GROUP BY 1, 2, 3, 4
        ORDER BY incidencia_100k DESC
    """).df()
    con.close()
    return df


@st.cache_data(show_spinner=False)
def cargar_vacunacion_pais(pais: str, fecha_corte: str):
    con = duckdb.connect(DW_PATH, read_only=True)
    df = con.execute(f"""
        SELECT CAST(d.fecha AS DATE) AS fecha,
               MAX(v.pct_vacunacion_completa) AS pct_vacunacion_completa
        FROM fact_vacunacion v
        JOIN dim_fecha d ON v.fecha_key = d.fecha_key
        JOIN (SELECT DISTINCT country_region, iso3 FROM dim_territorio WHERE iso3 IS NOT NULL) t
          ON v.iso3 = t.iso3
        WHERE t.country_region = ? AND d.fecha <= '{fecha_corte}'
        GROUP BY 1 ORDER BY 1
    """, [pais]).df()
    con.close()
    return df


def aplicar_supresion(valor: float, poblacion: float) -> str:
    """Regla R6: suprimir celdas pequeñas (conteos 1 a 4 en territorios con población < 50.000)."""
    if pd.isna(valor):
        return "Sin dato"
    if pd.notna(poblacion) and poblacion < 50_000 and 1 <= valor <= 4:
        return "<5 (suprimido R6)"
    return f"{int(round(valor)):,}".replace(",", ".")


# --- SIDEBAR: Filtros globales ---
paises, regiones_cl = cargar_listas_territorios()

st.sidebar.title("🦠 Sala de Crisis COVID-19")
st.sidebar.caption("Gestión de Datos · IN1232C · UCSC")

tipo_terr = st.sidebar.radio("Nivel de territorio", ["País", "Región de Chile"], horizontal=True)
if tipo_terr == "País":
    idx_cl = paises.index("Chile") if "Chile" in paises else 0
    territorio = st.sidebar.selectbox("Territorio", paises, index=idx_cl)
else:
    idx_bb = regiones_cl.index("Biobio") if "Biobio" in regiones_cl else 0
    territorio = st.sidebar.selectbox("Región de Chile", regiones_cl, index=idx_bb)

fecha_corte_dt = st.sidebar.date_input(
    "Fecha de corte de los datos",
    value=pd.to_datetime("2021-12-28"),
    min_value=pd.to_datetime("2020-02-15"),
    max_value=pd.to_datetime("2023-03-09"),
)
fecha_corte = fecha_corte_dt.strftime("%Y-%m-%d")

st.sidebar.divider()
st.sidebar.markdown("**Umbrales de Alerta Temprana (R5)**")
umbral_inc = st.sidebar.slider("Incidencia 7d mínima (c/100k)", 10.0, 100.0, 35.0, 5.0)
umbral_var = st.sidebar.slider("Variación semanal mínima (%)", 10.0, 60.0, 25.0, 5.0)

st.sidebar.divider()
st.sidebar.info(
    "**Advertencias de calidad y ética (R2 / R6):**\n"
    "- La letalidad aparente depende del nivel de testeo de cada país.\n"
    "- Chile cambia de granularidad (nacional → 16 regiones) a fines de mayo de 2020.\n"
    "- Conteos entre 1 y 4 en territorios con <50.000 hab. se suprimen (control de divulgación)."
)

# --- TÍTULO ---
st.title(f"Sala de Crisis COVID-19 · {territorio}")
st.caption(f"Corte de información al **{fecha_corte}** · Fuente: Johns Hopkins CSSE + Our World in Data (DuckDB DW)")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Panorama y Tendencias",
    "🗺️ Mapas Mundial y Chile",
    "🚨 Desafío en Vivo (Pronóstico y Alerta)",
    "🛡️ Calidad (R2) y Segmentación (P5)",
])

# =====================================================================
# TAB 1: PANORAMA Y TENDENCIAS
# =====================================================================
with tab1:
    try:
        serie = modelos.obtener_serie_territorio(territorio, fecha_corte=fecha_corte)
        estado_alerta = modelos.alerta(territorio, fecha_corte, umbral_var_pct=umbral_var, umbral_inc=umbral_inc)
        ult = serie.iloc[-1]
        pob = ult["population"]

        # Banner de alerta temprana con umbral visible
        if estado_alerta["activa"]:
            st.error(
                f"🚨 **ALERTA TEMPRANA ACTIVA** al {estado_alerta['fecha']} — "
                f"Incidencia 7d: **{estado_alerta['incidencia_7d']} / 100k** (umbral ≥ {umbral_inc}) · "
                f"Variación semanal: **+{estado_alerta['variacion_semanal_pct']} %** (umbral ≥ {umbral_var} %)"
            )
        else:
            st.success(
                f"✅ **Sin alerta activa** al {estado_alerta['fecha']} — "
                f"Incidencia 7d: **{estado_alerta['incidencia_7d']} / 100k** (umbral ≥ {umbral_inc}) · "
                f"Variación semanal: **{estado_alerta['variacion_semanal_pct']} %** (umbral ≥ {umbral_var} %)"
            )

        # Tarjetas KPI (con supresión R6)
        c1, c2, c3, c4, c5 = st.columns(5)
        letalidad = (ult["deaths"] / ult["confirmed"] * 100) if ult["confirmed"] > 0 else 0.0
        c1.metric("Casos acumulados", aplicar_supresion(ult["confirmed"], pob))
        c2.metric("Fallecidos acumulados", aplicar_supresion(ult["deaths"], pob))
        c3.metric("Media móvil 7d (casos)", f"{ult['mm7_casos']:,.1f}".replace(",", "."))
        c4.metric("Incidencia 7d (c/100k)", f"{ult['incidencia_100k_7d']:.1f}" if pd.notna(pob) else "N/D")
        c5.metric("Letalidad aparente*", f"{letalidad:.2f} %")

        # Gráfico de tendencia con media móvil 7 días
        fig_tend = go.Figure()
        fig_tend.add_bar(x=serie["fecha"], y=serie["casos_nuevos"], name="Casos diarios", marker_color="rgba(74,95,122,0.35)")
        fig_tend.add_trace(go.Scatter(x=serie["fecha"], y=serie["mm7_casos"], name="Media móvil 7 días", line=dict(color="#D00120", width=2.5)))
        fig_tend.update_layout(
            title=f"Evolución de casos nuevos diarios en {territorio} (hasta {fecha_corte})",
            xaxis_title="Fecha", yaxis_title="Casos diarios", height=380, hovermode="x unified",
        )
        st.plotly_chart(fig_tend, use_container_width=True)

        # Si es país, mostrar cruce con vacunación (P3)
        if tipo_terr == "País":
            vac = cargar_vacunacion_pais(territorio, fecha_corte)
            if not vac.empty:
                fig_vac = px.area(
                    vac, x="fecha", y="pct_vacunacion_completa",
                    title=f"Avance de vacunación completa en {territorio} (% población · OWID)",
                    labels={"fecha": "Fecha", "pct_vacunacion_completa": "% Esquema completo"},
                )
                fig_vac.update_traces(line_color="#1B7F5C")
                fig_vac.update_layout(height=280)
                st.plotly_chart(fig_vac, use_container_width=True)

    except Exception as e:
        st.warning(f"No hay datos disponibles para **{territorio}** al {fecha_corte}. ({e})")

# =====================================================================
# TAB 2: MAPAS MUNDIAL Y CHILE + RANKING
# =====================================================================
with tab2:
    col_m1, col_m2 = st.columns([1.4, 1])

    with col_m1:
        st.subheader(f"Mapa mundial de incidencia por 100.000 hab. ({fecha_corte})")
        df_mundo = cargar_mapa_mundial(fecha_corte)
        if not df_mundo.empty:
            fig_mundo = px.scatter_geo(
                df_mundo, lat="lat", lon="long", size="incidencia_100k", color="mortalidad_100k",
                hover_name="country_region",
                hover_data={"confirmed": True, "deaths": True, "incidencia_100k": True, "lat": False, "long": False},
                color_continuous_scale="Reds", size_max=35,
                title="Incidencia acumulada (tamaño) y mortalidad por 100k (color)",
            )
            fig_mundo.update_layout(height=450, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_mundo, use_container_width=True)

            st.markdown("**Top 10 países por incidencia acumulada (c/100k)**")
            st.dataframe(
                df_mundo.sort_values("incidencia_100k", ascending=False)[
                    ["country_region", "confirmed", "deaths", "incidencia_100k", "mortalidad_100k"]
                ].head(10),
                use_container_width=True, hide_index=True,
            )

    with col_m2:
        st.subheader(f"Mapa regional de Chile ({fecha_corte})")
        df_cl = cargar_mapa_chile(fecha_corte)
        if df_cl.empty:
            st.info("Los datos regionales de Chile comienzan a fines de mayo de 2020. Mueve la fecha de corte a junio de 2020 o posterior.")
        else:
            fig_cl = px.scatter_map(
                df_cl, lat="lat", lon="long", size="incidencia_100k", color="incidencia_100k",
                hover_name="region",
                hover_data={"confirmed": True, "deaths": True, "incidencia_100k": True, "lat": False, "long": False},
                color_continuous_scale="OrRd", size_max=28, zoom=3.2,
                center={"lat": -36.8, "lon": -72.0}, map_style="carto-positron",
            )
            fig_cl.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_cl, use_container_width=True)

            st.markdown("**Ranking regional de Chile (destacando Biobío)**")
            st.dataframe(
                df_cl[["region", "confirmed", "deaths", "incidencia_100k", "mortalidad_100k"]],
                use_container_width=True, hide_index=True,
            )

# =====================================================================
# TAB 3: DESAFÍO EN VIVO (PRONÓSTICO SIN FUGA + COMPARACIÓN REAL)
# =====================================================================
with tab3:
    st.subheader(f"Desafío en Vivo · {territorio} al {fecha_corte} (horizonte = 14 días)")
    horizonte = st.number_input("Horizonte de pronóstico (días)", min_value=7, max_value=30, value=14)
    revelar_real = st.toggle("🔍 Comparar con lo que realmente ocurrió después de la fecha de corte", value=False)
    try:
        hist = modelos.obtener_serie_territorio(territorio, fecha_corte=fecha_corte)
        pred = modelos.pronosticar(territorio, fecha_corte=fecha_corte, horizonte=int(horizonte))
        al = modelos.alerta(territorio, fecha_corte, umbral_var_pct=umbral_var, umbral_inc=umbral_inc)

        k1, k2, k3 = st.columns(3)
        k1.metric("Estado de alerta al corte", "🚨 ACTIVA" if al["activa"] else "✅ Inactiva")
        k2.metric("Pronóstico día +14 (Base MM7)", f"{pred['pred_base_mm7'].iloc[-1]:,.1f}")
        k3.metric("Pronóstico día +14 (Holt)", f"{pred['pred_holt'].iloc[-1]:,.1f}")

        ventana_hist = hist.tail(45)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=ventana_hist["fecha"], y=ventana_hist["mm7_casos"], name="Histórico MM7 (≤ corte)", line=dict(color="#2C3E50", width=2.5)))
        fig_p.add_trace(go.Scatter(x=pred["fecha"], y=pred["pred_base_mm7"], name="Modelo Base (MM7)", line=dict(color="#7F8C8D", dash="dash")))
        fig_p.add_trace(go.Scatter(x=pred["fecha"], y=pred["pred_holt"], name="Modelo Holt Amortiguado", line=dict(color="#D00120", width=2.5, dash="dot")))

        if revelar_real:
            real_full = modelos.obtener_serie_territorio(territorio)
            comp = pred.merge(real_full[["fecha", "mm7_casos"]], on="fecha", how="inner")
            if not comp.empty:
                fig_p.add_trace(go.Scatter(x=comp["fecha"], y=comp["mm7_casos"], name="Real ocurrido (> corte)", line=dict(color="#1B7F5C", width=3)))
                mae_b = np.abs(comp["mm7_casos"] - comp["pred_base_mm7"]).mean()
                mae_h = np.abs(comp["mm7_casos"] - comp["pred_holt"]).mean()
                mape_b = (np.abs(comp["mm7_casos"] - comp["pred_base_mm7"]) / comp["mm7_casos"].replace(0, np.nan)).dropna().mean() * 100
                mape_h = (np.abs(comp["mm7_casos"] - comp["pred_holt"]) / comp["mm7_casos"].replace(0, np.nan)).dropna().mean() * 100
                st.info(f"**Evaluación contra realidad ({len(comp)} días):** Base MM7 → MAE={mae_b:.1f}, MAPE={mape_b:.1f}% | **Holt → MAE={mae_h:.1f}, MAPE={mape_h:.1f}%**")

        fig_p.add_vline(x=pd.to_datetime(fecha_corte).timestamp() * 1000, line_dash="dash", line_color="black")
        fig_p.update_layout(
            title=f"Pronóstico sin fuga de datos · {territorio} (corte: {fecha_corte})",
            xaxis_title="Fecha", yaxis_title="Casos diarios (MM7)", height=420, hovermode="x unified",
        )
        st.plotly_chart(fig_p, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo ejecutar el pronóstico para {territorio} en {fecha_corte}: {e}")

# =====================================================================
# TAB 4: CALIDAD (R2) Y SEGMENTACIÓN (P5)
# =====================================================================
with tab4:
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.subheader("Control de calidad · 6 dimensiones (R2)")
        if os.path.exists("data/clean/reglas_calidad.csv"):
            st.dataframe(pd.read_csv("data/clean/reglas_calidad.csv"), use_container_width=True, hide_index=True)
        st.subheader("Top 10 países con peor índice de calidad (P4)")
        if os.path.exists("data/clean/indice_calidad_paises.csv"):
            st.dataframe(pd.read_csv("data/clean/indice_calidad_paises.csv").head(10), use_container_width=True, hide_index=True)

    with col_q2:
        st.subheader("Segmentación de países · K-Means (P5)")
        if os.path.exists("data/clean/segmentacion_paises.csv"):
            seg = pd.read_csv("data/clean/segmentacion_paises.csv")
            fig_seg = px.scatter(
                seg, x="casos_100k", y="fallecidos_100k", color=seg["cluster"].astype(str),
                size="population", hover_name="country_region",
                hover_data=["letalidad_pct", "max_vac_pct"],
                labels={"casos_100k": "Casos por 100k", "fallecidos_100k": "Fallecidos por 100k", "color": "Cluster"},
                title="Grupos de países por carga epidémica y mortalidad",
            )
            st.plotly_chart(fig_seg, use_container_width=True)

        st.subheader("Backtesting en 3 fechas de corte · Chile (R5)")
        if os.path.exists("data/clean/backtesting_chile.csv"):
            st.dataframe(pd.read_csv("data/clean/backtesting_chile.csv"), use_container_width=True, hide_index=True)