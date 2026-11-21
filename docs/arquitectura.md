# Arquitectura (R1)

```mermaid
flowchart LR
    JHU["GitHub JHU CSSE (raw)"] --> RAW["Capa cruda: data/raw (CSV tal cual)"]
    OWID["Our World in Data"] --> RAW
    RAW -->|"unificar.py: 5 esquemas a snake_case"| CLEAN["Capa limpia: Parquet (zstd)"]
    CLEAN -->|"reglas.py: 6 dimensiones"| Q["Reporte de calidad"]
    CLEAN -->|"dw/cargar.py: ETL"| DW["Capa analítica: PostgreSQL (estrella)"]
    DW --> NB["Notebooks P1 a P7"]
    DW --> MOD["pronosticar() / alerta()"]
    DW --> TAB["Tablero Streamlit"]
    MOD --> TAB
```

## Comparación CSV frente a Parquet

| Formato | Tamaño (MB) | Lectura (s) |
|---|---|---|
| CSV (1.143 archivos) | | |
| Parquet (zstd) | | |

(Salida de `comparar_csv_parquet()`.)

## Por qué PostgreSQL y no NoSQL (S4)

TODO (A): datos tabulares con esquema estable después de unificar; consultas analíticas con JOIN y agregaciones (OLAP, ROLLUP); integridad referencial en la estrella; comparación con MongoDB (documentos) o Cassandra (escritura masiva) y por qué aquí no aportan.

## Equivalente en la nube (excelente)

TODO (A, si sobra tiempo): por ejemplo, S3/GCS para las capas cruda y limpia, RDS/Cloud SQL para el DW y la app en un contenedor, con una estimación de costo mensual.
