# Sala de crisis COVID-19

Proyecto semestral de Gestión de Datos (IN1232C, 2026-2), UCSC. Equipo N.º __.

Plataforma de datos sobre el registro histórico de COVID-19 de Johns Hopkins (22-ene-2020 al 9-mar-2023): ingesta de los 1.143 reportes diarios, control de calidad, Data Warehouse en PostgreSQL integrado con Our World in Data, análisis P1 a P7, pronóstico y alerta temprana, y un tablero para la sesión del Comité.

| Integrante | Rol |
|---|---|
| Nicolás | A · Ingeniería de datos |
| Dan | B · Calidad, ética y fuente externa |
| Cristian | C · Modelos |
| Leo | D · Tablero y comunicación |

## Cómo reproducir el proyecto desde cero

1. **Requisitos:** Python 3.11 o 3.12, PostgreSQL 15 o superior y Git.
2. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Vitalithis/Sala-de-crisis-COVID-19.git
   cd Sala-de-crisis-COVID-19
   ```
3. **Crear el entorno e instalar las dependencias:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
4. **Crear la base de datos:** `createdb -U postgres sala_crisis`. Después copiar `.env.example` a `.env` y ajustar usuario y contraseña.
5. **Ejecutar el pipeline completo** (descarga, unificación, calidad y DW):
   ```bash
   python -m src.pipeline
   ```
   También se puede ejecutar un solo paso: `python -m src.pipeline descargar | unificar | calidad | dw`.
6. **Ejecutar los notebooks en orden**, de `notebooks/00_exploracion.ipynb` a `notebooks/06_proteccion_datos.ipynb`.
7. **Levantar el tablero:** `streamlit run dashboard/app.py`.
8. **Ejecutar las pruebas:** `pytest -q`.

> Los datos crudos (`data/raw/`) no se suben: el paso 5 los descarga. En `data/` solo quedan la capa limpia (Parquet) y la exportación del DW.

## Estructura

```
src/            código reutilizable (los notebooks solo lo llaman)
  ingesta/      R1  descarga y unificación de los 5 esquemas
  calidad/      R2  reglas de las 6 dimensiones e índice por país
  dw/           R3  ETL hacia el modelo en estrella
  externas/     R3  fuentes externas (OWID)
  modelos/      R5  pronosticar(), alerta(), segmentación
  proteccion/   R6  supresión de celdas pequeñas
  pipeline.py       un solo comando para todo
sql/            DDL del DW, vistas y consultas OLAP
notebooks/      00 a 06, en orden de ejecución
dashboard/      R7  app de Streamlit y capturas
data/           clean/ (Parquet) y dw/ (exportación); raw/ está ignorado
docs/           diccionario, decisiones, arquitectura, informes y guía del equipo
tests/          pruebas mínimas (esquemas, que no haya fuga de datos)
```

## Entregables

| Elemento | Ubicación |
|---|---|
| Diccionario de datos | [docs/diccionario_datos.md](docs/diccionario_datos.md) |
| Informe técnico (máx. 15 págs.) | `docs/informe_tecnico.pdf` (fuente: `docs/informe_tecnico.md`) |
| Informe al Comité (máx. 2 págs.) | `docs/informe_comite.pdf` (fuente: `docs/informe_comite.md`) |
| Tablero | [dashboard/](dashboard/) |
| Contribuciones y uso de IA | [contribuciones.md](contribuciones.md) |
