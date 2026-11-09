# Karryman V24 · auditoría del motor (rama `karryman-v24`)

Estado: **investigación**. Nada de lo siguiente es una estrategia validada. No hay conexión con IBKR ni órdenes reales.
`main` no se ha modificado en esta rama.

## 1. ¿Existe el "motor V5"?
No. Se buscó `V5` en todo el repositorio (código, flujos, documentos): las únicas coincidencias son `actions/setup-python@v5`.
Tampoco hay en `main` ni en las demás ramas ningún motor V24/V5. Los motores que sí existen son otros sistemas distintos:
`backtest.py`, `aplus_backtest.py`, `strategy_comparison.py` y `system_backtest.py` (roturas de bases, no es V24).
**No se ha reconstruido V5**: no se tienen su código ni sus archivos (`karryman_v24_*.py`, CSV) de la investigación anterior,
así que sus cifras (CAGR 29-31 %, etc.) **no se pueden reproducir ni verificar** y no se usan.
El motor V24 de este repositorio (`v24_engine.py`) es una implementación nueva a partir de las reglas escritas.

## 2. Reglas implementadas y cómo se verifican
Cada regla se contrasta con una implementación de referencia independiente en `tests/test_v24_audit.py` (29 pruebas en total
con `tests/test_v24_engine.py`; ejecutables con el flujo `v24-backtest.yml`, modo `tests`, o `python -m unittest tests.test_v24_engine tests.test_v24_audit`).

| Regla | Implementación | Verificación |
|---|---|---|
| Momentum 63 sesiones | `C[t]/C[t-63]-1` | referencia con bucle; primeras 63 sesiones sin valor |
| Entrada top 15, permanencia hasta salir del top 45, máx. 15 | `select()` (función pura) | casos límite: rango 15/16/45/46, tope de 15 |
| EMA20 | recursiva `α=2/21`, mínimo 20 observaciones | referencia recursiva |
| ATR14 | suavizado de Wilder sembrado con el primer TR (no con la media simple) | referencia recursiva; frente al ATR clásico (semilla SMA14) la diferencia es <1 % tras unas 700 sesiones |
| Salida por extensión | cierre > EMA20 + 6·ATR14 | sale aunque esté en el top |
| Espera de 10 sesiones | salida en la sesión *i*: sesiones *i+1…i+10* de espera; elegible desde *i+11* | prueba exacta sesión a sesión |
| Ranking | diario (`rank_every=1`) o mensual (`21`, como en el código histórico) | prueba de que no reordena entre rebalanceos |
| Sin información futura | señales con el cierre del día *i*, órdenes a la apertura de *i+1* | indicadores y operaciones idénticos si se altera el futuro |
| Comisión | `max(mínimo, 0,005 $/acción)` limitada al 1 % del importe (si no se impone el mínimo) | pruebas de los tres casos |
| Slippage | compra +bps, venta −bps sobre la apertura | precio de cada operación = apertura × (1±slip) |
| Contabilidad | efectivo ≥ 0, sin apalancamiento | identidad: capital + flujos − comisiones = efectivo final; patrimonio = efectivo + valor de posiciones |
| Protección progresiva | niveles solo 35/50/75/100 %, bajada inmediata, subida de UN nivel tras 5 cierres consecutivos | pruebas de la máquina de estados |

### Aclaraciones de interpretación (no están en las reglas originales)
- **Cooldown:** "10 sesiones" se interpretó como las 10 sesiones siguientes a la señal de salida. Es configurable (`cooldown`).
- **Peso:** con menos de 15 valores seleccionados cada uno pesa `exposición × patrimonio / 15` y el resto queda en efectivo.
- **Volatilidad objetivo:** volatilidad realizada de 20 sesiones de una cesta igualponderada de los valores seleccionados;
  escala = `min(1, 15 % / vol)`; sin apalancamiento.
- **Recuperación de la protección:** el drawdown actual desde el máximo de patrimonio permitiría un nivel superior al vigente.
- **Protección MA100 del patrimonio (25 %):** opcional (`ma100_guard`), desactivada por defecto.
- **Posiciones viables con poco capital:** si `exposición × patrimonio / 15 < importe mínimo`, se reduce el número de posiciones
  a `floor(exposición × patrimonio / mínimo)`. Esto corrige el bloqueo en efectivo observado en la investigación anterior
  (hipótesis: 3.000 $ × 25 % / 15 = 50 $ < 100 $ de orden mínima); no se pudo contrastar con el código antiguo.

## 3. Limitaciones conocidas (no resueltas)
1. **Sesgo de supervivencia.** El universo del backtest son valores cotizados *hoy*. Yahoo Finance no suele conservar precios de
   empresas deslistadas (ver §4). Hasta resolverlo, los resultados solo sirven para comparar políticas entre sí.
2. **Dividendos y splits.** Se usan precios ajustados de Yahoo (`auto_adjust=True`: splits y dividendos reinvertidos en O/H/L/C).
   Esto da rentabilidad total correcta, pero: (a) las cantidades de acciones y los importes mínimos son sobre precios *ajustados*
   (el precio histórico real era más alto), de modo que la comisión por acción queda algo sobrestimada; (b) un split sin ajustar
   o un error de datos se detecta solo parcialmente (`calidad_datos`: saltos diarios >40 %).
3. **Efectivo sin rendimiento.** El efectivo no devenga intereses (lastra a V24 frente a SPY, sobre todo desde 2022).
4. **Costes.** Slippage fijo de 5 pb por lado, sin impacto de mercado ni restricciones de préstamo; la comisión por defecto
   (0,005 $/acción, mínimo configurable) es una **hipótesis**, no la tarifa real de IBKR (verificar en su web).
5. **Delistadas en la cartera.** Si una posición deja de cotizar, se liquida al último cierre conocido (puede ser optimista).
6. **Datos de IBKR.** No se han usado en esta rama (no hay conexión desde el entorno de trabajo).
7. **Muestra.** Las ejecuciones hasta ahora usan 300 acciones al azar; los resultados dependen de la muestra.

## 4. Fuentes de datos con empresas deslistadas
Ver `docs/V24_DATOS.md` (se completa con las mediciones del flujo en modo `fuentes`; los ficheros de resultado están en `results/v24/`).

## 5. Cómo reproducir
- Pruebas: Actions → "Karryman V24 backtest" → modo `tests` (o `python -m unittest tests.test_v24_engine tests.test_v24_audit`).
- Backtest: modo `backtest` con `symbols`, `seed`, `capital`, `fee_min`, `min_order`, `fractional`. Cada ejecución guarda
  `results/v24/v24_results_<run_id>.json` en la rama con parámetros y `commit`.
- Fuentes: modo `fuentes` → `results/v24/v24_fuentes_<run_id>.json`.
