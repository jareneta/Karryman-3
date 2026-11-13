# Veredicto H14 · "no pelees contra la Fed" (criterios de `docs/V24_H14_LIQUIDEZ_FED.md`, sin modificarlos)

Fichero: `results/v24/v24_macro_43519900818.json` · commit `c290758` · `^GSPC` + `^IRX`, datos hasta 2020-12-31 (2021-2026 **no usado**) · dividendo aproximado 2 %/año · 0,10 % por cambio de posición.
Regla: S&P 500 1x salvo cuando el rendimiento a 3 meses ha subido > 0,5 pp respecto a hace 126 sesiones (25,7 % de las sesiones); entonces, en letras del Tesoro.

| | CAGR 1961-89 | CAGR 1990-2009 | CAGR 2010-20 | **CAGR 1961-2020** | Caída máx. 1961-2020 | Sharpe |
|---|---|---|---|---|---|---|
| **B** · comprar y mantener | 8,61 % | 7,96 % | 13,77 % | **9,38 %** | −55,5 % | 0,63 |
| **S** · no pelees contra la Fed (H14) | 13,18 % | 5,95 % | 12,54 % | **10,66 %** | −56,0 % | 0,76 |

Caída máxima por periodo, S frente a B: −26,0 % frente a −46,4 % (1961-89); −56,0 % frente a −55,5 % (1990-2009); −33,8 % frente a −33,8 % (2010-20).

| Criterio | Resultado |
|---|---|
| M1. CAGR de S > B en los tres periodos | **No** (1990-2009: 5,95 % < 7,96 %; 2010-2020: 12,54 % < 13,77 %) |
| M2. IC 99,64 % de la diferencia mensual media con límite inferior > 0 | **No**: media +0,08 %/mes, IC [−0,15 % ; +0,32 %] |
| M3. Sharpe de S ≥ Sharpe de B | Sí (0,76 frente a 0,63) |
| M4. Caída máxima de S no peor que la de B | **No** (−56,0 % frente a −55,5 %) |

## Veredicto registrado
**H14 no supera al S&P 500** y tampoco "reduce el riesgo sin superar en rentabilidad" (falla M4 por un margen mínimo). No se prueban variantes ni se desbloquea la prueba final 2021-2026.

## Lectura
- **Funciona en 1961-1989** (+4,6 pp anual y caída de −26 % frente a −46 %, periodo de inflación y ciclos de subidas de tipos) pero **no en 1990-2009**: las caídas de 2000-2002 y 2008 no vinieron precedidas por un endurecimiento de tipos que activara la señal, y en 2010-2020 los tipos casi cero la dejaron casi siempre en el mercado.
- La ventaja total (+1,3 pp anual) no es estadísticamente distinguible de cero con la corrección por pruebas múltiples. La regla de liquidez no es una protección general.
- **Sensibilidades (no deciden):** el filtro de curva de tipos rinde 10,05 % con caída −57 %; la media de 200 sesiones sola, 9,18 % con caída −23,9 %; **liquidez Y media de 200 sesiones**: 10,32 % anual, caída −21,0 % y Sharpe 1,11 en 1961-2020
  (por periodo: 13,5 %, 8,3 % y 5,7 % frente a 8,6 %, 8,0 % y 13,8 %), es decir, mucha menos caída con rentabilidad parecida a comprar y mantener, pero **por debajo del índice en 2010-2020**.
  Es la combinación con mejor perfil de riesgo, **elegida después de ver resultados**: no se presenta como validada.
- La sensibilidad "liquidez Y media de 200 sesiones" solo podría contrastarse con datos nuevos (la prueba final 2021-2026, que sigue sin abrirse); eso requeriría registro previo y confirmación explícita del usuario.

## Limitaciones
`^IRX` no es el tipo oficial de la Fed; con tipos cercanos a cero la señal casi no cambia; índice de precio con dividendo aproximado; costes y fiscalidad simplificados; catorce hipótesis probadas en esta fase.
