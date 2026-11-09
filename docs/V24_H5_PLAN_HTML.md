# H5 · sistema de `plan.html` (roturas de base con volumen) · registro previo

Fecha de registro: 2026-11-09, **antes de ejecutar nada de H5**. Las secciones 1-5 no se editan; los cambios van como enmienda fechada al final.

## 1. Qué se prueba (reglas tal como están en `plan.py`, `trade_levels.py`, `trade_manager.js`)
- **Filtro técnico de candidatas:** precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000; cierre > MA50 > MA200 y MA200 subiendo (hoy > hace 20 sesiones);
  cierre ≥ 85 % del máximo de 252 sesiones; fuerza relativa de 63 sesiones mayor que la de SPY.
- **Entrada (solo roturas):** cierre > máximo de las 30 sesiones previas (pivote) con volumen ≥ 1,4 × la media de 50 sesiones; no se compra si el cierre
  o la apertura siguiente superan el pivote en más de un 5 %. Orden a la apertura de la sesión siguiente a la señal.
- **Stop:** mínimo de las 10 sesiones previas; si el riesgo supera el 12 % no se entra. Stop por cierre/apertura según el motor `system_backtest.py`
  (configuración `FINAL`: parcial y gestión idénticas a las de la app).
- **Salida:** al llegar a +4R se vende 1/3 y el stop del resto sube a breakeven; el resto (runner) sale con un cierre **semanal** bajo la media de 50 semanas.
  Sin pullbacks, sin salida por clímax, sin filtro de mercado.
- **Tamaño de cartera:** 1 % de riesgo por operación, 6 % de riesgo abierto total, máximo 20 % de peso; coste 0,10 % por lado; sin apalancamiento.
- **Fuera del alcance (no comprobable con datos de la fecha):** el filtro de fundamentales del cribador de Stock Analysis (crecimiento de ventas, etc.) refleja el estado
  actual de cada empresa; aplicarlo al pasado sería mirar al futuro. **Se prueba el sistema técnico y su gestión, no el filtro de fundamentales.**

## 2. Datos y bloqueo
- Universo: S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`); una señal solo cuenta los días en que el valor era miembro del índice.
  **Limitación:** son empresas grandes; no equivale a las acciones de crecimiento pequeñas o medianas que puede mostrar un cribador.
- Entrenamiento 2010-01-01 a 2016-12-31; validación 2017-01-01 a 2020-12-31 (el historial previo se usa solo para calcular indicadores).
- **Prueba final 2021-2026 bloqueada:** los datos posteriores a 2020-12-31 no se cargan. Solo se abrirá si H5 es candidata y tras confirmarlo con el usuario.
- Una posición abierta cuando el valor deja de cotizar se cierra al último precio disponible (optimista en quiebras o fusiones abruptas).

## 3. Controles
- SPY comprado y mantenido (2010-2020).
- **Placebo de entrada aleatoria** (control ya implementado en `system_backtest.py`): mismas condiciones de liquidez y mismos stops y salidas, fecha de entrada aleatoria;
  10 semillas. Se usa tanto para operaciones individuales como para carteras.

## 4. Métricas y criterios (fijados antes)
- **Por operación:** esperanza en múltiplos de R (media de R), con IC del 95 % por remuestreo (5.000), número de operaciones, % de aciertos. Si hay menos de 300 operaciones
  en 2010-2020, el veredicto es "inconclusivo".
- **Q1.** La esperanza en R es > 0 con límite inferior del IC 95 % > 0 en 2010-2020, y su media es > 0 en entrenamiento y en validación por separado.
- **Q2.** Esperanza de H5 − esperanza de los placebos agrupados (10 semillas) > 0, con límite inferior del IC 95 % de la diferencia > 0 en 2010-2020.
- **H5 es candidata** si cumple Q1 y Q2 (una sola hipótesis: k = 1).
- **Cartera (reglas de tamaño de la sección 1):** CAGR, caída máxima, Sharpe, Calmar.
  - **Q3.** En 2010-2020: Sharpe ≥ el de SPY, o (Calmar ≥ el de SPY y CAGR ≥ 80 % del de SPY).
  - **Q4.** CAGR de H5 > mediana de CAGR de las 10 carteras placebo, en entrenamiento y en validación por separado.
  - **H5 supera al índice** si es candidata y cumple Q3 y Q4.
- Si H5 no es candidata: la conclusión registrada es "no hay ventaja demostrable en este universo y periodo"; no se prueban variantes ni parámetros distintos.

## 5. Qué NO se hará
Cambiar umbrales (1,4× de volumen, +4R, ventanas), activar variantes (pullbacks, clímax, filtro de mercado), elegir periodos después de ver resultados, mirar 2021-2026 antes de tiempo.
