# Veredicto H1-H4 (criterios de `docs/V24_HIPOTESIS.md`, sin modificarlos)

Fichero de datos: `results/v24/v24_hipotesis_42679809927.json` · commit `fb5a71c` · datos hasta 2020-12-31 (prueba final 2021-2026 **no cargada**).
Costes de la prueba: 5 pb de slippage por lado + 0,005 $/acción; 100.000 $, fraccionarias. Universo: S&P 500 point-in-time con deslistadas.
Referencias 2010-2020: SPY 13,72 % anual, caída −33,7 %, Sharpe 0,83, Calmar 0,41 · cartera igualponderada (con costes) 13,42 %, −39,5 %, Sharpe 0,76.

| Hipótesis | CAGR 2010-16 | CAGR 2017-20 | CAGR 2010-20 | Caída máx. | Sharpe | C1 | C2 | C3 | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| H1 Momentum 12-1 | 10,15 % | 8,38 % | 9,55 % | −43,1 % | 0,49 | no | no | no | **no candidata** |
| H2 Baja volatilidad | 14,18 % | 11,91 % | 13,36 % | −25,4 % | 1,09 | sí | **no** | sí | **no candidata** |
| H3 H1 + filtro SPY>MA200 | 3,47 % | 4,78 % | 4,01 % | −40,8 % | 0,30 | sí | no | no | **no candidata** |
| H4 Igualponderada + filtro | 5,48 % | 6,94 % | 6,09 % | −27,2 % | 0,52 | | | | **no candidata** (CAGR < 80 % de la referencia 13,42 %) |

Placebos aleatorios (10 semillas, 2010-2020): sin filtro mediana 10,46 % (rango 6,16-13,41 %); con filtro mediana 2,74 % (0,54-6,51 %).

**C2** (IC 98,75 % de la diferencia media mensual frente a los placebos): H1 [−0,70 %; +0,83 %], H2 [−0,61 %; +0,90 %], H3 [−0,61 %; +0,87 %];
en los tres casos el intervalo incluye 0.

## Lectura
- **Según los criterios registrados, ninguna hipótesis es candidata.** Conclusión registrada: **no hay ventaja demostrable** en este conjunto de pruebas.
  La prueba final 2021-2026 **no se desbloquea** y no se ha visto.
- **H2 (baja volatilidad)** es la única con un patrón llamativo (13,4 % anual, caída −25 %, Sharpe 1,09, ≥ SPY en Sharpe y Calmar). Pero con 15 valores el ruido
  es grande: los placebos aleatorios llegan a 13,4 % y el intervalo frente a ellos incluye 0. Es un resultado **sugerente, no demostrado**. Con estas reglas no se rescata.
- **H1** (momentum 12-1) no supera a los placebos. **H3** y **H4**: el filtro de media de 200 sesiones sobre SPY empeoró mucho el rendimiento en 2010-2020
  (muchos cambios de señal y retraso de ejecución) aunque redujo algo la caída máxima de H4 (−27 % frente a −39 %).
- Los placebos con filtro dan 2,7 % porque el filtro deja a la cartera aleatoria en efectivo ~14 % del tiempo y con cambios de señal costosos; eso muestra lo costoso que fue el filtro en este periodo.

## Limitaciones
Solo S&P 500; 10 semillas de placebo; 15 valores (alta varianza); datos de un tercero sin licencia y sin auditoría independiente; efectivo sin rendimiento;
costes hipotéticos; 4 hipótesis probadas (Bonferroni aplicado en C2). Un resultado no significativo con esta potencia no demuestra que no exista ventaja, solo que no la hemos demostrado.

## Siguiente paso permitido por las reglas
No se buscan más hipótesis para rescatar un resultado. Lo que sí es legítimo es **replicar H2 en un periodo independiente anterior** (1997-2009, ya disponible en el
conjunto de datos), registrando antes la hipótesis y los criterios, y solo si se acuerda explícitamente.
