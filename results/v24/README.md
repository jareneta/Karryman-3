# Resultados V24

| Fichero | Estado |
|---|---|
| `invalidos/v24_results_42665952060.json`, `invalidos/v24_results_42666315372.json` | **INVÁLIDOS. No usar.** Se construyó la pertenencia al S&P 500 con `members.parquet`, que contiene instantáneas dispersas (~3.000 fechas en 56 años), no una serie diaria. La máscara quedaba vacía casi todos los días, el motor vendía las posiciones y los resultados (p. ej. V24 ≈ 0,4 % anual, cartera igualponderada ≈ 3,4 % con caída máxima de −14 %) no representan nada. Lo detectó el control igualponderado. |
| `v24_fuentes_*.json` | Sondeos de fuentes de datos (estructura de la release del repositorio candidato). Válidos como descripción de ficheros, no como validación de su contenido. |
| `v24_results_*.json` posteriores a la corrección | Ver el `commit` y `datos` de cada fichero. Siguen siendo investigación. |

Corrección: la pertenencia diaria se reconstruye desde `membership_intervals.parquet` (intervalos `[start, end]`) y el cargador
rechaza universos con menos de 400 miembros con precio por día (control de cordura).
