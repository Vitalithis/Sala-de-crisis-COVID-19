"""Pruebas minimas. Ejecutar: pytest -q"""
import pandas as pd

from src.ingesta.unificar import esquema_de
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
