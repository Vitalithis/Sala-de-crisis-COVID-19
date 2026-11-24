# Sala de Crisis COVID-19 · Gestión de Datos (IN1232C)

Plataforma analítica, Data Warehouse y tablero interactivo construidos sobre el registro histórico completo de COVID-19 de Johns Hopkins CSSE (22 de enero de 2020 al 9 de marzo de 2023), integrado con datos de vacunación de Our World in Data (OWID).

## Estructura del repositorio

```text
Proyecto_Gestion/
├── README.md                          # Guía de reproducción paso a paso
├── contribuciones.md                  # Aportes por integrante y uso de IA
├── requirements.txt                   # Dependencias de Python
├── .gitignore                         # Excluye data/raw/ y .venv/
├── src/
│   ├── 01_ingesta_y_unificacion.py    # Descarga 1.143 CSV + UID + OWID y unifica 5 esquemas a Parquet
│   ├── 02_construir_dw.py             # Construye el modelo en estrella en DuckDB e integra OWID
│   ├── 03_calidad_y_olap.py           # Reglas ejecutables (6 dimensiones), índice P4 y consultas OLAP
│   ├── 04_modelos_y_alerta.py         # pronosticar(), alerta(), backtesting (3 cortes) y K-Means
│   └── 05_analisis_preguntas.py       # Métricas y gráficos para P1, P2, P3, P7 y control R6
├── notebooks/
│   └── 00_exploracion.ipynb           # Exploración guiada (enero a junio de 2020)
├── data/
│   ├── clean/                         # Capa limpia (reportes_unificados.parquet y tablas resumen)
│   └── dw_covid.duckdb                # Capa analítica (Data Warehouse en DuckDB)
├── dashboard/
│   └── app.py                         # Tablero interactivo en Streamlit (mapas y desafío en vivo)
└── docs/
    ├── diccionario_datos.md           # Diccionario de la tabla unificada (R2)
    ├── figuras/                       # Gráficos generados por los scripts
    ├── informe_tecnico.pdf            # Informe técnico completo (máx. 15 páginas)
    └── informe_comite.pdf             # Informe ejecutivo al Comité (máx. 2 páginas, R8)
```

> **Nota sobre datos crudos:** La carpeta `data/raw/` está excluida en `.gitignore` y se regenera automáticamente al ejecutar el Paso 4.

---

## Requisitos previos

- Python 3.10 o superior
- Git (opcional, si se clona desde GitHub)
- Conexión a internet para descargar los 1.143 reportes diarios de Johns Hopkins CSSE y el archivo de vacunación de Our World in Data.

---

## Pasos para reproducir el proyecto desde cero

1. **Clonar el repositorio (o descomprimir el `.zip`) y entrar a la carpeta del proyecto:**
   ```bash
   git clone https://github.com/Vitalithis/Sala-de-crisis-COVID-19.git
   cd Proyecto_Gestion
   ```

2. **Crear y activar un entorno virtual:**
   - **Windows (Command Prompt / cmd):**
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la ingesta y unificación de los 5 esquemas (R1):**
   Descarga los 1.143 reportes diarios, las series globales, la tabla maestra UID y OWID en `data/raw/`, unifica los esquemas a `data/clean/reportes_unificados.parquet` y compara tamaño y velocidad CSV vs. Parquet.
   ```bash
   python -u src/01_ingesta_y_unificacion.py
   ```

5. **Construir el Data Warehouse en estrella en DuckDB (R3):**
   Genera `data/dw_covid.duckdb` con `dim_fecha`, `dim_territorio`, `fact_covid` y `fact_vacunacion`, calcula casos/fallecidos nuevos diarios, concilia filas y reporta la tasa de cruce por código ISO3.
   ```bash
   python -u src/02_construir_dw.py
   ```

6. **Ejecutar el control de calidad de 6 dimensiones y consultas OLAP (R2 y R3):**
   Evalúa completitud, unicidad, validez, consistencia, exactitud y oportunidad, genera el índice de calidad por país (P4) y corre consultas `roll-up`, `drill-down`, `slice` y `dice` sobre DuckDB.
   ```bash
   python -u src/03_calidad_y_olap.py
   ```

7. **Ejecutar los modelos predictivos, alerta temprana y segmentación (R5, P5 y P6):**
   Corre el backtesting de `pronosticar()` en 3 fechas de corte (MAE y MAPE), evalúa `alerta()` en la historia de Chile y ejecuta la segmentación K-Means de países.
   ```bash
   python -u src/04_modelos_y_alerta.py
   ```

8. **Generar los análisis y gráficos de las preguntas del Comité (R4 y R6):**
   Produce los resultados y figuras de P1, P2 (destacando Biobío), P3, P7 y la medición de supresión de celdas pequeñas en `docs/figuras/`.
   ```bash
   python -u src/05_analisis_preguntas.py
   ```

9. **Levantar el tablero interactivo en Streamlit (R7 y Desafío en vivo):**
   ```bash
   streamlit run dashboard/app.py
   ```
   El tablero se abrirá en `http://localhost:8501` con filtros por país o región de Chile, fecha de corte, mapas georreferenciados, control de divulgación (R6) y la pestaña **Desafío en Vivo** para ejecutar `pronosticar()` y `alerta()` sin fuga de datos.

---

## Reproducción alternativa en Google Colab (pipeline de datos y análisis)

1. Subir el `.zip` del repositorio a Colab y descomprimirlo con `!unzip Proyecto_Gestion.zip`.
2. Instalar dependencias: `!pip install -r requirements.txt`.
3. Ejecutar los scripts en orden desde una celda:
   ```python
   !python -u src/01_ingesta_y_unificacion.py
   !python -u src/02_construir_dw.py
   !python -u src/03_calidad_y_olap.py
   !python -u src/04_modelos_y_alerta.py
   !python -u src/05_analisis_preguntas.py
   ```