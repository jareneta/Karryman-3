# Veredicto de la replicación de H2 en 1997-2009 (criterios de `docs/V24_REPLICA_H2.md`, sin modificarlos)

Fichero: `results/v24/v24_replica_h2_42701559467.json` · commit `56f8d1e` · datos de 1996-01-02 a 2009-12-31 (media de 500 miembros con precio por día, 913 series,
incluye deslistadas) · prueba final 2021-2026 **no cargada**. Mismos costes y cartera que en 2010-2020; ningún parámetro cambiado.

| | 1997-2002 | 2003-2009 | 1997-2009 | Caída máx. | Sharpe | Calmar |
|---|---|---|---|---|---|---|
| H2 baja volatilidad | 5,70 % | 4,38 % | 5,09 % | −34,6 % | 0,48 | 0,15 |
| SPY | 4,32 % | 4,94 % | 4,91 % | −55,2 % | 0,33 | 0,09 |
| Placebos aleatorios (10 semillas), mediana (rango) | 3,71 % (0,06-7,27) | 5,94 % (2,99-8,97) | 5,34 % (3,51-6,73) | | | |

| Criterio | Resultado |
|---|---|
| R1. CAGR de H2 > mediana de placebos en P1 **y** P2 | **No** (P1 sí: 5,70 > 3,71; P2 no: 4,38 < 5,94) |
| R2. IC 95 % de la diferencia mensual vs placebos con límite inferior > 0 | **No**: [−0,63 %; +0,50 %], media −0,07 % al mes |
| R3. Supera al índice (Sharpe ≥ SPY…) | Sí, pero solo frente a SPY |
| **Replica** | **No** |

## Veredicto registrado
**H2 no se replica en un periodo independiente.** Se descarta como idea con ventaja demostrable; no se prueban variantes ni se desbloquea la prueba final 2021-2026.

## Lectura
- La "victoria" de R3 frente a SPY no indica ventaja de H2: 1997-2009 fue un periodo muy malo para el índice (burbuja tecnológica y 2008) y una cartera aleatoria de 15 valores
  del mismo universo rinde igual o más (mediana 5,34 % frente a 5,09 %). Lo que el criterio de placebos pretendía separar es justo eso.
- En 2010-2020 H2 tampoco fue significativa; la combinación de ambos resultados no apoya una ventaja real de baja volatilidad con estas reglas y este universo.

## Conclusión del conjunto de pruebas (V24, H1-H4 y replicación de H2)
Con un motor auditado, un universo point-in-time con deslistadas y controles aleatorios, **no hemos encontrado ningún sistema con ventaja demostrable sobre el índice ni sobre la selección aleatoria**.
Limitaciones: solo S&P 500, 15 valores (alta varianza), datos de un tercero sin licencia clara ni auditoría independiente, costes hipotéticos, efectivo sin rendimiento.
Un resultado no significativo no demuestra que no exista ventaja; demuestra que con esta evidencia no se puede afirmar.
