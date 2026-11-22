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

# Nombres de pais inconsistentes entre esquemas -> nombre canonico de la tabla
# UID (UID_ISO_FIPS_LookUp_Table.csv). Decision documentada en
# docs/decisiones_calidad.md (problema 7). Casi todas las variantes aparecen
# solo entre ene y mar de 2020 (esquemas 1 y 2).
NORMALIZAR_PAIS = {
    "Mainland China": "China",
    "South Korea": "Korea, South",
    "Republic of Korea": "Korea, South",
    "Iran (Islamic Republic of)": "Iran",
    "UK": "United Kingdom",
    "Viet Nam": "Vietnam",
    "Russian Federation": "Russia",
    "Czech Republic": "Czechia",
    "Taiwan": "Taiwan*",
    "Taipei and environs": "Taiwan*",
    "Bahamas, The": "Bahamas",
    "The Bahamas": "Bahamas",
    "Gambia, The": "Gambia",
    "The Gambia": "Gambia",
    "Cape Verde": "Cabo Verde",
    "East Timor": "Timor-Leste",
    "Ivory Coast": "Cote d'Ivoire",
    "Republic of Ireland": "Ireland",
    "Republic of Moldova": "Moldova",
    "Republic of the Congo": "Congo (Brazzaville)",
    "Vatican City": "Holy See",
    "Palestine": "West Bank and Gaza",
    "occupied Palestinian territory": "West Bank and Gaza",
    # Crucero informado como pais generico al inicio
    "Cruise Ship": "Diamond Princess",
    "Others": "Diamond Princess",
}

# Territorios que al inicio se informaron como pais y despues JHU los ubica
# como provincia de otro pais: pais_original -> (pais, provincia).
PAIS_A_PROVINCIA = {
    "Hong Kong": ("China", "Hong Kong"),
    "Hong Kong SAR": ("China", "Hong Kong"),
    "Macau": ("China", "Macau"),
    "Macao SAR": ("China", "Macau"),
    "Aruba": ("Netherlands", "Aruba"),
    "Curacao": ("Netherlands", "Curacao"),
    "Faroe Islands": ("Denmark", "Faroe Islands"),
    "Greenland": ("Denmark", "Greenland"),
    "French Guiana": ("France", "French Guiana"),
    "Guadeloupe": ("France", "Guadeloupe"),
    "Martinique": ("France", "Martinique"),
    "Mayotte": ("France", "Mayotte"),
    "Reunion": ("France", "Reunion"),
    "Saint Barthelemy": ("France", "Saint Barthelemy"),
    "Saint Martin": ("France", "St Martin"),
    "St. Martin": ("France", "St Martin"),
    "Cayman Islands": ("United Kingdom", "Cayman Islands"),
    "Channel Islands": ("United Kingdom", "Channel Islands"),
    "Gibraltar": ("United Kingdom", "Gibraltar"),
    "Guernsey": ("United Kingdom", "Guernsey"),
    "Jersey": ("United Kingdom", "Jersey"),
    "North Ireland": ("United Kingdom", "Northern Ireland"),
    "Guam": ("US", "Guam"),
    "Puerto Rico": ("US", "Puerto Rico"),
}

# Archivo con las filas excluidas por duplicado (linaje de la decision)
DUPLICADOS_EXCLUIDOS = config.REPORTS / "duplicados_excluidos.csv"

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
    df = normalizar_territorio(df)
    df["clave_territorio"] = (
        df["country_region"].fillna("")
        + "|" + df["province_state"].fillna("")
        + "|" + df["admin2"].fillna("")
    )
    df["esquema"] = df["esquema"].astype("int8")
    return df[COLUMNAS]


def normalizar_territorio(df: pd.DataFrame) -> pd.DataFrame:
    """Lleva country_region/province_state a los nombres canonicos de la tabla UID."""
    df["country_region"] = df["country_region"].replace(NORMALIZAR_PAIS)
    for original, (pais, provincia) in PAIS_A_PROVINCIA.items():
        m = df["country_region"] == original
        df.loc[m, "province_state"] = provincia
        df.loc[m, "country_region"] = pais
    # «Others / Diamond Princess cruise ship» queda como el pais Diamond Princess
    m = df["country_region"] == "Diamond Princess"
    df.loc[m, "province_state"] = pd.NA
    return df


def separar_duplicados(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Unicidad (R2): una fila por (fecha_reporte, clave_territorio).

    JHU publico algunos territorios dos veces en el mismo archivo (por ejemplo,
    Gansu y Hebei el 11 y 12-mar-2020: una fila con datos y otra en cero). Se
    conserva la fila con mayor confirmed (y luego deaths) y se EXCLUYEN las
    demas; no se suman ni se imputan. Devuelve (sin_duplicados, excluidas).
    """
    orden = df.sort_values(["confirmed", "deaths"], ascending=False, na_position="last")
    dup = orden.duplicated(["fecha_reporte", "clave_territorio"], keep="first")
    excluidas = orden[dup]
    limpio = df.drop(index=excluidas.index).reset_index(drop=True)
    return limpio, excluidas.sort_values(["fecha_reporte", "clave_territorio"])


def unificar(carpeta: Path = config.RAW_DIARIOS) -> pd.DataFrame:
    archivos = sorted(carpeta.glob("*.csv"), key=lambda p: pd.to_datetime(p.stem, format="%m-%d-%Y"))
    if not archivos:
        raise FileNotFoundError(f"No hay reportes en {carpeta}. Ejecute primero la descarga.")
    df = pd.concat((leer_reporte(a) for a in archivos), ignore_index=True)
    df, excluidas = separar_duplicados(_tipar(df))
    DUPLICADOS_EXCLUIDOS.parent.mkdir(parents=True, exist_ok=True)
    excluidas.to_csv(DUPLICADOS_EXCLUIDOS, index=False)
    print(f"Duplicados excluidos: {len(excluidas)} filas -> {DUPLICADOS_EXCLUIDOS}")
    return df


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
