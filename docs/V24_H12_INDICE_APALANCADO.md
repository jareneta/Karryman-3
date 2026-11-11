# H12 · S&P 500 con apalancamiento 2x y filtro de tendencia (frente a comprar y mantener el índice) · registro previo

Fecha de registro: 2026-11-11, **antes de ejecutar H12**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Motivación y advertencia
Ninguna de las once hipótesis con acciones individuales superó al S&P 500 (`docs/V24_VEREDICTO_H11.md` y anteriores). La investigación previa (`index_leverage.py`) ya indicaba que el índice apalancado con filtro de tendencia era lo único que se acercaba a doblar al índice.
Esta prueba la evalúa con criterios fijados antes, tres periodos independientes y el riesgo incluido. **Apalancar aumenta el riesgo: una caída del índice se amplifica y un fondo apalancado puede perder la mayor parte de su valor.**
No es una recomendación; es una medición histórica. Se usan fondos tipo 2x diario (SSO, por ejemplo), es decir **ETF**, no acciones individuales.

## 1. Estrategias comparadas
Datos: S&P 500 (`^GSPC`, precio) desde 1950 y letras del Tesoro a 3 meses (`^IRX`), Yahoo Finance. Rentabilidad por dividendo aproximada del 2 %/año sumada a todas las estrategias invertidas; sin dividendos reales (limitación).
- **Referencia (B):** S&P 500 1x comprar y mantener.
- **H12 (S):** 2x diario (rentabilidad diaria ×2 menos coste de financiación al tipo de las letras sobre la parte prestada, menos comisión del fondo 0,9 %/año), **invertido solo si el cierre del índice está sobre su media de 200 sesiones**; si no, en letras del Tesoro. La señal se ejecuta al día siguiente. Coste de cambio de posición 0,10 % por cambio.
- Implementación: `index_leverage.simulate` (ya existente) sin modificar parámetros.

## 2. Periodos y bloqueo
Evaluación 1960-01-01 a 2020-12-31, en tres periodos independientes: **P1 1960-1989, P2 1990-2009, P3 2010-2020** (la historia previa a cada periodo solo calcula la media de 200 sesiones). **Prueba final 2021-2026 bloqueada** (los datos posteriores a 2020-12-31 no se cargan).

## 3. Criterios (fijados antes)
Doce hipótesis probadas en esta fase (Bonferroni k = 12: nivel 99,58 %).
- **L1.** CAGR de S > CAGR de B en **cada uno de los tres periodos**.
- **L2.** En todo 1960-2020, el IC (99,58 %, remuestreo por meses, 5.000) de la media de la diferencia de rentabilidades mensuales (S − B) tiene límite inferior > 0.
- **L3.** En todo 1960-2020: Sharpe de S ≥ Sharpe de B.
- **L4.** En todo 1960-2020: la caída máxima de S no es peor que la de B (se informa también por periodo).
- **H12 "supera al S&P 500"** si cumple L1, L2, L3 y L4. Si falla L4 pero cumple L1-L3, el veredicto será **"rinde más pero con más riesgo"** y no se presentará como superar al índice.
- La prueba final 2021-2026 solo se abriría una vez y con confirmación explícita del usuario.

## 4. Sensibilidades (se informan, no deciden)
2x sin filtro; 3x con filtro; 2x con filtro de media de 10 meses; 1x con filtro de 200 sesiones (aísla el efecto del filtro).

## 5. Limitaciones declaradas
Índice de precio con dividendo aproximado; comisión y financiación del fondo hipotéticas y constantes; sin impuestos ni deslizamiento real; los fondos 2x reales existen desde 2006, el resto es simulación; el riesgo de cola (días extremos) puede subestimarse en una simulación diaria.

## 6. Qué NO se hará
Cambiar la media de 200 sesiones, el apalancamiento o los costes tras ver resultados; elegir periodos a posteriori; presentar una variante de las sensibilidades como la estrategia; mirar 2021-2026 sin confirmación.
