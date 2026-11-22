"""Pruebas minimas. Ejecutar: pytest -q"""
import pandas as pd

from src.ingesta.unificar import esquema_de, normalizar_territorio, separar_duplicados
from src.modelos.datos import recortar


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


def test_normalizar_territorio():
    df = pd.DataFrame({
        "country_region": ["Hong Kong", "Taiwan", "Others", "Chile"],
        "province_state": [None, None, "Diamond Princess cruise ship", "Biobio"],
    })
    out = normalizar_territorio(df)
    assert out["country_region"].tolist() == ["China", "Taiwan*", "Diamond Princess", "Chile"]
    assert out.loc[0, "province_state"] == "Hong Kong"
    assert pd.isna(out.loc[2, "province_state"])
    assert out.loc[3, "province_state"] == "Biobio"


def test_separar_duplicados_conserva_fila_con_datos():
    df = pd.DataFrame({
        "fecha_reporte": pd.to_datetime(["2020-03-11"] * 2 + ["2020-03-12"]),
        "clave_territorio": ["China|Gansu|"] * 3,
        "confirmed": pd.array([0, 127, 127], dtype="Int64"),
        "deaths": pd.array([0, 2, 2], dtype="Int64"),
    })
    limpio, excluidas = separar_duplicados(df)
    assert len(limpio) == 2 and len(excluidas) == 1
    assert limpio.loc[limpio["fecha_reporte"] == "2020-03-11", "confirmed"].item() == 127
    assert excluidas["confirmed"].item() == 0
