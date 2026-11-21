"""Pipeline completo en un solo comando (R1: reproducible).

    python -m src.pipeline            # todo, en orden
    python -m src.pipeline descargar  # un paso
Pasos: descargar, unificar, calidad, dw
"""
from __future__ import annotations

import sys

import pandas as pd

from src import config


def paso_descargar():
    from src.externas import owid
    from src.ingesta.descargar import descargar_todo

    descargar_todo()
    owid.descargar()


def paso_unificar():
    from src.ingesta.unificar import comparar_csv_parquet, guardar_parquet, unificar

    df = unificar()
    print(f"Unificado: {len(df):,} filas -> {guardar_parquet(df)}")
    print(comparar_csv_parquet().to_string(index=False))


def paso_calidad():
    from src.calidad.reglas import ejecutar_reglas

    res = ejecutar_reglas(pd.read_parquet(config.PARQUET_UNIFICADO))
    config.REPORTS.mkdir(exist_ok=True)
    res.to_csv(config.REPORTS / "calidad_ultima_carga.csv", index=False)
    print(res.to_string(index=False))


def paso_dw():
    from src.dw.cargar import cargar_todo, exportar_dw

    cargar_todo()
    exportar_dw()


PASOS = {"descargar": paso_descargar, "unificar": paso_unificar,
         "calidad": paso_calidad, "dw": paso_dw}


if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(PASOS)
    for p in pedidos:
        print(f"\n=== {p} ===")
        PASOS[p]()
