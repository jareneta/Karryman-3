# Veredicto · H9b en la burbuja punto com y en correcciones recientes (exploratorio)

Run 44831428773; `results/v24/v24_dip_burbujas_44831428773.json`; registro `docs/V24_H9B_BURBUJAS.md`. Operaciones independientes de H9b, sin corrección por multiplicidad; datos hasta 2026-10-30.

| Ventana | N | Esperanza R | Placebo R | Dif. (IC 95 %) | Lectura |
|---|---|---|---|---|---|
| D0 burbuja alcista 1998-10 a 2000-03 | 586 | +0,123 | −0,001 | +0,119 (+0,035 a +0,204) | ventaja |
| D1 caída 2000-03 a 2002-10 | 1.247 | +0,069 | −0,030 | +0,099 (+0,013 a +0,168) | ventaja |
| D2 recuperación 2002-10 a 2004 | 464 | +0,153 | +0,027 | +0,127 (+0,036 a +0,204) | ventaja |
| C2018 | 114 | −0,157 | −0,089 | −0,068 (−0,155 a +0,010) | indicativo, sin ventaja |
| C2020 | 104 | −0,768 | −0,673 | −0,076 (−0,128 a −0,012) | indicativo, peor que el azar |
| C2022 | 345 | −0,005 | +0,002 | −0,008 (−0,153 a +0,152) | sin ventaja |
| C2026 (hasta 30 oct) | 56 | −0,251 | +0,012 | n/c | no concluyente |

- **Por estado del mercado:** 1998-2004, ventaja solo con el S&P 500 entre −10 y −20 % (+0,134 R); 2015-2026, solo entre −5 y −10 % (+0,110 R). Con caídas del índice > 20 % no hay ventaja (1998-2004: +0,011; 2015-2026 N = 90, no concluyente).
- **Tecnológicas (sesgado):** 1998-2004 ventaja en ambos grupos (tecnológicas +0,139 R, resto +0,078 R); 2015-2026 ninguna (+0,043 y +0,050 R, IC incluye 0). El campo `cobertura_clasificadas_pct` = 100 % es un error de cálculo (cuenta claves del mapa, no clasificaciones reales); la cobertura real conocida es 35,6 % en deslistadas.

## Lectura
Comprar caídas funcionó mejor que el azar durante toda la burbuja y su desplome (1998-2004), incluso dentro de la caída de 2000-2002 (+0,07 R, 67,7 % ganadoras), pero con ventaja pequeña por operación. En las correcciones recientes no hay ventaja, y en la del Covid-2020 fue peor que el azar; el mercado de 2015-2026 no replica el patrón de 1998-2004. En caídas profundas del índice (> 20 %) no se puede afirmar nada. Evidencia exploratoria, sin multiplicidad corregida; no cambia la conclusión de H9b ni equivale a una estrategia que supere al S&P 500.
