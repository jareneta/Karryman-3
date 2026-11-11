# Veredicto H12 · S&P 500 2x con filtro de tendencia (criterios de `docs/V24_H12_INDICE_APALANCADO.md`, sin modificarlos)

Fichero: `results/v24/v24_lev_43001112850.json` · commit `f04556a` · `^GSPC` + `^IRX`, datos hasta 2020-12-31 (2021-2026 **no usado**) · dividendo aproximado 2 %/año · comisión del fondo 0,9 %/año · financiación al tipo de las letras · 0,10 % por cambio de posición.

| | CAGR 1960-89 | CAGR 1990-2009 | CAGR 2010-20 | **CAGR 1960-2020** | Caída máx. 1960-2020 | Sharpe 1960-2020 |
|---|---|---|---|---|---|---|
| **B** · S&P 500 1x comprar y mantener | 8,24 % | 7,96 % | 13,77 % | **9,18 %** | −55,5 % | 0,62 |
| **S** · 2x + filtro MA200 (H12) | 13,77 % | 10,45 % | 11,33 % | **12,35 %** | −50,1 % | 0,67 |

Caída máxima por periodo, S frente a B: −33,1 % frente a −46,4 % (1960-89); −50,1 % frente a −55,5 % (1990-2009); **−36,0 % frente a −33,8 % (2010-20)**.

| Criterio | Resultado |
|---|---|
| L1. CAGR de S > CAGR de B en los tres periodos | **No** (en 2010-2020: 11,33 % < 13,77 %) |
| L2. IC 99,58 % de la diferencia mensual media con límite inferior > 0 | **No**: media +0,33 %/mes, IC [−0,14 % ; +0,77 %] |
| L3. Sharpe de S ≥ Sharpe de B (1960-2020) | Sí (0,67 frente a 0,62) |
| L4. Caída máxima de S no peor que la de B (1960-2020) | Sí (−50,1 % frente a −55,5 %) |

## Veredicto registrado
**H12 no supera al S&P 500 según los criterios registrados** (falla L1 y L2). Tampoco es "rinde más pero con más riesgo": la caída máxima de todo el periodo no es peor que la de comprar y mantener. No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Lectura (sin cambiar el veredicto)
- En dos de los tres periodos el 2x filtrado rinde claramente más (+5,5 pp y +2,5 pp al año) y en el conjunto de 60 años +3,2 pp con una caída máxima algo menor. Pero en el periodo más reciente (2010-2020), de mercado alcista casi continuo, **rinde menos** (−2,4 pp) y con más caída.
- La diferencia mensual media (+0,33 %) **no es estadísticamente distinguible de cero** con la corrección por pruebas múltiples exigida.
- **Sensibilidades (no deciden):** el filtro de tendencia a 1x (sin apalancar) rinde lo mismo que comprar y mantener a 60 años (8,98 % frente a 9,18 %) con una caída máxima de −23,9 % en vez de −55,5 % y Sharpe 0,88 frente a 0,62; en 2010-2020 rinde menos (6,6 % frente a 13,8 %).
  El 3x filtrado (15,3 % anual) tiene una caída de −68,4 %; el 2x sin filtro, −87 %.
- El filtro de tendencia reduce mucho el riesgo, pero el rendimiento extra del apalancamiento lo da el apalancamiento, con más riesgo de cola, y no es robusto en todos los periodos.

## Limitaciones
Fondos 2x reales solo desde 2006, antes es simulación; dividendo, comisión y financiación aproximados y constantes; sin impuestos ni deslizamiento real; el riesgo de gaps y de días extremos puede estar subestimado; doce hipótesis probadas en esta fase.
