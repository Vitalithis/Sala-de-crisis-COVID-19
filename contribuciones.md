# Contribuciones del equipo y uso de IA generativa

## Integrantes y responsabilidades

| Integrante | Rol principal | Módulos y entregables desarrollados |
| :--- | :--- | :--- |
| **Nicolás Urrutia** | Rol A · Ingeniería de datos y DW | `src/01_ingesta_y_unificacion.py`, `src/02_construir_dw.py`, `src/ingesta/`, `src/dw/`, `src/pipeline.py`, `sql/`, `notebooks/01_ingesta.ipynb`, `notebooks/03_dw_olap.ipynb`, `docs/arquitectura.md`, secciones 2 y 4 de `docs/informe_tecnico.md`. |
| **Dan Ocampo** | Rol B · Calidad, ética y fuentes externas | `src/03_calidad_y_olap.py`, `src/calidad/reglas.py`, `src/calidad/indice.py`, `src/externas/owid.py`, `src/proteccion/supresion.py`, `notebooks/02_calidad.ipynb`, `notebooks/04b_P3_P4_P7.ipynb`, `notebooks/06_proteccion_datos.ipynb`, `docs/diccionario_datos.md`, `docs/decisiones_calidad.md`, `docs/proteccion_datos.md`, secciones 3, 5 (P3, P4, P7) y 7 de `docs/informe_tecnico.md`, mejoras estéticas y tabla día a día en `dashboard/app.py`. |
| **Cristian** | Rol C · Modelos predictivos y minería | `src/04_modelos_y_alerta.py`, `src/modelos/`, `tests/test_basicos.py`, `notebooks/04c_P5_P6.ipynb`, `notebooks/05_mineria_prediccion.ipynb`, secciones 5 (P5, P6) y 6 de `docs/informe_tecnico.md`. |
| **Leo** | Rol D · Tablero, análisis P1–P2 y comunicación | `dashboard/app.py`, `src/05_analisis_preguntas.py`, `notebooks/00_exploracion.ipynb`, `notebooks/04a_P1_P2.ipynb`, `README.md`, `docs/informe_comite.md`, `docs/guion_comite.md`, ensamblado de `docs/informe_tecnico.md` y `contribuciones.md`. |

## Declaración de uso de herramientas de IA generativa

En cumplimiento de las normas del curso, declaramos que utilizamos herramientas de IA generativa (**Gemini**, **Cursor** y **Antigravity**) como apoyo para:
- Estructuración del plan de trabajo, depuración de errores de entorno/librerías (Python/uv, PowerShell, Plotly) y optimización de consultas SQL en DuckDB.
- Asistencia en la redacción técnica del `README.md`, diccionario de datos, documentación de calidad/ética, pruebas unitarias y diseño de visualizaciones en Streamlit.

Todo el código fue ejecutado, verificado contra los datos reales de Johns Hopkins CSSE, Our World in Data y Banco Mundial, y estudiado por todos los integrantes para su defensa y ejecución en vivo ante el Comité.
