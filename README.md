# FinanTrack — Microtaller 6

Aplicación web local de análisis financiero de la empresa **ficticia** NovaTech Store. Estudiante: **Laura Valeria Espejo Mantilla**.

## Ejecutar en VS Code / Windows PowerShell

1. Abre la carpeta `FinanTrack_Dashboard` en VS Code.
2. Abre **Terminal > Nueva terminal**.
3. Ejecuta:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit mostrará una dirección local, normalmente `http://localhost:8501`. Ctrl+C detiene el servidor.

## Pruebas

```powershell
python -m pytest -q
```

## Qué mostrar al profesor

- Seis meses, 60 ventas y 24 registros de costos fijos de carácter ficticio.
- Ocho tarjetas de KPI y cuatro visualizaciones interactivas.
- Filtros por mes, categoría y producto. Los indicadores comerciales responden a los filtros de artículos; los gastos fijos/utilidad total permanecen asociados a toda la empresa.
- Tabla de movimientos, botón para descargar registros filtrados, tres conclusiones y fórmulas.

## Valores esperados del conjunto completo

| Concepto | COP |
|---|---:|
| Ingresos | 37.977.000 |
| Costos variables | 22.064.000 |
| Costos fijos | 5.383.500 |
| Costos totales | 27.447.500 |
| Utilidad operativa | 10.529.500 |
| Margen operativo | 27,73 % |
| Unidades | 344 |
| Punto equilibrio en un mes promedio | 20 unidades (aprox.) |

## Archivos

- `app.py`: interfaz Streamlit y gráficos Plotly.
- `src/calculos.py`: carga, validación, cálculos y conclusiones.
- `data/ventas.csv` y `data/costos_fijos.csv`: datos ficticios.
- `tests/test_calculos.py`: pruebas sobre cálculos, datos y casos límite.
- `guion_video.md`: guía para grabar el video de máximo tres minutos.
- `Microtaller_6_Analisis_Financiero.docx`: informe académico.

## Consideraciones

Los costos fijos se suman una vez por mes y concepto; no se distribuyen arbitrariamente entre productos. El punto de equilibrio se aproxima a partir de la composición histórica de las ventas. La utilidad es **operativa**, no neta: no se modelan impuestos, intereses ni depreciación. El proyecto no requiere conexión externa ni base de datos en la nube.

**Captura para entregar:** ejecuta el dashboard y toma una captura con `Win + Shift + S`; guárdala en `evidencias/dashboard.png` y agrégala al Word en la sección «Dashboard interactivo». Graba el video siguiendo `guion_video.md`.

## Dashboard rediseñado

Requiere Python 3.12 y Streamlit 1.67 o superior (dentro de la rama 1.x).
Navegación: Resumen general, Ventas, Costos y Rentabilidad. Los filtros de periodo, categoría y producto se aplican automáticamente y se conservan al cambiar de vista. Restablecer filtros recupera el periodo completo. Los cuatro KPI y la franja secundaria representan la empresa en el periodo; el detalle comercial de Ventas muestra ingresos, costos variables y contribución sin asignar gastos fijos.

- `src/filtros.py`: selección de periodo y segmento, y productos dependientes.
- `src/dashboard.css` y `.streamlit/config.toml`: diseño y tema visual.
- `tests/test_dashboard.py`: agregaciones e interacción de filtros, vistas y restablecimiento.

La tabla de ventas y su descarga CSV están en una sección expandible. La vista Costos también permite consultar y descargar los costos fijos del periodo. Los CSV conservan valores numéricos en COP.

## Transiciones de los gráficos

`src/animated_plotly.py` registra un componente nativo Streamlit CCv2 con claves estables. Utiliza el JavaScript incluido en el paquete Plotly instalado, sin CDN ni dependencias adicionales de ejecución. `src/animated_plotly.js` conserva cada gráfico y reconcilia su estructura con `Plotly.react`; interpola sus datos con `requestAnimationFrame` y `Plotly.restyle` durante 550 ms, con curva cúbica ease-in-out. Las actualizaciones rápidas sustituyen la transición pendiente desde el estado visible. Los valores finales siempre son los calculados por Python. La preferencia `prefers-reduced-motion` evita las transiciones.

La zona interactiva está aislada con `st.fragment`. Las alturas y la distribución se conservan. Las categorías mantienen etiquetas, orden y colores; una categoría excluida tiene valor cero. Las escalas numéricas se mantienen al reducir la selección y se amplían cuando es necesario. Los gráficos empresariales no se alteran al filtrar productos, porque representan resultados globales.

La API nativa `st.plotly_chart` de Streamlit 1.67 incluye la figura en su identidad. Añadir únicamente `layout.transition` no resuelve su recreación. Además, la [documentación de Plotly.animate](https://plotly.com/javascript/animations/) describe limitaciones de interpolación según el tipo de traza; por eso la dona utiliza interpolación numérica explícita en el navegador. Cuando cambia la vista y se sustituye un gráfico por otro de distinto tipo o significado, se actualiza sin interpolar datos no relacionados. Las transiciones se aplican a actualizaciones de datos del mismo gráfico, no a su primer montaje.

Si cambia el conjunto de puntos (por ejemplo, seis meses frente a un solo mes), Plotly reconcilia las etiquetas y el número de puntos al inicio. Se interpolan los valores comparables; no se garantiza una transformación geométrica continua de una línea de seis puntos a un solo punto. La prueba visual verifica interpolación de los cuatro gráficos entre dos meses individuales. No se inventan ventas para meses excluidos por el filtro.

Pruebas habituales: `python -m pytest -q`. La prueba de navegador es opcional para el entorno de desarrollo: instalar `playwright`, ejecutar `python -m playwright install chromium`, arrancar la app y ejecutar:

```powershell
$env:FINANTRACK_BROWSER_URL = 'http://127.0.0.1:8501'
python -m pytest tests/test_animation_browser.py -q
```

Esta prueba verifica nodos persistentes, valores intermedios reales en los cuatro gráficos, marcador de equilibrio, cifras finales, colores, filtros, tooltips, leyendas y reducción de movimiento. Después de editar el JavaScript del componente, reiniciar el servidor para registrar el módulo actualizado.
