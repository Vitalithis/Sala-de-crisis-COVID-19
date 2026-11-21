-- R3 - Consultas OLAP sobre el DW (no sobre el CSV). Plantillas: validar y completar.

-- ROLL-UP: casos nuevos de Chile, de dia -> mes -> anio
SELECT f.anio, f.mes, SUM(c.casos_nuevos) AS casos
FROM fact_covid_diario c
JOIN dim_fecha f      ON f.fecha_key = c.fecha_key
JOIN dim_territorio t ON t.territorio_key = c.territorio_key
WHERE t.pais = 'Chile'
GROUP BY ROLLUP (f.anio, f.mes)
ORDER BY f.anio, f.mes;

-- DRILL-DOWN: de Chile (pais) a sus regiones en 2021
SELECT t.region, SUM(c.casos_nuevos) AS casos
FROM fact_covid_diario c
JOIN dim_fecha f      ON f.fecha_key = c.fecha_key
JOIN dim_territorio t ON t.territorio_key = c.territorio_key
WHERE t.pais = 'Chile' AND f.anio = 2021
GROUP BY t.region
ORDER BY casos DESC;

-- SLICE: un solo corte (anio 2022)
-- TODO

-- DICE: varias condiciones (paises de Sudamerica x primer semestre 2021)
-- TODO
