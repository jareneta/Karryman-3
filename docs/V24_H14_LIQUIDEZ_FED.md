# H14 · "No pelees contra la Fed": S&P 500 solo cuando la política monetaria no se endurece (inspirado en Druckenmiller) · registro previo

Fecha de registro: 2026-11-13, **antes de ejecutar H14**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Alcance y advertencia
El método de Stanley Druckenmiller es discrecional (macro, divisas, tipos, análisis técnico, concentración según convicción). **No es reproducible mecánicamente.** H14 prueba solo una aproximación de una idea que él repite ("la liquidez y la Fed mueven el mercado"):
estar en el S&P 500 solo cuando los tipos de interés a corto plazo no suben de forma apreciable. Un resultado negativo no dice nada sobre Druckenmiller, solo sobre esta regla.

## 1. Estrategia
Datos: S&P 500 (`^GSPC`, precio) y rendimiento de las letras del Tesoro a 3 meses (`^IRX`, que aproxima la política monetaria), Yahoo Finance. Dividendo aproximado del 2 %/año en todas las estrategias invertidas; sin comisión (1x).
- **Referencia (B):** S&P 500 1x comprar y mantener.
- **H14 (S):** invertido en el S&P 500 1x salvo cuando el **rendimiento a 3 meses ha subido más de 0,5 puntos porcentuales respecto a hace 126 sesiones** (régimen de endurecimiento); en ese caso, en letras del Tesoro al tipo del día.
  La señal se calcula al cierre y se ejecuta al día siguiente; coste por cambio de posición 0,10 %.
- Parámetros (0,5 pp y 126 sesiones) fijados aquí y **no se modificarán**.

## 2. Periodos y bloqueo
Evaluación 1961-01-01 a 2020-12-31 (el primer año se usa para la ventana de 126 sesiones), en tres periodos independientes: **P1 1961-1989, P2 1990-2009, P3 2010-2020**. **Prueba final 2021-2026 bloqueada** (los datos posteriores a 2020-12-31 no se usan).

## 3. Criterios (fijados antes)
Catorce hipótesis probadas en esta fase (Bonferroni k = 14: nivel 99,64 %).
- **M1.** CAGR de S > CAGR de B en **cada uno de los tres periodos**.
- **M2.** En todo 1961-2020, IC (99,64 %, remuestreo por meses, 5.000) de la media de la diferencia de rentabilidades mensuales (S − B) con límite inferior > 0.
- **M3.** En todo 1961-2020: Sharpe de S ≥ Sharpe de B.
- **M4.** En todo 1961-2020: caída máxima de S no peor que la de B.
- **H14 "supera al S&P 500"** si cumple M1, M2, M3 y M4. Si falla M1 o M2 pero cumple M3 y M4, el veredicto será **"reduce el riesgo sin superar al índice en rentabilidad"**.
- La prueba final 2021-2026 solo se abriría una vez y con confirmación explícita del usuario.

## 4. Sensibilidades (se informan, no deciden)
Umbrales de 0,25 y 1,0 pp; ventanas de 63 y 252 sesiones; filtro de curva de tipos (rendimiento a 10 años `^TNX` − rendimiento a 3 meses > 0); combinación liquidez Y media de 200 sesiones; solo media de 200 sesiones.

## 5. Limitaciones declaradas
`^IRX` es el rendimiento de mercado de las letras a 3 meses, no el tipo oficial de la Fed; con tipos cercanos a cero (2009-2015) la señal casi no cambia; índice de precio con dividendo aproximado; costes y fiscalidad simplificados; la explicación macro de cada periodo no se prueba.

## 6. Qué NO se hará
Cambiar el umbral, la ventana o el activo tras ver resultados; elegir una sensibilidad como principal; elegir periodos a posteriori; mirar 2021-2026 sin confirmación.
