# Guion para la sesión del Comité (martes 24-nov, 15 minutos)

## Relato (7 minutos, con el tablero; nada de diapositivas llenas de texto)

| Min | Quién | Contenido |
|---|---|---|
| 0:00 a 1:00 | D | Encargo y qué construimos (arquitectura en una imagen) |
| 1:00 a 2:30 | A | Plataforma: 1.143 reportes, 5 esquemas, capas, DW |
| 2:30 a 3:30 | B | Confiabilidad de los datos (P4) y decisiones de calidad |
| 3:30 a 5:30 | D y B | Hallazgos P1, P2, P3 y P7 en el tablero |
| 5:30 a 6:30 | C | Grupos de países (P5) y ómicron (P6): ¿se podía anticipar? |
| 6:30 a 7:00 | D | Tres recomendaciones |
| 0:00 a 1:00 | Leo (D) | Encargo y qué construimos (arquitectura en una imagen) |
| 1:00 a 2:30 | Nicolás (A) | Plataforma: 1.143 reportes, 5 esquemas, capas, DW |
| 2:30 a 3:30 | Dan (B) | Confiabilidad de los datos (P4) y decisiones de calidad |
| 3:30 a 5:30 | Leo (D) y Dan (B) | Hallazgos P1, P2, P3 y P7 en el tablero |
| 5:30 a 6:30 | Cristian (C) | Grupos de países (P5) y ómicron (P6): ¿se podía anticipar? |
| 6:30 a 7:00 | Leo (D) | Tres recomendaciones |

## Desafío en vivo (4 minutos)

1. D: en el tablero, filtra el territorio y la fecha sorteados y lee los KPI.
2. C: muestra el estado de `alerta(territorio, fecha)` con su umbral.
3. C: ejecuta `pronosticar(territorio, fecha_corte, 14)` y lo compara con lo real.
4. A: respaldo técnico (PostgreSQL arriba, datos cargados).
1. Leo (D): en el tablero, filtra el territorio y la fecha sorteados y lee los KPI.
2. Cristian (C): muestra el estado de `alerta(territorio, fecha)` con su umbral.
3. Cristian (C): ejecuta `pronosticar(territorio, fecha_corte, 14)` y lo compara con lo real.
4. Nicolás (A): respaldo técnico (PostgreSQL arriba, datos cargados).

## Lista antes de entrar

- [ ] Computador definido, con PostgreSQL, el DW cargado y el tablero corriendo
- [ ] Probados al menos 3 sorteos (país y región de Chile, fechas distintas)
- [ ] Plan B: capturas y notebook 05 ya ejecutado
- [ ] Cada integrante repasó las partes de los demás (preguntas a cualquiera)
