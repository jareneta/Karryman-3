# Resultados de todos los backtests en 2015 → actualidad (protocolo `docs/V24_REGIMEN_2015.md`, sin modificarlo)

Datos: S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`), precios hasta 2026-10-30; índices desde `^GSPC`/`^IRX`. Periodo único **N = 2015-01-01 a 2026-10-31**, tramos **S1 2015-2020** y **S2 2021-2026**.
**Se abrió 2021-2026 para todas las hipótesis a la vez por decisión del usuario**; ya no queda tramo histórico sin mirar. Reglas, parámetros y costes: los originales de cada hipótesis. Bonferroni k = 14. Ficheros en `results/v24/` (campo `regimen: "2015"`).
(Nota técnica: en los JSON de H1-H5 las claves `train`, `valid` y `todo_2010_2020` son etiquetas heredadas; en este régimen significan S1, S2 y N.)

## 1. Veredictos
| Hipótesis | Resultado en N (2015-2026) | S1 / S2 | Veredicto |
|---|---|---|---|
| **H9b** comprar caídas (S&P 500) | esperanza +0,057 R (IC 95 %: +0,036 a +0,079) frente a +0,009 R del azar; diferencia +0,049 R, IC 99,44 % [+0,018 ; +0,080]; 3.758 operaciones | +0,022 R / **+0,074 R** | **Candidata** (cumple N, Q1, Q2 y Q3). No supera al índice como cartera: 5,6 % frente a 13,5 % |
| **H11** SPY + complemento de caídas | 13,94 % frente a 13,50 % de SPY (+0,44 pp); exceso mensual +0,07 %, IC [−0,48 % ; +0,61 %] | 14,63 % frente a 12,69 % / 13,54 % frente a 14,63 % | **No supera** (E1 y E3 fallan: Sharpe 0,73 < 0,81). Con coste 0,20 % por lado: −1,9 pp |
| **H12** S&P 500 2x + filtro MA200 | 13,81 % frente a 13,91 % de comprar y mantener; caída −36,0 % frente a −33,8 % | 8,37 % frente a 12,78 % / 20,36 % frente a 15,39 % | No supera |
| **H14** no pelees contra la Fed | 13,49 % frente a 13,91 %; Sharpe 0,88 frente a 0,83; caída igual (−33,8 %) | 10,55 % frente a 12,78 % / 16,92 % frente a 15,39 % (caída −18,7 % frente a −24,3 %) | No supera; "reduce riesgo" de forma marginal |
| **H13** arbitraje estadístico larga-corta | −25,5 % anual neto (media mensual IC 99,62 %: [−3,6 % ; −0,6 %]) | −20,9 % / −29,9 % | Sin esperanza positiva (ya la señal supera a los placebos, pero los costes la hunden) |
| **H1** momentum 12-1 | 12,39 % frente a 9,84 % de carteras al azar; diferencia mensual +0,36 %, IC [−1,1 % ; +1,7 %] | 6,37 % / 19,18 % | No candidata (2015-2020 por debajo del azar) |
| **H2** baja volatilidad | 9,83 % (azar 9,84 %) | 11,90 % / 7,87 % | No candidata |
| **H3** momentum con filtro de mercado | 6,38 % | 3,42 % / 9,70 % | No candidata |
| **H4** igualponderada con filtro | 6,57 % frente a 11,27 % sin filtro | 4,51 % / 9,05 % | No candidata |
| **H5** sistema de `plan.html` | +0,525 R frente a +0,454 R al azar; diferencia +0,07 R, IC [−0,07 ; +0,21]; cartera 2,87 % (azar 4,21 %) | +0,52 R / +0,53 R | No candidata |
| **H6** momentum 63 sesiones | 10,30 % (azar 9,62 %) | 5,86 % / 15,02 % | No candidata |
| **H7** tipo Minervini | +0,393 R frente a +0,214 R; diferencia +0,18 R, IC 99,29 % [−0,07 ; +0,44]; 525 operaciones; cartera 4,76 % | **+0,62 R** (azar +0,27) / **+0,14 R** (azar +0,15) | No candidata; la ventaja de 2015-2020 **desaparece en 2021-2026** |
| **H8** tipo Kell | +0,074 R frente a +0,167 R; diferencia **−0,093 R**, IC 99,4 % [−0,165 ; −0,022] | +0,13 R / +0,01 R | Peor que el azar (significativo) |
| **H10** tipo O'Neil | +0,414 R frente a +0,397 R; 271 operaciones (< 300) | +0,51 R / +0,28 R | Inconclusiva, sin ventaja |
| **V24 y variantes** (100.000 $, fraccionarias) | CAGR en N: base 4,6 %; freno fijo 5,3 %; progresiva 4,8 %; con banda 4,9 %; con MA100 3,6 %; ranking mensual 4,6 % frente a 13,5 % de SPY y 11,4 % de la igualponderada | | Muy por debajo del índice |

## 2. ¿Cambió el régimen en 2015? (descriptivo; no se afirma causalidad)
Comparación de la **ventaja frente al azar** o frente a SPY entre épocas, con las mismas reglas:
| Sistema | 1997-2009 | 2010-2020 | 2015-2026 | 2021-2026 (solo) |
|---|---|---|---|---|
| H9b, diferencia por operación frente al azar | +0,085 R | +0,050 R | +0,049 R | +0,066 R |
| H7, diferencia por operación | +0,29 R | +0,22 R | +0,18 R | −0,005 R |
| H5, diferencia por operación | | +0,10 R | +0,07 R | |
| H8, diferencia por operación | −0,10 R | −0,14 R | −0,093 R | |
| H11, exceso de CAGR sobre SPY | +1,61 pp | −0,55 pp | +0,44 pp | −1,09 pp |
| H13, CAGR neto | −4,7 % | −25,8 % | −25,5 % | −29,9 % |

- **No se observa un cambio de régimen claro** que haga funcionar estos sistemas. La única ventaja demostrada (H9b) tiene un tamaño parecido en todas las épocas, y la de H7 se debilita con el tiempo, no mejora. Lo que perdía antes sigue perdiendo.
- En 2021-2026 la rentabilidad bruta de muchos sistemas sube (por ejemplo, momentum de 12 meses, 19,2 %), pero también sube la de las carteras al azar y la de SPY (14,6 %), de modo que la ventaja relativa no cambia.
- La muestra de 2015-2026 es corta, y la afirmación contraria (que la tecnología haya cambiado todo) tampoco se puede descartar con estos datos: significa que, **con las reglas probadas**, no hay evidencia a favor.

## 3. Conclusión
En 2015-2026 **ninguna hipótesis supera al S&P 500 de forma demostrable**. La única candidata (H9b, comprar caídas) tiene esperanza positiva frente al azar en 1997-2009, 2010-2020 y 2015-2026 (incluido 2021-2026, sin ver antes), pero como cartera rinde poco y su ventaja por operación es pequeña.
H11 (SPY más caídas) es lo que más se acerca (+0,44 pp), sin significación y negativo con costes del 0,20 % por lado. Con 2021-2026 abierto ya no hay datos históricos de reserva: cualquier hipótesis nueva solo podrá validarse con datos futuros.
