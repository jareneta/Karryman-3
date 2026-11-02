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
