# Karryman · hipótesis registradas ANTES de probar (rama `karryman-v24`)

Fecha de registro: 2026-11-09, antes de ejecutar ninguna de estas pruebas. Cualquier cambio posterior de reglas o criterios se
anota al final como **enmienda con fecha y motivo**; no se editan las secciones 1-4.

## 1. Hipótesis (cerradas: no se ajustan parámetros después de ver resultados)
Universo: S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`). Ranking mensual (cada 21 sesiones), peso igual,
15 posiciones (entran top 15, permanecen hasta salir del top 45), sin protección progresiva, sin volatilidad objetivo, sin salida por
extensión. Órdenes a la apertura de la sesión siguiente.

| ID | Hipótesis | Definición |
|---|---|---|
| H1 | Momentum 12-1 | Rentabilidad entre *t−252* y *t−21* sesiones (se omite el último mes). Mayor mejor. |
| H2 | Baja volatilidad | Desviación típica de las rentabilidades diarias de 63 sesiones. Menor mejor. |
| H3 | H1 con filtro de mercado | H1, pero en efectivo si el cierre de SPY es ≤ su media de 200 sesiones (señal al cierre, orden en la apertura siguiente). |
| H4 | Filtro de mercado sobre el índice | Todos los miembros del S&P 500 con peso igual (rebalanceo mensual), en efectivo si SPY ≤ su media de 200 sesiones. |

Cuatro hipótesis en total (corrección de Bonferroni con k = 4).

## 2. Datos y bloqueo de la prueba final
- **Entrenamiento:** 2010-01-01 a 2016-12-31 · **Validación:** 2017-01-01 a 2020-12-31.
- **Prueba final (2021-2026): bloqueada.** Los datos posteriores al 2020-12-31 **no se cargan** en estas ejecuciones (`end=2020-12-31`).
  Solo se desbloquea para las hipótesis que superen los criterios de la sección 4, y solo tras confirmarlo con el usuario.
- Costes del test de señal: slippage 5 pb por lado + 0,005 $/acción, capital 100.000 $, acciones fraccionarias. La viabilidad con
  3.000 $ solo se estudia si alguna hipótesis pasa.

## 3. Referencias y controles
- SPY comprado y mantenido; cartera igualponderada diaria de los miembros del S&P 500 (sin costes).
- **Placebos:** 10 semillas de ranking aleatorio mensual con las mismas reglas de cartera. Para H3, placebos aleatorios **con el mismo
  filtro de mercado** (aíslan el efecto de la señal del efecto del filtro). H4 se compara con la cartera igualponderada sin filtro.

## 4. Criterios de aceptación (todos fijados antes)
Una hipótesis H1-H3 se considera **candidata** si cumple C1 y C2; **supera al índice** si además cumple C3:
- **C1.** CAGR de la hipótesis > mediana de CAGR de sus placebos, **en entrenamiento y en validación por separado**.
- **C2.** Intervalo de confianza del 98,75 % (remuestreo por bloques mensuales, 5.000 muestras) de la media de la diferencia de
  rentabilidades mensuales frente a la media de sus placebos, en 2010-2020, con límite inferior > 0.
- **C3.** En 2010-2020: Sharpe ≥ Sharpe de SPY, **o** (Calmar ≥ Calmar de SPY y CAGR ≥ 80 % del de SPY).
- **H4** (filtro sobre el índice) es candidata si, frente a la cartera igualponderada sin filtro en 2010-2020, reduce la caída máxima
  y mantiene el CAGR ≥ 80 % del de la igualponderada; no se compara contra placebos.
- Si ninguna pasa: la conclusión registrada es **"no hay ventaja demostrable"**; no se buscan más hipótesis para rescatar un resultado.

## 5. Qué NO se hará
Ajustar ventanas, umbrales o número de posiciones tras ver resultados; añadir hipótesis después; mirar la prueba final antes de tiempo;
presentar como validada una hipótesis sin pasar los criterios.

## Enmiendas (no cambian hipótesis, criterios ni datos)
**2026-11-09, antes de ver ningún resultado de H1-H4.** La primera ejecución se canceló tras 55 min sin terminar. Causa: `_afford` del
motor reducía una cantidad fraccionaria un 0,1 % por iteración (hasta ~14.000 iteraciones por orden cuando faltaba efectivo).
Se sustituyó por una estimación directa más un ajuste fino. Comprobación sobre datos sintéticos: con acciones enteras resultado idéntico;
con fraccionarias el patrimonio final difiere ~1e-6 en términos relativos y desaparecen operaciones de importe despreciable. Velocidad ×16-28.
Los resultados válidos A y B de `docs/V24_RESULTADOS.md` se generaron con la versión anterior del motor (commit indicado en cada JSON).
Implementación aclarada: en todas las carteras (hipótesis, referencias y placebos) los pesos se reajustan a diario al objetivo (banda 0);
la selección de valores se actualiza cada 21 sesiones. También se subió el límite de tiempo de la ejecución a 150 min.
