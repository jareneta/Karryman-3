# Resultado: ¿qué tipo de caída comprar? (criterios de `docs/V24_TIPOS_DE_CAIDA.md`, sin modificarlos)

Fichero: `results/v24/v24_dip_tipos_44050086713.json` · commit `0c66da8` · operaciones de H9b en tres épocas: **A 2010-2020** (2.650), **B 1997-2009** (4.256), **C 2021-2026** (2.551). Esperanza total: +0,060 R, +0,084 R y +0,073 R (≈ +0,7 % a +1,0 % por operación con R = 12 %).

## Resultado
| | |
|---|---|
| Contrastes (grupos de un solo factor) | 21 (falsos positivos esperados al 5 %: ≈ 1,05) |
| Significativos en A sin corregir (p < 0,05) | 5 |
| Significativos en A tras Benjamini-Hochberg al 5 % | 4 |
| Que además replican en B y en C, con efecto mínimo y n ≥ 150 en las tres épocas | **0** |

**Veredicto registrado: no se distingue ningún tipo de caída mejor o peor que otro con esta evidencia.** No se registra ninguna hipótesis derivada.

## Lo que sí se ve (descriptivo, no validado)
Diferencia en R frente al resto de operaciones de esa característica (época A / B / C; p entre paréntesis):
| Grupo | A 2010-2020 | B 1997-2009 | C 2021-2026 |
|---|---|---|---|
| Máximo de 60 sesiones **hace 11-30 sesiones** | **+0,127** (p < 0,001; n = 1.124) | +0,064 (p = 0,003) | +0,037 (p = 0,17) |
| Máximo de 60 sesiones **hace más de 30 sesiones** (caída lenta) | **−0,079** (p = 0,001; n = 1.241) | −0,101 (p < 0,001) | −0,033 (p = 0,20) |
| Máximo hace ≤ 10 sesiones (caída muy reciente) | −0,119 (p = 0,017) | +0,069 (p = 0,07) | −0,006 |
| Entre 10 % y 30 % sobre la SMA200 | +0,159 (p < 0,001) | +0,038 | −0,043 |
| Menos de 10 % sobre la SMA200 | −0,136 (p < 0,001) | −0,042 | −0,041 |
| Caída rápida (≤ −10 % en 5 sesiones) | −0,006 | +0,092 (p = 0,004) | +0,037 |
| SPY sobre su SMA200 | −0,032 | +0,043 | −0,074 (p = 0,037) |
| ≥ 40 % bajo el máximo de 252 sesiones | +0,151 (n = 30) | +0,094 (n = 317) | +0,370 (n = 39) |

- **Lo único con signo coherente en las tres épocas:** las caídas "del medio" (máximo de 60 sesiones hace 11-30 sesiones) rinden mejor y las lentas (máximo hace más de 30 sesiones) peor. La diferencia es significativa en A y B pero **no en C** (p = 0,17 y 0,20), por lo que no cumple el criterio de replicación.
  Es un **indicio**, no un hallazgo.
- **Estado del mercado:** no hay un patrón estable (las caídas con SPY bajo su SMA200 rinden más en C y menos en B).
- **Hueco bajista, volumen del día y profundidad:** sin diferencias estables.
- **Limitación de diseño:** casi todas las señales (2.599 de 2.650 en A) se disparan justo al cruzar el −15 %, de modo que los grupos de **profundidad** de 20-25 % y 25-35 % tienen muy pocas operaciones (48 y 3 en A) y el análisis no tiene potencia para esa característica.
  Los grupos ≥ 40 % bajo el máximo anual (n = 30 y 39 en A y C) tampoco alcanzan las 150 operaciones exigidas.

## Lectura práctica (con cautela)
- **Con los datos disponibles, no hay un tipo de caída "mejor" que se pueda recomendar con fundamento.** La esperanza de H9b es pequeña y similar en casi todos los subgrupos.
- Lo más consistente es evitar las caídas **lentas y largas** (el máximo de 60 sesiones queda lejos en el tiempo) y preferir las que llevan **11-30 sesiones** de recorrido; pero no está validado en 2021-2026.
- Cualquier filtro derivado de esto sería una hipótesis nueva que solo se podría confirmar con datos futuros o seguimiento en papel.

## Limitaciones
Solo S&P 500; las tres épocas ya se habían visto con H9b; costes hipotéticos; 21 contrastes de un solo factor (sin combinar filtros); potencia insuficiente para profundidad y para las caídas muy profundas.
