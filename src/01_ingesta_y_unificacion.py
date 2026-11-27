import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd

# --- Configuración de rutas ---
RAW_DAILY = "data/raw/daily_reports"
RAW_TS = "data/raw/time_series"
RAW_ROOT = "data/raw"
CLEAN_DIR = "data/clean"

for d in [RAW_DAILY, RAW_TS, CLEAN_DIR]:
    os.makedirs(d, exist_ok=True)

JHU_BASE = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data"
OWID_VAC_URL = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/vaccinations.csv"
WB_POP65_URL = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.65UP.TO.ZS?date=2021&format=json&per_page=400"
WB_GDP_URL = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?date=2021&format=json&per_page=400"

RENOMBRAR = {
    "Province/State": "province_state",
    "Province_State": "province_state",
    "Country/Region": "country_region",
    "Country_Region": "country_region",
    "Last Update": "last_update",
    "Last_Update": "last_update",
    "Latitude": "lat",
    "Lat": "lat",
    "Longitude": "long",
    "Long_": "long",
    "Incidence_Rate": "incident_rate",
    "Incident_Rate": "incident_rate",
    "Case-Fatality_Ratio": "case_fatality_ratio",
    "Case_Fatality_Ratio": "case_fatality_ratio",
}

COLUMNAS_FINALES = [
    "fecha_reporte", "esquema", "fips", "admin2", "province_state",
    "country_region", "combined_key", "last_update", "lat", "long",
    "confirmed", "deaths", "recovered", "active",
    "incident_rate", "case_fatality_ratio",
]


def descargar_archivo(url: str, destino: str) -> bool:
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return True
    for intento in range(3):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(destino, "wb") as f:
                    f.write(r.content)
                return True
        except requests.RequestException:
            time.sleep(1)
    return False


def obtener_esquema(fecha: pd.Timestamp) -> int:
    if fecha <= pd.Timestamp("2020-02-29"):
        return 1
    if fecha <= pd.Timestamp("2020-03-21"):
        return 2
    if fecha <= pd.Timestamp("2020-05-28"):
        return 3
    if fecha <= pd.Timestamp("2020-11-08"):
        return 4
    return 5


def descargar_banco_mundial(destino: str) -> bool:
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return True
    try:
        r_pop = requests.get(WB_POP65_URL, timeout=15).json()[1]
        r_gdp = requests.get(WB_GDP_URL, timeout=15).json()[1]
        df_pop = pd.DataFrame([
            {"iso3": x.get("countryiso3code"), "pais_wb": x.get("country", {}).get("value"), "pct_pob_65mas": x.get("value")}
            for x in r_pop if x.get("countryiso3code")
        ])
        df_gdp = pd.DataFrame([
            {"iso3": x.get("countryiso3code"), "pib_per_capita": x.get("value")}
            for x in r_gdp if x.get("countryiso3code")
        ])
        wb = df_pop.merge(df_gdp, on="iso3", how="outer")
        wb = wb[wb["iso3"].str.len() == 3].drop_duplicates("iso3")
        wb.to_csv(destino, index=False)
        return True
    except Exception:
        return False


def paso_1_descargar():
    print("1/3 · Descargando archivos maestros y fuentes externas (OWID + Banco Mundial)...")
    maestros = [
        (f"{JHU_BASE}/UID_ISO_FIPS_LookUp_Table.csv", f"{RAW_ROOT}/UID_ISO_FIPS_LookUp_Table.csv"),
        (f"{JHU_BASE}/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv", f"{RAW_TS}/confirmed_global.csv"),
        (f"{JHU_BASE}/csse_covid_19_time_series/time_series_covid19_deaths_global.csv", f"{RAW_TS}/deaths_global.csv"),
        (OWID_VAC_URL, f"{RAW_ROOT}/owid_vaccinations.csv"),
    ]
    for url, dest in maestros:
        ok = descargar_archivo(url, dest)
        print(f"   [{'OK' if ok else 'ERROR'}] {os.path.basename(dest)}")
    ok_wb = descargar_banco_mundial(f"{RAW_ROOT}/worldbank_indicadores.csv")
    print(f"   [{'OK' if ok_wb else 'ERROR'}] worldbank_indicadores.csv")

    fechas = pd.date_range("2020-01-22", "2023-03-09", freq="D")
    tareas = [
        (f"{JHU_BASE}/csse_covid_19_daily_reports/{f.strftime('%m-%d-%Y')}.csv",
         f"{RAW_DAILY}/{f.strftime('%m-%d-%Y')}.csv")
        for f in fechas
    ]

    print(f"2/3 · Descargando {len(tareas)} reportes diarios en paralelo...")
    fallos = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futuros = {pool.submit(descargar_archivo, u, d): d for u, d in tareas}
        completados = 0
        for fut in as_completed(futuros):
            completados += 1
            if not fut.result():
                fallos.append(futuros[fut])
            if completados % 200 == 0 or completados == len(tareas):
                print(f"   Progreso: {completados}/{len(tareas)} archivos")
    if fallos:
        print(f"   [ADVERTENCIA] Fallaron {len(fallos)} archivos: {fallos[:5]}")


def paso_2_unificar_y_parquet():
    print("3/3 · Unificando los 5 esquemas a Parquet...")
    fechas = pd.date_range("2020-01-22", "2023-03-09", freq="D")
    dfs = []
    t0_csv = time.perf_counter()

    for f in fechas:
        ruta = f"{RAW_DAILY}/{f.strftime('%m-%d-%Y')}.csv"
        if not os.path.exists(ruta):
            continue
        df = pd.read_csv(ruta, dtype={"FIPS": "string", "Admin2": "string"}, low_memory=False)
        # Limpiar BOM o espacios accidentales en encabezados
        df.columns = df.columns.str.replace("\ufeff", "", regex=False).str.strip()
        df = df.rename(columns=RENOMBRAR)
        df.columns = df.columns.str.lower()

        df["fecha_reporte"] = f.strftime("%Y-%m-%d")
        df["esquema"] = obtener_esquema(f)

        # Normalizar nombre antiguo de China en etapas 1-2
        if "country_region" in df.columns:
            df["country_region"] = df["country_region"].replace({"Mainland China": "China"})

        # Construir combined_key en etapas 1 y 2 donde no existía
        if "combined_key" not in df.columns:
            prov = df["province_state"].fillna("").astype(str).str.strip()
            pais = df["country_region"].fillna("").astype(str).str.strip()
            df["combined_key"] = prov.where(prov == "", prov + ", ") + pais

        # Asegurar todas las columnas del esquema unificado (sin inventar valores)
        for col in COLUMNAS_FINALES:
            if col not in df.columns:
                df[col] = pd.NA

        dfs.append(df[COLUMNAS_FINALES])

    tiempo_lectura_csv = time.perf_counter() - t0_csv
    unificado = pd.concat(dfs, ignore_index=True)

    # Tipos numéricos consistentes
    for col in ["lat", "long", "confirmed", "deaths", "recovered", "active", "incident_rate", "case_fatality_ratio"]:
        unificado[col] = pd.to_numeric(unificado[col], errors="coerce")
    for col in ["fips", "admin2", "province_state", "country_region", "combined_key", "last_update", "fecha_reporte"]:
        unificado[col] = unificado[col].astype("string")

    ruta_parquet = f"{CLEAN_DIR}/reportes_unificados.parquet"
    unificado.to_parquet(ruta_parquet, index=False, compression="snappy")

    # Benchmark exigido en R1: tamaño y tiempo de lectura CSV vs Parquet
    tam_csv_mb = sum(
        os.path.getsize(os.path.join(RAW_DAILY, x)) for x in os.listdir(RAW_DAILY) if x.endswith(".csv")
    ) / (1024 ** 2)
    tam_parquet_mb = os.path.getsize(ruta_parquet) / (1024 ** 2)

    t0_pq = time.perf_counter()
    _ = pd.read_parquet(ruta_parquet)
    tiempo_lectura_pq = time.perf_counter() - t0_pq

    print("\n--- RESUMEN R1 (CSV vs Parquet) ---")
    print(f"Filas totales unificadas : {len(unificado):,}")
    print(f"Tamaño CSV (1.143 arch.) : {tam_csv_mb:.1f} MB")
    print(f"Tamaño Parquet           : {tam_parquet_mb:.1f} MB (reducción {(1 - tam_parquet_mb/tam_csv_mb)*100:.1f} %)")
    print(f"Lectura 1.143 CSVs       : {tiempo_lectura_csv:.2f} s")
    print(f"Lectura Parquet          : {tiempo_lectura_pq:.2f} s ({tiempo_lectura_csv/tiempo_lectura_pq:.1f}x más rápido)")


if __name__ == "__main__":
    paso_1_descargar()
    paso_2_unificar_y_parquet()