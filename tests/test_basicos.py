"""Pruebas automatizadas del proyecto. Ejecutar: python -m pytest -q"""
import importlib.util
import os
import pandas as pd

from src.ingesta.unificar import esquema_de
from src.modelos.datos import recortar
from src.calidad.reglas import ejecutar_reglas
from src.calidad.indice import problemas_por_pais, indice_calidad
from src.proteccion.supresion import suprimir, informacion_perdida


def test_esquemas():
    assert esquema_de("2020-01-22") == 1
    assert esquema_de("2020-03-01") == 2
    assert esquema_de("2020-03-22") == 3
    assert esquema_de("2020-05-29") == 4
    assert esquema_de("2020-11-09") == 5
    assert esquema_de("2023-03-09") == 5


def test_recortar_no_filtra_futuro():
    s = pd.DataFrame({"fecha": pd.date_range("2021-12-01", periods=60), "casos_nuevos": 1})
    out = recortar(s, "2021-12-15")
    assert out["fecha"].max() == pd.Timestamp("2021-12-15")
    assert len(out) == 15


def test_reglas_e_indice_calidad():
    df = pd.DataFrame({
        "fecha_reporte": ["2021-01-01", "2021-01-02", "2021-01-03"],
        "combined_key": ["Chile", "Chile", "Chile"],
        "country_region": ["Chile", "Chile", "Chile"],
        "lat": [-35.6, -35.6, -35.6],
        "long": [-71.5, -71.5, -71.5],
        "confirmed": [100, 120, 115],
        "deaths": [5, 6, 6],
    })
    res = ejecutar_reglas(df)
    assert len(res) == 9
    assert set(res["dimension"]) == {"completitud", "unicidad", "validez", "consistencia", "exactitud", "oportunidad"}

    df_pd = pd.DataFrame({
        "pais": ["PaisTest"] * 3,
        "fecha": pd.date_range("2021-01-01", periods=3),
        "confirmados_acum": [1000, 1100, 1050],
        "fallecidos_acum": [10, 10, 10],
        "casos_nuevos": [100, 100, -50],
    })
    idx = indice_calidad(problemas_por_pais(df_pd))
    assert len(idx) == 1
    assert 0.0 <= idx["indice_calidad"].iloc[0] <= 100.0


def test_supresion_y_perdida():
    df = pd.DataFrame({
        "poblacion": [3000, 3000, 100000],
        "casos_nuevos": [3, 12, 2],
    })
    sup = suprimir(df, ["casos_nuevos"], umbral_poblacion=5000)
    assert sup.loc[0, "casos_nuevos"] == "<5"
    assert sup.loc[1, "casos_nuevos"] == 12
    assert sup.loc[2, "casos_nuevos"] == 2
    perd = informacion_perdida(df, ["casos_nuevos"], umbral_poblacion=5000)
    assert perd.loc[0, "celdas_suprimidas"] == 1


def test_pronosticar_tres_modelos_sin_fuga():
    if not os.path.exists("data/dw_covid.duckdb"):
        return
    spec = importlib.util.spec_from_file_location("mod04", os.path.join("src", "04_modelos_y_alerta.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pred = mod.pronosticar("Chile", "2021-12-28", horizonte=14)
    assert len(pred) == 14
    assert {"pred_base_mm7", "pred_holt", "pred_arima"}.issubset(pred.columns)
    assert pred["fecha"].min() == pd.Timestamp("2021-12-29")
