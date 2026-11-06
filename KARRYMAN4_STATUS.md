# Karryman 4.0 — estado de seguridad y validación

## Uso actual
- Desarrollo aislado en `karryman-4-automatizacion-segura`. No fusionar a `main` sin aprobación.
- `review.html`: revisión móvil de referencias históricas. Decisiones solo en localStorage.
- `cartera.html`: cartera manual o CSV, almacenada únicamente en el navegador con clave `karryman_portfolio_v1`.
- `risk.js`: cálculo orientativo de tamaño, efectivo y riesgo agregado; sin acceso a bróker. No impone límite de riesgo agregado.
- `discovery.py`: explora lotes rotativos; no cubre todo el mercado en cada ejecución.
- `screener.py`: aproximación con Yahoo Finance, NO integración con Stock Analysis ni Finviz. Campos ausentes quedan pendientes.
- `setups.py`: heurística técnica A+; no constituye señal operable verificada.
- `review.py`: descarta sesiones de más de cinco días naturales.

## Investigación histórica
- `backtest.py`: baseline de ruptura de 30 sesiones, entrada a apertura siguiente, stop y +2R, comisiones y deslizamiento. No reproduce Karryman A+.
- `backtest_report.py`: descarga hasta cinco años para ocho símbolos predeterminados, ejecuta backtests separados y genera JSON. No se debe interpretar como resultado de cartera ni evidencia de rentabilidad futura.
- `.github/workflows/backtest.yml`: ejecución **manual**, guarda artefacto temporal de CI; no publica cifras en GitHub Pages.
- Limitaciones: sesgo de supervivencia, selección de símbolos, universo pequeño, ausencia de exclusiones por resultados, sin prueba fuera de muestra, sin benchmark ajustado a exposición y sin simulación multi-posición.

## Antes de operaciones reales
1. Validar el barrido y exactitud de filtros con fuentes verificables.
2. Backtest sin lookahead de reglas A+ completas, universo histórico con deslistadas, costes y periodos fuera de muestra.
3. Verificar calidad de datos y earnings; controlar riesgo de cartera, concentración y correlación.
4. Desarrollar servicio **privado** de IBKR (no en GitHub Pages), con autenticación, conciliación de posiciones, paper trading, logs y kill switch.
5. Requerir aprobación explícita por orden, límites de precio, cuenta y cantidad; nunca enviar órdenes automáticamente por señales no verificadas.

**Estado:** no hay conexión ni órdenes IBKR. No se ha demostrado ventaja matemática.

## Comparativa A+ de stops (investigación)
- `aplus_backtest.py` permite `stop_mode='intraday'` o `stop_mode='close_next_open'`; en este último caso una ruptura por cierre se ejecuta a la siguiente apertura, con riesgo de hueco.
- `aplus_stop_report.py` y `.github/workflows/aplus-compare.yml` preparan un informe de 5 años sobre SPY, QQQ, AAPL y MSFT. El workflow es manual y no se ejecuta por sí solo en la rama de desarrollo.
- **No hay resultados históricos de este informe hasta que se ejecute el workflow.** El modo intradía incorpora objetivo +2R, mientras que el modo por cierre no; por tanto, la diferencia no identifica exclusivamente el efecto del stop. Se requiere una comparación controlada y muestra independiente antes de afirmar ventaja.

## Plan de órdenes (`plan.html`)
Flujo: tus criterios (Discovery → Screener → Setups) → `plan.py` calcula pivote, stop, +1R, +2R y estado → `plan.html` cruza con tu cartera local y propone; **tú decides** y pones la orden en IBKR.
- **Entrada**: cierre por encima del pivote (máximo de 30 sesiones en bases; de 5 en pullbacks) con volumen ≥ 1,4× la media de 50 (pullback ≥ 1,1×). No comprar a más de pivote +5 % (EXTENDIDA). Estados: ESPERANDO, ACTIVADA, EXTENDIDA, FALLIDA, INVALIDADA, RIESGO_ALTO (stop > 12 %).
- **Stop inicial**: mínimo de las 10 sesiones previas al disparo (base) o de las 5 (pullback). Stop por cierre.
- **Salida**: a +2R vender 1/3 y subir el stop del resto a breakeven; el runner sale con un cierre bajo EMA20 (configurable EMA10/MA50). +1R solo informa.
- **Tamaño**: 1 % de riesgo por operación, 6 % de riesgo total hasta stops, 20 % de peso máximo y efectivo disponible (`trade_manager.js` + `risk.js`). Si alguna posición no tiene stop, no se proponen compras. El margen (efectivo negativo o compra mayor que el efectivo) no bloquea: solo se avisa.
- **Resultados**: se busca la fecha en Yahoo para todas las candidatas; a 14 días o menos de resultados la entrada se bloquea. Si Yahoo no la publica, aviso para comprobarla en IBKR.
- **Motivos**: cada candidata indica por qué espera, está bloqueada o descartada; la sección 5 muestra los descartes de Discovery y Screener con el criterio que no cumplen.
- **Posiciones**: cada análisis (manual desde la app o automático, lun–vie 23:50 UTC) revisa los tickers de `data/tracked.json`. Solo se publican tickers; cantidades, precios y patrimonio se quedan en el navegador.
- Los workflows se lanzan sobre `main`: hay que fusionar esta rama para que `plan.yml` exista allí.

## Reglas actualizadas tras el backtest (nov. 2026)
Backtest 2015–2026 (`system_backtest.py`, 4 muestras de 700–1.500 acciones, placebo y fuera de muestra):
- **Solo rupturas de base** (los pullbacks rendían casi como entradas al azar).
- **Vender 1/3 en +4R** y subir el stop del resto a breakeven.
- **Runner**: sale cuando un **cierre semanal** queda por debajo de la **media de 50 semanas**.
- Stop por cierre (mejor que intradía); sin breakeven en +1R ni stop por tiempo (empeoran).
- Esperanza por operación (2 muestras de 1.500): sistema anterior +0,12/+0,15R; nuevo +0,47/+0,66R;
  placebo +0,05/+0,07R. Sesgo de supervivencia: las salidas largas lo amplifican.
- **Universo**: lista exportada del screener de Stock Analysis (`data/universe.json`); se revisan todas
  las acciones cada día. Discovery/Screener/Setups quedan solo para ejecución manual.
