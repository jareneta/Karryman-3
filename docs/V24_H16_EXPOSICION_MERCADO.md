# H16 · Regla de exposición al mercado (estar fuera o más/menos invertido) · registro previo

Fecha de registro: 2026-11-20, **antes de ejecutar H16**. Las secciones 1-7 no se editan; los cambios van como enmienda fechada al final.

## 0. Origen y aviso
El usuario pidió una regla para "estar fuera o más o menos invertido" inspirada en el análisis de mercado de Albert Albareda (Bolsa General). **No se conocen sus reglas exactas ni se pueden ver sus vídeos; esta prueba NO replica su método.** Se prueban indicadores genéricos, objetivos y medibles con datos históricos. Si el usuario aporta sus indicadores concretos, se registrarían como hipótesis nueva (H17).

## 1. Qué se mide
Una cartera que invierte en **SPY** una fracción variable (0 %, 50 % o 100 %) y deja el resto en **efectivo al 0 %** (supuesto conservador: penaliza a la regla). Referencia: SPY comprado y mantenido.

## 2. Indicadores (cierre de cada día t; parámetros fijados aquí, sin optimizar)
1. **Tendencia lenta:** cierre de SPY > media simple de 200 sesiones.
2. **Tendencia rápida:** cierre de SPY > media simple de 50 sesiones.
3. **Amplitud 200:** ≥ 50 % de los miembros del S&P 500 ese día (point-in-time, con deslistadas) cierran sobre su media de 200 sesiones.
4. **Amplitud 50:** ≥ 50 % de los miembros cierran sobre su media de 50 sesiones.
5. **Caída desde máximos:** SPY está a menos del 10 % de su máximo de cierre de 252 sesiones.
6. **Volatilidad:** desviación típica de rentabilidades diarias de SPY de 20 sesiones, anualizada, < 25 %.

Puntuación = número de indicadores cumplidos (0-6). **Exposición primaria:** puntuación ≥ 5 → 100 %; 3-4 → 50 %; ≤ 2 → 0 %. Indicadores con datos insuficientes cuentan como no cumplidos.

## 3. Ejecución sin mirar al futuro y costes
La señal se calcula con el cierre de t y se aplica a la rentabilidad de **t+1 a t+2** (se opera al cierre siguiente, un día de retraso). Coste 0,10 % del importe negociado por cada cambio de exposición. Sin impuestos. SPY ajustado por dividendos.

## 4. Datos y periodos
`sp500data` `snapshot-2026-11` (mismos datos que H1-H15). Régimen **2015** (primario por decisión del usuario): 2015-01-01 a 2026-10-31, tramos S1 2015-2020 y S2 2021-2026. Régimen **legacy** (contexto): A 2010-2020 (2010-16, 2017-20) y B 1997-2009 (1997-02, 2003-09), con 2021-2026 bloqueado.

## 5. Controles
- **SPY comprado y mantenido.**
- **Mezcla constante:** SPY con la misma exposición media que la regla en cada ventana (el resto en efectivo). Aísla si el *momento* de entrar y salir aporta algo, o si solo se reduce riesgo por tener menos exposición.
- **Placebo por desplazamiento circular:** la serie de exposición de la regla se desplaza un número aleatorio de sesiones (≥ 63) en 2.000 ocasiones, conservando su distribución y persistencia pero rompiendo su relación con el mercado. P-valor = fracción de placebos con Sharpe ≥ el de la regla.

## 6. Criterios (fijados antes; dieciséis hipótesis probadas en esta fase, Bonferroni k = 16: nivel IC 99,69 %, p < 0,003125)
- **R1 (supera al S&P 500 en rentabilidad).** CAGR de la regla > CAGR de SPY en la ventana completa y en cada tramo, **y** el IC de la media de la diferencia de rentabilidades mensuales (regla − SPY) tiene límite inferior > 0.
- **R2 (reduce el riesgo).** Caída máxima de la regla menos profunda que la de SPY en la ventana completa y en cada tramo, **y** Sharpe de la regla ≥ Sharpe de SPY en la ventana completa.
- **R3 (el momento aporta).** Sharpe de la regla > Sharpe de la mezcla constante en la ventana completa y en cada tramo, **y** p-valor del placebo < 0,05/16.
- **Regla "útil como control de riesgo"** si cumple R2 y R3. **"Supera al S&P 500"** solo si además cumple R1. En ambos casos debe cumplirse en cada periodo evaluado (en régimen 2015, el periodo único; en legacy, A y B).
- Si no cumple: "no hay evidencia"; sin variantes.

## 7. Sensibilidades (se informan, **no deciden**)
Cada indicador por separado (100 % si se cumple, 0 % si no); versión de dos estados (puntuación ≥ 3 → 100 %, si no 0 %); coste 0,20 %; efectivo remunerado al 2 % anual. Si la regla pasa con los parámetros primarios pero falla en alguna sensibilidad, se advierte expresamente.

## 8. Limitaciones declaradas
No es el método de Albareda; los umbrales (50 %, 10 %, 25 %, 5/3) son convencionales pero arbitrarios y no se optimizaron; una sola serie histórica de mercado (pocas caídas grandes independientes: 2018, 2020, 2022); efectivo al 0 %; sin impuestos ni deslizamiento real; amplitud calculada solo sobre el S&P 500 con datos de un tercero sin licencia clara; las reglas de timing suelen reducir caídas a costa de rentabilidad.

## 9. Qué NO se hará
Cambiar umbrales o mapeo tras ver resultados; elegir la sensibilidad "mejor" como primaria; elegir periodos a posteriori; abrir 2021-2026 en régimen legacy sin confirmación.
