# Karryman V24 · fuentes de datos con empresas deslistadas

Todo lo de este documento procede de mediciones guardadas en `results/v24/` (sondeos `v24_fuentes_*.json`) o está marcado
como *no verificado*. Es investigación; ninguna fuente se da por validada.

## 1. Fuente evaluada: `Johnbrick123/sp500-data`
**Qué es (según su README, no verificado por nosotros):** historia point-in-time del S&P 500 desde 1970 con precio de cada
miembro cada día, incluidas empresas que desaparecieron (1.895 valores, 1.742 alguna vez miembros), más ETF.
Dos niveles: 1996-hoy (cierres y dividendos contrastados con CRSP y otra fuente) y 1970-1995 (CRSP, sin O/H/L/volumen).

**Medido en la release `snapshot-2026-11`** (`results/v24/v24_fuentes_42665259583.json`):
- `prices.parquet` (236 MB): 12.294.730 filas; columnas `date, ticker, open, high, low, close, volume, adj_close, dividends, stock_splits, source`;
  1968-01-02 → 2026-10-30; 1.895 tickers. Fuentes de las filas desde 2009: Yahoo (~84 %), Tiingo (~12 %), Wikipedia, CRSP,
  Kaggle y parches (`por_fuente` en cada resultado).
- `membership_intervals.parquet`: 1.801 intervalos (`ticker, start, end`; `end` vacío = sigue en el índice), 1.742 tickers.
- `members.parquet`: 1.523.200 filas, ~3.000 fechas en 56 años. **Son instantáneas dispersas, no una serie diaria**:
  usarlas como máscara diaria invalidó dos ejecuciones (ver `results/v24/README.md`). La pertenencia diaria debe construirse con los intervalos.
- `verification_report.txt` (informe propio del autor, 3-nov-2026): splits y dividendos conocidos, conciliación con Yahoo y
  comparación con la API histórica de Nasdaq en PASS. **No lo hemos replicado.**

**Comprobación nuestra (control de cordura):** con la pertenencia desde intervalos hay de media 502,8 miembros con precio por
día (mín. 499, máx. 509) entre 2009 y 2026, y la cartera igualponderada de los miembros da 13,1 % anual con caída máxima −40,0 %
(2010-2026), coherente con un mercado real. Es una comprobación de plausibilidad, no una auditoría de precios.

**Riesgos / limitaciones**
1. **Sin licencia.** El repositorio no tiene fichero de licencia (la API devuelve `license: null`); por defecto no hay permiso explícito
   de uso o redistribución. Solo uso interno de investigación hasta aclararlo con el autor.
2. **Procedencia contradictoria.** El README habla de CRSP (datos de pago) para 1970-1995 y para contraste; `SETUP.md` dice
   "derivado de Yahoo, nada propietario". Hay que aclarar si los datos CRSP pueden usarse.
3. **84 series con saltos diarios >40 %** en 2010-2026 (`calidad_datos`): muchos son movimientos reales (CVNA, CHK, quiebras),
   pero no se ha revisado cada caso para descartar splits o errores no ajustados.
4. **Salidas no ejecutables.** El autor lista `exit_gaps.csv` (SVB, Signature 2023…): el último precio no era operable. El motor
   liquida una posición que deja de cotizar al último cierre conocido, lo que es optimista en esos casos.
5. **Dependencia de un tercero.** Los datos son *release assets* que se actualizan cada noche; para reproducibilidad cada
   resultado guarda `tag` y SHA-256 de los ficheros usados (`datos` en el JSON).
6. Solo cubre el **S&P 500**: no es el universo completo de acciones de EE. UU.

## 2. Otras fuentes consideradas (sin probar en esta rama)
- **Yahoo Finance (yfinance):** gratuito, pero en general no conserva empresas deslistadas; no resuelve el sesgo de supervivencia.
  (El sondeo previsto de cobertura de salidas del S&P 500 desde Wikipedia no pudo ejecutarse: la tabla de cambios no se localizó en el HTML actual.)
- **Tiingo, Alpha Vantage (listados incl. deslistadas), Polygon, EOD, Norgate, CRSP/Compustat, Sharadar:** requieren clave y/o pago;
  no se han probado, no se afirma su cobertura.
- **IBKR:** permite históricos de contratos vigentes; no se espera que proporcione series de valores deslistados.
  No usado en esta rama (sin conexión desde el entorno de trabajo).

## 3. Decisión de trabajo
Usar `sp500data` como **universo de investigación** (S&P 500 point-in-time) mientras se aclara la licencia, registrando `tag` y
SHA-256 en cada resultado. Para decidir con dinero real haría falta un contraste independiente de precios (p. ej. IBKR o un proveedor
de pago) de una muestra de valores y fechas.
