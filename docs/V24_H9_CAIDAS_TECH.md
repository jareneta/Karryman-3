# H9 · comprar caídas de acciones tecnológicas (etapa 1: S&P 500) · registro previo

Fecha de registro: 2026-11-10, **antes de ejecutar nada de H9**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 1. Universo (etapa 1)
Miembros del S&P 500 en cada fecha (point-in-time, con deslistadas; `sp500data`, `snapshot-2026-11`) **clasificados como tecnológicos por su código SIC de la SEC**:
3570-3579 (ordenadores y equipos de oficina), 3660-3679 (equipos de telecomunicación, componentes electrónicos y semiconductores) y 7370-7379 (software, servicios y proceso de datos).
El sector se toma de la clasificación SEC actual de cada empresa (no cambia en el tiempo). La relación ticker-empresa se hace con los ficheros de la SEC; las empresas sin correspondencia **quedan sin clasificar y fuera de la prueba**.

**Regla de cobertura (fijada antes):** se mide qué porcentaje de las empresas del S&P 500 ya deslistadas (con fin de pertenencia anterior a 2026) se consigue clasificar por SIC.
Si es **< 70 %**, la prueba se declara **inconclusiva por sesgo de supervivencia en la clasificación** y no se interpreta como evidencia a favor ni en contra.

## 2. Reglas de la estrategia
- **Señal de caída:** en la sesión *i*, el cierre está entre un 15 % y un 35 % por debajo del **máximo de cierre de las 60 sesiones previas** (*i−60…i−1*) y era < 15 % por debajo el día anterior (evento de cruce, no entradas repetidas); además cierre > SMA200 (caída dentro de una tendencia alcista); precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000; el valor es miembro y tecnológico ese día.
- **Entrada:** apertura de *i+1*. Sin entrada si la apertura queda más de un 5 % por encima o por debajo del cierre de la señal.
- **Salidas:** stop por cierre un **12 % bajo el precio de entrada**; salida (ejecución en la apertura siguiente) cuando el cierre supera la **SMA20**, o tras **20 sesiones** si no se dio antes; sin parciales.
- **Cartera:** 1 % de riesgo por operación (R = 12 % de la entrada), 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado; sin apalancamiento.

## 3. Datos, periodos y bloqueo
**Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (incluye la burbuja tecnológica). **Prueba final 2021-2026 bloqueada** (no se carga).
Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible (optimista en quiebras).

## 4. Controles
SPY; **placebo de entrada aleatoria** entre las mismas tecnológicas líquidas y miembros (mismas salidas y mismo stop del 12 %), 10 semillas, para operaciones y carteras, en cada periodo.

## 5. Criterios (fijados antes)
Nueve hipótesis probadas en total en esta fase (Bonferroni k = 9: nivel 99,44 % en el periodo A; 95 % en el B).
- **N.** ≥ 300 operaciones por periodo; si no, "inconclusivo".
- **Q1.** Esperanza en R > 0 con IC 95 % inferior > 0 en el periodo completo, y media > 0 en cada tramo.
- **Q2.** Diferencia H9 − placebo con IC inferior > 0 (A al 99,44 %; B al 95 %).
- **Q3.** CAGR de la cartera > mediana de las 10 carteras placebo en cada tramo.
- **Candidata** si cumple N, Q1 y Q2 en **ambos** periodos y la cobertura de clasificación es ≥ 70 %. **Supera al índice** si además cumple Q3 y, en cada periodo, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: "no hay ventaja demostrable"; sin variantes (umbrales de caída, ventana de 60 sesiones, salidas).

## 6. Etapa 2 (Nasdaq fuera del S&P 500): NO incluida en este registro
Requiere universo con deslistadas fuera del S&P 500 (Tiingo de pago o muestra limitada) y clasificación sectorial de empresas que no están en los ficheros actuales de la SEC. Se registrará aparte, antes de probarla.
**Una prueba con acciones del Nasdaq que cotizan hoy no es válida para comprar caídas**: el sesgo de supervivencia es máximo (las que se hundieron y desaparecieron no están).

## 7. Qué NO se hará
Cambiar los umbrales (15 %/35 %, 60 sesiones, SMA200, 12 %, SMA20, 20 sesiones), añadir filtros, elegir periodos a posteriori, interpretar un resultado "inconclusivo" por cobertura, mirar 2021-2026.
