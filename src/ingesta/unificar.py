"""R1 - Unificacion de los cinco esquemas en una sola tabla (capa limpia).

Uso:  python -m src.ingesta.unificar
Salida: data/clean/reportes_diarios_unificados.parquet

Contrato de salida (lo usan calidad, DW, analisis y modelos; cambiarlo exige
avisar al equipo y actualizar docs/diccionario_datos.md):
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src import config

RENOMBRAR = {
    "Province/State": "province_state", "Province_State": "province_state",
    "Country/Region": "country_region", "Country_Region": "country_region",
    "Last Update": "last_update", "Last_Update": "last_update",
    "Latitude": "lat", "Lat": "lat", "Longitude": "long", "Long_": "long",
    "Incidence_Rate": "incident_rate", "Incident_Rate": "incident_rate",
    "Case-Fatality_Ratio": "case_fatality_ratio",
    "Case_Fatality_Ratio": "case_fatality_ratio",
    "FIPS": "fips", "Admin2": "admin2", "Confirmed": "confirmed",
    "Deaths": "deaths", "Recovered": "recovered", "Active": "active",
    "Combined_Key": "combined_key",
}

COLUMNAS = [
    "fecha_reporte", "esquema", "fips", "admin2", "province_state",
    "country_region", "last_update", "lat", "long", "confirmed", "deaths",
    "recovered", "active", "combined_key", "incident_rate",
    "case_fatality_ratio", "clave_territorio", "archivo_origen", "fila_origen",
]

# Nombres de pais inconsistentes entre esquemas. Lista INICIAL: completar y
# documentar cada decision en docs/decisiones_calidad.md (R2).
NORMALIZAR_PAIS = {
    "Mainland China": "China",
    "South Korea": "Korea, South",
    "Republic of Korea": "Korea, South",
    "Iran (Islamic Republic of)": "Iran",
    "UK": "United Kingdom",
    "Viet Nam": "Vietnam",
    "Russian Federation": "Russia",
    "Czech Republic": "Czechia",
}

LIMITES_ESQUEMA = [  # (ultima fecha del esquema, numero de esquema)
    ("2020-02-29", 1),
    ("2020-03-21", 2),
    ("2020-05-28", 3),
    ("2020-11-08", 4),
]


def esquema_de(fecha: pd.Timestamp | str) -> int:
    fecha = pd.Timestamp(fecha)
    for limite, n in LIMITES_ESQUEMA:
        if fecha <= pd.Timestamp(limite):
            return n
    return 5


def leer_reporte(ruta: Path) -> pd.DataFrame:
    """Lee un reporte diario y lo deja con los nombres unificados."""
    df = pd.read_csv(ruta, dtype=str)
    df = df.rename(columns=lambda c: RENOMBRAR.get(c.strip(), c.strip().lower()))
    fecha = pd.to_datetime(ruta.stem, format="%m-%d-%Y")
    # La fecha del dato es la del ARCHIVO, no last_update (ver PPT S14, lamina 26)
    df["fecha_reporte"] = fecha
    df["esquema"] = esquema_de(fecha)
    df["archivo_origen"] = ruta.name
    df["fila_origen"] = range(2, len(df) + 2)  # linea en el CSV (linaje, R2)
    return df.reindex(columns=[c for c in COLUMNAS if c != "clave_territorio"])


def _tipar(df: pd.DataFrame) -> pd.DataFrame:
    for c in ("confirmed", "deaths", "recovered", "active"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ("lat", "long", "incident_rate", "case_fatality_ratio"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["fips"] = df["fips"].str.replace(r"\.0$", "", regex=True)
    df["last_update"] = pd.to_datetime(
        df["last_update"], format="mixed", errors="coerce"
    ).dt.strftime("%Y-%m-%d")  # formato ISO AAAA-MM-DD
    for c in ("country_region", "province_state", "admin2", "combined_key"):
        df[c] = df[c].str.strip()
    df["country_region"] = df["country_region"].replace(NORMALIZAR_PAIS)
    df["clave_territorio"] = (
        df["country_region"].fillna("")
        + "|" + df["province_state"].fillna("")
        + "|" + df["admin2"].fillna("")
    )
    df["esquema"] = df["esquema"].astype("int8")
    return df[COLUMNAS]


def unificar(carpeta: Path = config.RAW_DIARIOS) -> pd.DataFrame:
    archivos = sorted(carpeta.glob("*.csv"), key=lambda p: pd.to_datetime(p.stem, format="%m-%d-%Y"))
    if not archivos:
        raise FileNotFoundError(f"No hay reportes en {carpeta}. Ejecute primero la descarga.")
    df = pd.concat((leer_reporte(a) for a in archivos), ignore_index=True)
    return _tipar(df)


def guardar_parquet(df: pd.DataFrame, ruta: Path = config.PARQUET_UNIFICADO) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta, index=False, compression="zstd")
    return ruta


def comparar_csv_parquet(carpeta: Path = config.RAW_DIARIOS,
                         parquet: Path = config.PARQUET_UNIFICADO) -> pd.DataFrame:
    """R1: tamanio en disco y tiempo de lectura CSV vs Parquet."""
    csvs = list(carpeta.glob("*.csv"))
    t0 = time.perf_counter()
    pd.concat((pd.read_csv(a, dtype=str) for a in csvs), ignore_index=True)
    t_csv = time.perf_counter() - t0
    t0 = time.perf_counter()
    pd.read_parquet(parquet)
    t_pq = time.perf_counter() - t0
    mb_csv = sum(a.stat().st_size for a in csvs) / 1e6
    mb_pq = parquet.stat().st_size / 1e6
    return pd.DataFrame({
        "formato": ["CSV (1.143 archivos)", "Parquet (zstd)"],
        "tamano_mb": [round(mb_csv, 1), round(mb_pq, 1)],
        "lectura_s": [round(t_csv, 2), round(t_pq, 2)],
    })


if __name__ == "__main__":
    df = unificar()
    ruta = guardar_parquet(df)
    print(f"{len(df):,} filas -> {ruta}")
    print(comparar_csv_parquet())
