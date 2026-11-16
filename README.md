# P5X — Servidor local de preservación (estudio de ingeniería inversa)

> **Estado: EN PAUSA (noviembre 2026).** El trabajo se detiene aquí y se publica como base
> reproducible para quien quiera continuarlo. El objetivo es documentar lo reconstruido,
> lo que falta y cómo verificarlo — no distribuir el juego.

Proyecto **no oficial**, sin fines de lucro, de **preservación e investigación**. Reconstruye
desde cero un servidor local compatible con el cliente de PC de *Persona 5: The Phantom X*
(P5X), a partir del análisis del propio cliente: esquema de red, resoluciones de assets,
bytecode Lua y tablas de configuración.

**No es** un emulador completo del juego. Es un servidor de estudio con transporte, login,
escena y mundo funcionando, y una hoja de ruta con evidencia para el resto.

---

## 1. Aviso legal

- Este repositorio **no contiene** binarios, assets, datos, textos ni código del juego.
  Solo documentación y código original de interoperabilidad.
- No se distribuye `msg.proto`, catálogos, bundles, bytecode Lua ni tablas maestras.
  Esos materiales son propiedad de sus autores y se regeneran localmente a partir de una
  copia obtenida legalmente.
- Para usarlo necesitás **tu propia copia legítima** del cliente. El proyecto no incluye
  ni provee accesos, claves, cuentas ni servicios.
- No se elude autenticación de servicios de terceros, ni anti-cheat, ni se atacan servicios
  todavía operativos. Todo el trabajo es **offline y en local (127.0.0.1)**.
- Marcas, personajes y contenido pertenecen a SEGA / Atlus y sus licenciantes. Este trabajo
  no está afiliado ni respaldado por ellos.

---

## 2. Estado verificado

Verificado contra el cliente oficial de PC (Unity 2022.3.49f1) y registros de ejecución.
Cada fila indica si está **confirmado en runtime** o solo a nivel de protocolo.

| Área | Estado | Evidencia |
|---|---|---|
| Handshake de sesión (Trama 0, RC4 drop 1024) | ✅ Confirmado | cliente conecta y descifra |
| Encuadre de tramas (`len(4)+msg_id(2)+seq(2)+protobuf`) | ✅ Confirmado | 183 tramas registradas |
| `CSLogin` → `SCLoginResult` | ✅ Confirmado | flujo completo |
| `CSLoginGate` → `SCLoginGateResult` | ✅ Confirmado | flujo completo |
| `CSQueryCharacters` → `SCQueryCharactersResult` | ✅ Confirmado | selección de avatar |
| `CSCharacterLogin` → `SCCharacterLoginResult` | ✅ Confirmado | entrada al mundo |
| `SCServerTime` y corrección de `zoneTime` | ✅ Confirmado | fechas coherentes en cliente |
| Carga de escena Shibuya (`sn 2102`, `scn13_shibuya`) | ✅ Confirmado | escena 3D completa |
| Movimiento, físicas, colisiones (`CSSceneMove`, `CSSceneMoveStop`) | ✅ Confirmado | WASD/gamepad |
| NPCs ambientales y diálogos | ✅ Confirmado | interacción en mundo |
| Arranque 100% offline (sin CDN / verificador de paquetes) | ✅ Confirmado | `OuterPackageFileChecker Result: None` |
| **HUD / UI** (minimapa, menús, `[M]`, `[J]`) | ❌ **Bloqueado** | atajos visibles, paneles no se instancian (4 prefabs `_EN` nulos) |
| Combate PvE (turnos, daño, skills) | ⚠️ Solo esqueleto de codec | servidor no calcula batalla |
| Persistencia de progreso | ⚠️ En memoria | sin base de datos |
| Misiones / ConfData (tablas maestras) | ⚠️ Parcial / en investigación | sin descifrado completo |

### Evidencia visual

`evidence/screenshots/hud-missing-shibuya-2026-11-15.png`

Login completo y mundo de Shibuya jugable (cámara, personaje, NPCs con diálogo, movimiento).
Se ven los atajos `[M] Map` y `[J] Missions`, pero los paneles no se instancian: **no hay
minimapa, menú, SNS ni barra de combate**. Esa captura documenta exactamente el bloqueo:
el mundo funciona, la interfaz no. No hay captura de HUD funcional porque ese hito no se
alcanzó.

---

## 3. Cómo se llegó hasta acá (resumen técnico)

- **Transporte:** protocolo propio de Zeus; 8 bytes de cabecera, payload Protobuf2; cifrado
  RC4 inicializado en la primera trama, descartando 1024 bytes de keystream.
- **Tiempo:** `SCLoginResult` con `zoneTime` provoca un offset negativo que rompe `os.date`
  en el cliente; se omite el campo (`zoneTime = None`) y el problema desaparece.
- **Offline:** se neutralizó el verificador de paquetes (`OuterPackageFileChecker`) y se
  vaciaron las URLs remotas de hotfix/parcheo para que el cliente no re-descargue nada.
  Los ajustes locales exactos (tamaños en las tablas de integridad y flags de configuración)
  están listados en `docs/01-status/STATUS_AND_REMAINING_WORK.md`, sección 1.3. No se
  distribuyen: son cambios sobre *tu* copia y deben revertirse para jugar en línea.
- **HUD (bloqueo principal):** el catálogo de assets indexa los nombres canónicos con
  mayúsculas (`UI-…_EN.prefab`), pero el `m_Container` de los bundles empaquetados tiene las
  claves en minúsculas (`ui-…_en.prefab`). El lookup por nombre falla y devuelve `null`.
  Detalle completo en `docs/03-client/UI_LANGUAGE_DIAGNOSIS.md` y `UI_FIX_REPORT.md`.

---

## 4. Cómo reproducirlo

**Requisitos:** Windows x64, Python 3.10+, tu copia legal del cliente de PC y conocimientos
básicos de red local. Nada de esto requiere internet para funcionar.

1. **Servidor**
   ```powershell
   cd server
   python poc_login_server.py --port 10403
   ```
   Escucha en `127.0.0.1:10403`.

2. **Redirección local del host de login** (temporal, revertir al terminar)
   ```
   # C:\Windows\System32\drivers\etc\hosts
   127.0.0.1 eulogin.p5xjpupd.com
   ```

3. **Cliente**
   ```powershell
   <ruta-a-tu-copia>\P5X.exe
   ```

4. **Resultado esperado hoy:** login completo → selección de personaje → Shibuya con cámara,
   movimiento y NPCs. **Sin HUD** (bloqueo conocido).

> Usá una copia de trabajo del cliente. Este proyecto no modifica binarios ni tu instalación
> original, y no debe usarse contra servicios en línea.

---

## 5. Bloqueos conocidos y próximos pasos

| # | Bloqueo | Causa raíz | Próximo paso sugerido |
|---|---|---|---|
| 1 | HUD no se instancia | case mismatch catálogo ↔ `m_Container` | reempaquetar con `packer='original'` (flags `0x243`) renombrando claves, o normalizar en runtime |
| 2 | Combate ausente | el cliente solo reproduce animaciones; el servidor debe calcular todo | máquina de turnos + datos reales de ConfData |
| 3 | Sin persistencia | estado en memoria | SQLite: cuenta, personaje, inventario, posición |
| 4 | Tablas maestras | ConfData cifrado | descifrar y mapear monstruos, skills, misiones |
| 5 | Fidelidad no verificable | no existe el servidor original | declarar cada campo como derivado / aproximado / desconocido |

**Orden recomendado para retomar:** HUD → ConfData → vertical slice de combate → persistencia.

Reglas de método que este proyecto adoptó (y conviene mantener): toda afirmación en `docs/`
debe citar evidencia (VA, hash, línea de log o script reproducible); toda hipótesis se marca
como *confirmada*, *probable* o *desconocida*; no se repite un experimento fallido sin haber
explicado antes por qué falló.

---

## 6. Estructura del repositorio

```
docs/
  01-status/     estado, bloqueos y próximos pasos
  02-network/    protocolo, framing, cifrado, dependencias de mensajes
  03-client/     ingeniería inversa de cliente: IL2CPP, Lua, UI, ConfData
  04-world/      escena, arranque y pruebas de runtime
  09-history/    informes de sesión y experimentos (registro histórico)
server/          servidor PoC (transporte, login, escena, mundo) y tests de codec
tools/           utilidades: reempaque de bundles, verificación de hashes, catálogo, arnés de prueba
evidence/        capturas y notas de evidencia
```

---

## 7. Roadmap (sin fechas, por dependencia)

- **T1 — Mundo jugable:** login, escena, movimiento, NPCs, HUD. *Casi completo; falta HUD.*
- **T2 — Vertical slice de combate:** 1 escena, 3 sombras, skills básicas con datos reales.
- **T3 — Progresión:** persistencia + primeras misiones de historia.
- **T4 — Contenido completo:** fuera de alcance de este estudio.

El entregable valioso no es "el juego completo": es el protocolo documentado, las tablas
descifradas, el servidor modular y un arnés reproducible. Eso es lo que permite que otra
persona continúe sin volver a empezar.

---

## 8. Licencia y contribuciones

El código de este repositorio (servidor y herramientas) se publica para estudio y
preservación. No se otorga licencia sobre material de terceros. Si querés contribuir,
abrí un issue describiendo la evidencia antes de proponer un cambio de comportamiento.

**Este proyecto se publica tal como está, en pausa, para que no se pierda.**
