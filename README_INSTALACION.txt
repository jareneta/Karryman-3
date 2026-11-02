KARRYMAN 3.0 - MODULO DE ESCANEO AUTOMATICO

IMPORTANTE: No sustituir ni borrar el index.html que ya funciona.

Archivos que se deben añadir al repositorio Karryman-3:
- auto.html (pantalla de resultados)
- scanner.py (analisis tecnico)
- requirements.txt (dependencias)
- .github/workflows/scan.yml (programacion automatica)

El script creara data/signals.json cuando se ejecute por primera vez.

INSTALACION RECOMENDADA DESDE ANDROID:
1. Descomprime el ZIP en tu movil.
2. En GitHub abre el repositorio Karryman-3 y elige Add file > Upload files.
3. GitHub web puede aplanar las carpetas al subir desde Android. Comprueba especialmente que scan.yml termine en .github/workflows/scan.yml. Si no puedes preservar rutas, crea .github/workflows/scan.yml con Add file > Create new file, escribiendo la ruta completa como nombre, y pega el contenido del archivo.
4. Sube auto.html, scanner.py y requirements.txt en la raiz.
5. En Settings > Actions > General > Workflow permissions, selecciona Read and write permissions si GitHub no permite al bot guardar el JSON. Guarda.
6. En Actions > Karryman - escaneo diario > Run workflow, ejecuta manualmente la primera vez.
7. Espera a que el workflow termine en verde y abre https://jareneta.github.io/Karryman-3/auto.html

HORARIO: lunes a viernes a las 23:30 UTC (despues del cierre habitual de EEUU). GitHub puede retrasar ejecuciones programadas.

LIMITACIONES: Fuente gratuita Yahoo Finance via yfinance, sin SLA, posible bloqueo/rate-limit. No incluye fundamentales, eventos ni cartera real de IBKR. No envia ordenes. No guardes claves ni posiciones privadas en repositorio publico. No se garantiza rentabilidad.
