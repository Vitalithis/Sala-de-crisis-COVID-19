-- Vistas de consumo: las usan analisis, modelos y tablero. NO consultar los CSV.

-- Pais x dia (roll-up de regiones/condados al pais)
-- TODO(R3): validar que no se dupliquen paises que reportan a la vez total y regiones.
CREATE OR REPLACE VIEW vw_pais_dia AS
SELECT
    f.fecha,
    t.pais,
    MAX(t.iso3)               AS iso3,
    SUM(c.confirmados_acum)   AS confirmados_acum,
    SUM(c.fallecidos_acum)    AS fallecidos_acum,
    SUM(c.casos_nuevos)       AS casos_nuevos,
    SUM(c.fallecidos_nuevos)  AS fallecidos_nuevos
FROM fact_covid_diario c
JOIN dim_fecha f      ON f.fecha_key = c.fecha_key
JOIN dim_territorio t ON t.territorio_key = c.territorio_key
GROUP BY f.fecha, t.pais;

-- Vista unica que consumen pronosticar() y alerta():
-- territorio = pais o region de Chile, con poblacion para tasas por 100.000.
-- TODO(R3): definir con Modelos; columnas fijas: territorio, fecha, casos_nuevos,
--           fallecidos_nuevos, poblacion.
