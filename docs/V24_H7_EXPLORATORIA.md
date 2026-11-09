# H7 exploratoria en acciones que cotizan hoy (fuera del S&P 500) · registro previo

Fecha de registro: 2026-11-09, **antes de ejecutar**. **Prueba EXPLORATORIA con sesgo de supervivencia declarado.** No cuenta para la candidatura de H7 ni se presenta como evidencia de ventaja.

## 1. Qué se prueba
- **Reglas H7 sin ningún cambio** (`docs/V24_H7_MINERVINI.md`, configuración `CFG` de `v24_h7.py`): Trend Template, base ≥ 5 semanas con contracción, rotura con volumen ≥ 1,4×, stop del 8 % o mínimo de 10 sesiones,
  +3R vende 1/3 y breakeven, resto con cierre diario bajo MA50; cartera con 1 % de riesgo por operación, 6 % de riesgo total, 20 % de peso máximo; coste 0,10 % por lado.
- **Universo:** acciones de EE. UU. que cotizan **hoy** (listados de NASDAQ Trader, sin ETF ni emisiones de prueba, símbolos de 1-5 letras sin sufijos de warrants/unidades/derechos), **muestra aleatoria de 2.500** (semilla 42), precios de Yahoo ajustados.
  Incluye small, mid y large caps, pero **no incluye empresas deslistadas**.
- **Periodo:** 2010-01-01 a 2020-12-31 (entrenamiento 2010-16, validación 2017-20). Datos posteriores a 2020-12-31 **no se cargan**. No se prueba 1997-2009 (en supervivientes sería una muestra mínima y muy sesgada).
- **Controles:** placebo de entradas aleatorias en fechas aleatorias (mismo stop y salidas), 10 semillas, en el mismo universo; SPY.
- RS rank entre los valores líquidos de la muestra.

## 2. Reglas de lectura (fijadas antes)
- **Diagnóstico de sesgo:** se comparan la esperanza de las entradas aleatorias aquí con la del universo sin sesgo (S&P 500 point-in-time: 0,38 R en 2010-2020). Si es mucho mayor, indica inflación por supervivencia.
- **Señal favorable** (solo para decidir si merece la pena conseguir datos con deslistadas, no como validación): diferencia de esperanza H7 − placebo con IC 95 % inferior > 0 en el total y media > 0 en entrenamiento y validación.
- **Señal desfavorable:** diferencia ≤ 0 o IC incluye 0 en el total. En ese caso se archiva la línea.
- Aunque sea favorable, **no** se concluye que H7 funcione: requiere confirmación con datos sin sesgo de supervivencia y registrada antes.

## 3. Qué NO se hará
Cambiar parámetros de H7, ampliar o reducir la muestra tras ver resultados, probar otros periodos, mirar 2021-2026.
