# Evidencia

Capturas y notas de ejecución que respaldan el estado documentado.

## `screenshots/hud-missing-shibuya-2026-11-15.png`

Login completo y mundo de Shibuya en ejecución contra el servidor local: cámara,
personaje, NPCs con diálogo y movimiento funcional. Se ven los atajos `[M] Map` y
`[J] Missions` en la esquina inferior izquierda, pero **no se instancian los paneles**
(minimapa, menú inferior derecho, SNS ni barra de combate): al pulsar las teclas no
ocurre nada. Ese es el bloqueo 1 documentado en `docs/01-status/KNOWN_BLOCKERS.md`.

Datos visibles del overlay: FPS/AVR/RES arriba a la izquierda y `ID:100001` abajo a la
derecha (probablemente identificador de depuración del cliente; sin confirmar).

La captura es material del juego, propiedad de sus autores; se incluye únicamente como
evidencia técnica del estado del proyecto, sin fines comerciales.

## Registros

Los `Player.log` completos no se versionan: contienen rutas locales, IDs de sesión y
pueden contener datos de cuenta. El arnés `tools/run_test.py` archiva el fragmento de log
generado por cada prueba en `runs/<timestamp>/`, excluido por `.gitignore`.
