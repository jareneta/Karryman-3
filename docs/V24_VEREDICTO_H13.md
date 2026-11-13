# Veredicto H13 · arbitraje estadístico diario larga-corta (criterios de `docs/V24_H13_ARBITRAJE_ESTADISTICO.md`, sin modificarlos)

Fichero: `results/v24/v24_statarb_43509435656.json` · commit `3797726` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · prueba final 2021-2026 **no cargada**.
Señal: reversión de 5 sesiones; cartera diaria largo en el decil que más cae y corto en el que más sube, dólar-neutral, costes 0,10 % por lado más préstamo del 1 % anual. Rentabilidad por 1 de nominal largo.
Rotación media: 1,58 (A) y 1,65 (B) de nominal por sesión.

| | CAGR neto | Sharpe | Caída máx. | Media mensual neta (IC) |
|---|---|---|---|---|
| **A 2010-2020** · H13 (entren. −31,8 %, valid. −14,3 %) | **−25,8 %** | −1,39 | −98,9 % | **−2,33 %** (IC 99,62 %: −3,50 % a −0,71 %) |
| Placebo señal obsoleta 20 / 40 sesiones | −30,2 % / −31,4 % | −2,22 / −2,43 | | |
| SPY | 13,8 % | 0,84 | −33,7 % | |
| **B 1997-2009** · H13 (1997-02 +9,2 %, 2003-09 −15,4 %) | **−4,7 %** | −0,03 | −84,0 % | −0,15 % (IC 95 %: −1,31 % a +1,01 %) |
| Placebo señal obsoleta 20 / 40 sesiones | −37,5 % / −33,5 % | −1,72 / −1,47 | | |
| SPY | 5,0 % | 0,33 | −55,2 % | |

| Criterio | A | B |
|---|---|---|
| J1. Media mensual neta con IC inferior > 0 | **No** (significativamente **negativa**) | **No** (IC incluye 0) |
| J2. Sharpe mayor que ambos placebos en cada tramo | Sí | Sí |

## Veredicto registrado
**H13 no tiene esperanza matemática positiva neta de costes** (falla J1 en los dos periodos) y por supuesto no supera a SPY. No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Lectura
- **La señal sí contiene información bruta** (J2: mejor que las señales obsoletas en todos los tramos), pero **los costes la destruyen**: con rotación de ~1,6 de nominal al día y 0,10 % por lado, el coste solo supone una pérdida del orden de 40 % anual.
- **Sensibilidad a costes (no decide):** con 0,05 % por lado el resultado en 1997-2009 pasa a +17,4 % anual (Sharpe 0,70) y en 2010-2020 sigue siendo −9,5 %; con 0,20 % por lado, −37 % y −50 %. El resultado depende por completo de los costes de ejecución.
- **El efecto se debilita con el tiempo:** en 1997-2002 rinde +9,2 % neto y en 2010-2020 es claramente negativo, coherente con una reversión de corto plazo arbitrada por operadores más rápidos.
- **Horizonte (no decide):** a 1 sesión, −57 % y −39 % anual; a 21 sesiones, −13,6 % (2010-20) y +2,5 % (1997-2009).
- **Lado largo solo, neto (no decide, con beta de mercado):** −4,0 % (A) y +9,1 % (B) anual; no es una conclusión sobre superar a SPY.
- **Relevancia para el caso Simons:** esto es coherente con que la ventaja de ese tipo de estrategias dependa de costes de ejecución mínimos, rotación controlada e infraestructura, que no están al alcance de una cuenta personal. No dice nada sobre Renaissance, solo sobre esta versión diaria.

## Limitaciones
Precios ajustados de un tercero; coste de préstamo único y constante; ejecución a la apertura sin deslizamiento adicional; sin impuestos; S&P 500 de gran capitalización (reversión más débil que en valores pequeños); trece hipótesis probadas en esta fase.
