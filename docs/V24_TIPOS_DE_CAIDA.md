# ¿Qué tipo de caída comprar? Análisis de subgrupos de H9b · registro previo

Fecha de registro: 2026-11-17, **antes de ejecutar el análisis**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Objetivo y advertencia
H9b (comprar caídas del S&P 500) es la única hipótesis con esperanza positiva demostrada (1997-2009, 2010-2020 y 2015-2026). Aquí se mide **si algún tipo de caída dentro de H9b rinde claramente mejor o peor**.
Es un análisis **exploratorio** de subgrupos: dividir las operaciones en muchos grupos genera falsos positivos, así que se fija la lista de grupos, se corrige por pruebas múltiples y se exige replicación en épocas distintas.
Como **ya no queda ningún periodo histórico sin mirar**, un tipo de caída "ganador" no estará validado con datos nuevos: solo podrá confirmarse con datos futuros o seguimiento en papel.

## 1. Operaciones
Exactamente las de H9b (`docs/V24_H9B_CAIDAS_SP500.md`): cruce a una caída del 15-35 % desde el máximo de cierre de las 60 sesiones previas, cierre > SMA200, miembro del S&P 500, precio ≥ 5 $, volumen medio de 50 sesiones ≥ 500.000; entrada a la apertura siguiente;
stop 12 % bajo la entrada; salida al cerrar sobre la SMA20 o a las 20 sesiones; coste 0,10 % por lado. La métrica es la esperanza en R por operación (R = 12 % de la entrada).
Tres épocas: **A 2010-2020**, **B 1997-2009** (calentamiento desde 1996) y **C 2021-2026** (calentamiento desde 2019; datos hasta 2026-10-30).

## 2. Características y grupos (lista cerrada; todas calculadas con datos hasta el cierre de la sesión de la señal)
1. **Profundidad** de la caída desde el máximo de 60 sesiones: 15-20 %, 20-25 %, 25-35 %.
2. **Velocidad**: rápida si la rentabilidad de las últimas 5 sesiones es ≤ −10 %; gradual si no. (2 grupos)
3. **Antigüedad del máximo**: sesiones desde el máximo de cierre de las 60 previas: ≤ 10, 11-30, > 30.
4. **Volumen del día de la señal** / media de 50 sesiones: < 1, 1-1,5, ≥ 1,5.
5. **Mercado**: SPY por encima de su SMA200 / por debajo. (2 grupos)
6. **Distancia al máximo de 252 sesiones**: < 25 %, 25-40 %, ≥ 40 % por debajo.
7. **Hueco de apertura** del día de la señal: bajista (apertura ≥ 3 % por debajo del cierre previo) / resto. (2 grupos)
8. **Distancia sobre la SMA200**: < 10 %, 10-30 %, > 30 %.
Total: **23 grupos**. Cada grupo se compara con **el resto de las operaciones de esa característica** (contraste de un solo factor; no se combinan filtros).

## 3. Estadísticos y decisión (fijados antes)
- Para cada grupo y época: esperanza en R del grupo menos la del resto, *t* de Welch (p bilateral por aproximación normal).
- **Corrección Benjamini-Hochberg al 5 %** sobre los 23 contrastes **en la época A** (descubrimiento).
- **Un grupo es "tipo de caída mejor (o peor)"** si: (1) es significativo tras BH en A; (2) en B **y** en C el signo es el mismo y p < 0,05 sin corregir; (3) |diferencia| ≥ 0,02 R en las tres épocas; (4) tiene al menos 150 operaciones en cada época.
- Se informa también la esperanza absoluta del grupo (en R y en % por operación = R × 12 %) y el número esperado de falsos positivos (5 % de 23 ≈ 1,2).

## 4. Qué se hace con el resultado
Un "tipo mejor" no se convierte en estrategia ni se opera: sería una hipótesis nueva (un filtro de H9b) que requeriría registro y datos futuros o seguimiento en papel. Si no hay grupos que cumplan, la conclusión es "no se distingue ningún tipo de caída mejor que otro con esta evidencia".

## 5. Qué NO se hará
Añadir características o grupos después de ver resultados, cambiar los cortes, combinar filtros para "afinar", elegir épocas a posteriori, presentar un grupo no replicado como una regla.

## 6. Limitaciones declaradas
Solo S&P 500 (grandes y líquidas); las tres épocas ya se han visto con H9b; coste y deslizamiento hipotéticos; muchos grupos con pocas operaciones tendrán intervalos amplios.
