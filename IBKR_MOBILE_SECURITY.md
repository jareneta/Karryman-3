# IBKR móvil: límites de seguridad y puesta en marcha

Estado: **NO CONECTADO**. El panel estático de GitHub Pages no puede operar de forma segura directamente contra la sesión autenticada de Interactive Brokers.

## Disponible hoy sin servidor
- Importación privada de snapshot JSON desde el almacenamiento del móvil en `cartera.html`.
- Comparación de posiciones antes de reemplazar la cartera; los stops externos no se aceptan.
- Riesgo estimado por cierre y borradores paper guardados únicamente en el navegador.
- Sin transferencia de credenciales, números de cuenta, posiciones ni órdenes a GitHub.

## Requisitos obligatorios para conexión automática
1. Elegir y autorizar un servicio privado de ejecución accesible desde Android, separado del repositorio público.
2. Autenticar IBKR mediante el flujo oficial admitido por el servicio, sin guardar contraseñas en el navegador ni en GitHub Actions.
3. Almacenar tokens exclusivamente en el backend privado, cifrados y con renovación y revocación.
4. Endpoint de lectura de cartera, con autorización de usuario y control de acceso. Nunca exponer datos IBKR en archivos JSON públicos.
5. En Paper Trading, solicitar una cotización reciente y volver a calcular stop, efectivo, riesgo individual <=1% NLV y riesgo agregado <=5% NLV. Rechazar señales caducadas y duplicados.
6. Mostrar una previsualización exacta y exigir aprobación humana explícita **por cada orden**. El servidor debe aplicar idempotencia y verificar cuenta Paper.
7. Comprobar estado y confirmación del broker; registrar rechazos, ejecución parcial y cancelaciones. No convertir una respuesta de envío en una ejecución confirmada.
8. Probar el circuito con cuenta Paper, fallos de autenticación, desconexión, gaps, saldo insuficiente, límites, concurrencia y órdenes duplicadas.
9. Mantener la negociación real deshabilitada hasta una aprobación explícita y separada.

No implementar una supuesta conexión directa desde JavaScript público ni automatizar compras reales sin esos controles. La conexión de IBKR disponible dentro de ChatGPT **no es** una sesión reutilizable automáticamente por la web.

## Investigación cuantitativa
Los backtests del repositorio son investigación con datos históricos, sesgos de selección y supuestos de ejecución; no demuestran una ventaja matemática. No habilitar órdenes por resultados favorables sin prueba fuera de muestra y costes realistas.
