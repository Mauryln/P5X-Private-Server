# Servidor local (PoC)

Servidor TCP en Python que habla el protocolo de P5X en `127.0.0.1`. Cubre handshake,
login, selección de personaje, entrada a escena, movimiento, NPCs/diálogos y consultas
básicas. El combate y la persistencia son esqueletos (ver `docs/01-status/`).

## Uso

```powershell
python poc_login_server.py --port 10403
```

Variables de entorno:

| Variable | Efecto |
|---|---|
| `P5X_FRAME_LOG` | ruta del JSON con el registro de tramas (por defecto `poc_frame_log.json` junto al script) |

El cliente debe apuntar `eulogin.p5xjpupd.com` a `127.0.0.1` vía `hosts` (revertir al
terminar). Ver el README principal para el procedimiento completo.

## Archivos

| Archivo | Rol |
|---|---|
| `poc_login_server.py` | servidor TCP, máquina de estados de login/escena/mundo |
| `proto2_codec.py` | framing, RC4 y codecs Protobuf2 de los mensajes soportados |

## Tests

```powershell
python tests\test_new_codecs.py
```

Los tests que requieren datos del cliente (descriptor `allMsgPb.bytes`) no se incluyen
por derechos de autor; se ejecutan contra una copia local del juego.

## Estado

Es un PoC de estudio, no un servidor de producción: sin autenticación real, sin
persistencia y sin validación de estado. No usar contra servicios en línea.
