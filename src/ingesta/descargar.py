"""R1 - Descarga automatica y reproducible de la fuente JHU CSSE.

Uso:  python -m src.ingesta.descargar
Es idempotente: si un archivo ya existe en data/raw no se vuelve a descargar.
"""
from __future__ import annotations

import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src import config

SERIES = [
    "time_series_covid19_confirmed_global.csv",
    "time_series_covid19_deaths_global.csv",
    "time_series_covid19_recovered_global.csv",
    "time_series_covid19_confirmed_US.csv",
    "time_series_covid19_deaths_US.csv",
]
UID = "UID_ISO_FIPS_LookUp_Table.csv"


def descargar_archivo(url: str, destino: Path, reintentos: int = 3) -> Path:
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    for intento in range(1, reintentos + 1):
        try:
            urllib.request.urlretrieve(url, destino)
            return destino
        except Exception as e:  # noqa: BLE001
            if intento == reintentos:
                raise RuntimeError(f"No se pudo descargar {url}: {e}") from e
            time.sleep(2 * intento)
    return destino


def urls_reportes_diarios() -> list[tuple[str, Path]]:
    """1.143 archivos: el nombre es mes-dia-anio (01-22-2020.csv)."""
    base = config.JHU_BASE + "csse_covid_19_daily_reports/"
    fechas = pd.date_range(config.FECHA_INICIO, config.FECHA_FIN, freq="D")
    out = []
    for f in fechas:
        nombre = f.strftime("%m-%d-%Y") + ".csv"
        out.append((base + nombre, config.RAW_DIARIOS / nombre))
    return out


def urls_series_y_uid() -> list[tuple[str, Path]]:
    base = config.JHU_BASE + "csse_covid_19_time_series/"
    out = [(base + s, config.RAW_SERIES / s) for s in SERIES]
    out.append((config.JHU_BASE + UID, config.RAW / UID))
    return out


def descargar_todo(hilos: int = 8) -> None:
    config.crear_carpetas()
    tareas = urls_reportes_diarios() + urls_series_y_uid()
    errores = []
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        futuros = {ex.submit(descargar_archivo, u, d): u for u, d in tareas}
        for i, fut in enumerate(as_completed(futuros), 1):
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001
                errores.append(str(e))
            if i % 100 == 0:
                print(f"  {i}/{len(tareas)} archivos")
    print(f"Descarga terminada: {len(tareas) - len(errores)}/{len(tareas)} archivos OK")
    if errores:
        print("Errores:", *errores[:10], sep="\n  ")


if __name__ == "__main__":
    descargar_todo()
