# H15 · "comprar 15 acciones del screener y vender cuando dejen de aparecer" (réplica parcial) · registro previo

Fecha de registro: 2026-11-18, **antes de ejecutar H15**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Origen y alcance
El usuario aporta capturas de su screener de Stock Analysis (21 filtros; 15 resultados el 2026-11-18) y propone: **mantener 15 acciones del screener y vender cuando dejen de aparecer**.
**Esta prueba es una réplica PARCIAL**: solo se reproducen los filtros comprobables con datos de cada fecha, en el universo S&P 500 point-in-time. **No valida el screener completo** (que devuelve sobre todo empresas pequeñas fuera del S&P 500 y usa fundamentales).

## 1. Filtros del screener y qué se reproduce
Reproducidos (datos de precio, volumen y dividendos hasta el cierre de la sesión *t*; `sp500data`, `snapshot-2026-11`):
- Cambio de precio a 3 meses (63 sesiones) > +10 %; a 1 mes (21) > +1 %; a 6 meses (126) > 0 %; a 1 año (252) > +1 %.
- Cierre por encima de la media de 20, de 50 y de 200 sesiones.
- Cierre a menos del 15 % del máximo de 252 sesiones (`Price Change 52W High > −15 %`).
- Precio > 5 $; volumen medio de 50 sesiones > 500.000 (el screener usa el volumen del día; se usa la media de 50 para estabilidad: desviación declarada).
- **Rendimiento por dividendo cero:** ningún dividendo pagado en las últimas 252 sesiones.
- Miembro del S&P 500 ese día (sustituye a "País: EE. UU." y a "Capitalización > 300 M$", que el S&P 500 cumple de sobra).
**No reproducidos (no comprobables con datos de cada fecha):** crecimiento de ventas del trimestre, del trimestre anterior y del año (> 10 %), BPA > −1, filtro de sectores (lista truncada en la captura) y los filtros desactivados (1 semana, RSI, ATR).

## 2. Mecánica (fijada antes)
- Cada sesión *t* con datos hasta el cierre: se sale de las posiciones que **ya no cumplen** los filtros y se compra para llegar a **15 posiciones**; las órdenes se ejecutan a la **apertura de *t+1***.
- **Selección de nuevas compras:** al azar (con semilla) entre las que cumplen y no están en cartera; **10 semillas**. (No se usa ningún orden por rentabilidad: es "comprar 15 del screener" sin criterio adicional.)
- **Peso:** cada compra recibe 1/15 del patrimonio de la apertura (limitado por el efectivo); sin reequilibrio posterior; si menos de 15 cumplen, se mantienen menos y el resto queda en efectivo (sin rendimiento). Sin apalancamiento.
- Coste 0,10 % por lado. Posiciones de valores que dejan de cotizar: se liquidan al último cierre.

## 3. Controles
- **SPY comprado y mantenido** y **cartera igualponderada de todos los miembros** (referencias).
- **Solo tendencia:** misma mecánica y mismas 10 semillas, con un único filtro (cierre > media de 200 sesiones, miembro, precio > 5 $, volumen > 500.000). Mide si los demás filtros añaden algo a una simple tendencia.
- **Azar mensual:** 15 miembros líquidos al azar (precio > 5 $, volumen medio > 500.000), recompuestos por completo cada 21 sesiones, 10 semillas.

## 4. Datos, periodos y bloqueo
Siguiendo el protocolo `docs/V24_REGIMEN_2015.md`: periodo **N = 2015-01-01 a 2026-10-31** en dos tramos, **S1 2015-2020** y **S2 2021-2026** (historial anterior solo para calentar). No queda ningún periodo de reserva.

## 5. Criterios (fijados antes)
Quince hipótesis probadas en esta fase (Bonferroni k = 15: nivel 99,67 %).
- **R1 (supera al S&P 500).** En N: CAGR medio de las 10 semillas > CAGR de SPY **y** IC (99,67 %, remuestreo por meses) de la media de la diferencia mensual (media de las semillas − SPY) con límite inferior > 0, **y** Sharpe ≥ el de SPY.
- **R2 (aporta algo).** CAGR medio de las 10 semillas > CAGR medio de "solo tendencia" y de "azar mensual", en **cada tramo** (S1 y S2).
- **H15 "supera al S&P 500"** si cumple R1 y R2. Si cumple R2 pero no R1: "mejor que el azar y que la tendencia, pero no supera al índice".
- Si no cumple R2: la réplica parcial del screener no aporta nada sobre una simple tendencia.

## 6. Limitaciones declaradas y siguiente paso
S&P 500 (empresas grandes) en vez del universo del screener (sobre todo pequeñas); sin fundamentales ni sectores; selección aleatoria entre las que cumplen; cinco filtros de rentabilidad y medias muy correlacionados.
**La única forma de probar el screener completo** es seguirlo en tiempo real: guardar cada día su lista y calcular la estrategia hacia adelante (prueba "hacia delante"); no se hace aquí sin decisión del usuario.

## 7. Qué NO se hará
Cambiar los umbrales de los filtros, el número de posiciones (15) o la selección de nuevas compras tras ver resultados; añadir filtros; elegir periodos a posteriori.
