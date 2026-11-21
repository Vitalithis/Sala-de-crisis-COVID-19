-- R3 - Modelo en estrella. Grano de la tabla de hechos: territorio x dia.
-- Se ejecuta desde src/dw/cargar.py (recrea todo desde cero: reproducible).

DROP VIEW  IF EXISTS vw_territorio_dia, vw_pais_dia CASCADE;
DROP TABLE IF EXISTS fact_vacunacion, fact_covid_diario, dim_territorio, dim_fecha CASCADE;

CREATE TABLE dim_fecha (
    fecha_key        INTEGER PRIMARY KEY,      -- AAAAMMDD
    fecha            DATE NOT NULL UNIQUE,
    anio             SMALLINT NOT NULL,
    trimestre        SMALLINT NOT NULL,
    mes              SMALLINT NOT NULL,
    nombre_mes       TEXT NOT NULL,
    semana_iso       SMALLINT NOT NULL,
    anio_semana_iso  SMALLINT NOT NULL,
    dia_semana       SMALLINT NOT NULL,        -- 1 = lunes
    es_fin_semana    BOOLEAN NOT NULL
);

-- Jerarquia: pais -> region/estado -> condado (desde la tabla UID)
CREATE TABLE dim_territorio (
    territorio_key   INTEGER PRIMARY KEY,
    uid              BIGINT,
    iso3             CHAR(3),
    pais             TEXT NOT NULL,
    region           TEXT,
    condado          TEXT,
    combined_key     TEXT,
    lat              DOUBLE PRECISION,
    long             DOUBLE PRECISION,
    poblacion        BIGINT,
    nivel            TEXT NOT NULL CHECK (nivel IN ('pais', 'region', 'condado'))
    -- TODO(R3 excelente): vigente_desde / vigente_hasta para Chile nacional -> regional
);

CREATE TABLE fact_covid_diario (
    fecha_key          INTEGER NOT NULL REFERENCES dim_fecha (fecha_key),
    territorio_key     INTEGER NOT NULL REFERENCES dim_territorio (territorio_key),
    confirmados_acum   BIGINT,
    fallecidos_acum    BIGINT,
    recuperados_acum   BIGINT,
    casos_nuevos       BIGINT,          -- diff del acumulado; puede ser negativo
    fallecidos_nuevos  BIGINT,
    retrocede          BOOLEAN,         -- bandera de calidad: acumulado bajo
    esquema            SMALLINT,        -- 1..5
    archivo_origen     TEXT,            -- linaje (R2 excelente)
    fila_origen        INTEGER,
    PRIMARY KEY (fecha_key, territorio_key)
);

-- Fuente externa (OWID vacunacion), a nivel pais
CREATE TABLE fact_vacunacion (
    fecha_key                         INTEGER NOT NULL REFERENCES dim_fecha (fecha_key),
    territorio_key                    INTEGER NOT NULL REFERENCES dim_territorio (territorio_key),
    personas_vacunadas_100            DOUBLE PRECISION,
    personas_vacunacion_completa_100  DOUBLE PRECISION,
    dosis_totales                     BIGINT,
    PRIMARY KEY (fecha_key, territorio_key)
);

CREATE INDEX ix_fact_territorio ON fact_covid_diario (territorio_key);
