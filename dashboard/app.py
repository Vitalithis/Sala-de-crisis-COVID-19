"""R7 - Tablero de la Sala de crisis (Streamlit).

Ejecutar:  streamlit run dashboard/app.py

Requisitos de la rubrica (todos visibles sin tocar el codigo):
  - KPI en tarjetas, tendencia con media movil 7 dias, ranking
  - filtros por territorio y fecha de corte
  - mapa georreferenciado (lat/long de la tabla UID) mundial y de regiones de Chile
  - indicador de alerta con umbral visible, fecha de corte y advertencias de calidad
  - supresion de celdas pequenas (src.proteccion.supresion) antes de mostrar
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

st.set_page_config(page_title="Sala de crisis COVID-19", layout="wide")
st.title("Sala de crisis COVID-19")

# ---- Filtros ---------------------------------------------------------------
with st.sidebar:
    st.header("Filtros")
    territorio = st.selectbox("Territorio", ["Chile"])  # TODO: lista desde dim_territorio
    fecha_corte = st.date_input("Fecha de corte", pd.Timestamp("2021-12-15"),
                                min_value=pd.Timestamp("2020-01-22"),
                                max_value=pd.Timestamp("2023-03-09"))
    st.caption(f"Datos hasta: {fecha_corte}")

# ---- KPI -------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Casos nuevos 7d / 100k", "TODO")
c2.metric("Fallecidos nuevos 7d / 100k", "TODO")
c3.metric("Letalidad aparente", "TODO")
c4.metric("Alerta temprana", "TODO")  # src.modelos.alerta.alerta(territorio, fecha_corte)

tab_tend, tab_mapa, tab_rank, tab_pron, tab_cal = st.tabs(
    ["Tendencia", "Mapa", "Ranking", "Pronostico", "Calidad y advertencias"])

with tab_tend:
    st.info("TODO: casos y fallecidos nuevos con media movil de 7 dias (plotly)")
with tab_mapa:
    st.info("TODO: scatter_geo / density_mapbox de incidencia por 100k; mundo y regiones de Chile")
with tab_rank:
    st.info("TODO: ranking de territorios por incidencia a la fecha de corte")
with tab_pron:
    st.info("TODO: boton que ejecuta pronosticar(territorio, fecha_corte, 14) y lo compara con lo real")
with tab_cal:
    st.info("TODO: indice de calidad del territorio, advertencias de interpretacion (R6)")
