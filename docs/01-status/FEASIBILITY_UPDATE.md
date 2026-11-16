# Actualización de Viabilidad Técnica tras el Experimento 2

**Fecha:** 2026-11-14  
**Estado del proyecto:** Fase 1.2 completada — Transición hacia Fase 1.3 (Verificación final de cabecera/RC4 en `Utils.TcpClient`).

---

## 1. Impacto de los Hallazgos del Experimento 2 en la Viabilidad Global

Los resultados del Experimento 2 transforman sustancialmente el panorama técnico del proyecto de preservación para la versión **Global/Steam PC (`P5XEN_41000_PC`)**:

### 1.1. Factores que Incrementan Drásticamente la Viabilidad (Noticias Positivas)
1. **El 100% de la lógica Lua del cliente (`7,364` scripts en 18 contenedores `.bytes`) está en claro (LuaJIT 2.1 estándar):**
   - No existe cifrado personalizado sobre los contenedores Lua ni sobre el bytecode LuaJIT (`1B 4C 4A 02 0A`).
   - Esto significa que **no estamos a ciegas ante la lógica del servidor**: para cualquier mensaje `SC*` de los 2,195 `MsgID`s catalogados en el Experimento 1, podemos desensamblar el manejador Lua correspondiente (como hicimos con `LoginMod:OnGetSCServerConfigMsg` en `E8DF29521A39C99.bytes[0]`) y ver con precisión matemática **qué campos lee el cliente, en qué orden y qué valores espera para no fallar**.
2. **`global-metadata.dat` está en claro (Unity IL2CPP v31 estándar):**
   - Las 18,315 definiciones de clases C#, sus 83,497 campos, sus constantes por defecto (`fieldDefaultValues`) y sus 140,823 métodos son completamente legibles sin necesidad de herramientas invasivas.
3. **`openGM = true` en `SCServerConfig` (`MsgID 1112`) es funcional:**
   - A diferencia de `isClientBattle`, el campo `openGM` sí se lee en `LoginMod:OnGetSCServerConfigMsg` y activa `GameConfig.EnableGM = true`, lo cual habilita herramientas de depuración nativas del cliente (`GMCmdMgr.showClientMsgCS` y `GMCmdMgr.showClientMsgSC`).

### 1.2. Factores que Ajustan el Alcance del Servidor (Realismo Técnico)
1. **Descarte de `isClientBattle` (`SCServerConfig`, MsgID 1112):**
   - Al confirmarse que `isClientBattle` es un campo vestigial con 0 referencias en el código del cliente, **queda descartado el atajo de delegar el cálculo de combate al cliente**.
   - **Solución escalonada para preservación:**
     - *Etapa PoC (Corto plazo):* Implementar un **resolutor de combate mínimo (*Stub/Dummy Battle Resolver*)** en el servidor que rresponda a la seleccion de habilidad (CSRoundSkillList 1325 / CSRoundSetSkill 1337; preliminarmente referido como 2722) devolviendo un SCFightRoundBattleSkill (MsgID 1327, preliminarmente 2723) con un DRoundSkillResultico válido (aplicando daño fijo o victoria inmediata). Esto permite desbloquear el flujo de historia, cinemáticas y exploración de palacios sin tener que programar todas las fórmulas matemáticas desde el primer día.
     - *Etapa Fidelidad (Medio/Largo plazo):* Implementar progresivamente las reglas de debilidades elementales, *One More*, *All-Out Attack* y *Highlight* en el servidor.
2. **Existencia de `ENCRYPT = true` y `Utils.RC4` en `Utils.TcpClient`:**
   - El socket TCP (`Utils.TcpClient`, `TypeDef[1823]`) define `HEAD_SIZE = 8` (`4B` longitud + `4B` `MsgID`), pero también define `ENCRYPT = true`, `_readKey (bool)` y `_rc4 (Utils.RC4)`.
   - Un servidor local compatible debe hablar exactamente el mismo protocolo de entramado y flujo RC4 que `Utils.TcpClient` espera en el puerto TCP (`10403`/`10404`).

---

## 2. Evaluación del Criterio de Continuación: ¿Podemos construir ya la PoC?

| Componente necesario para la PoC | Estado actual | Nivel de certeza |
| :--- | :--- | :--- |
| Esquema completo Protobuf (`allMsgPb.bytes` -> `msg.proto`) | **Completado** (2,663 mensajes, 37 enums) | 100% (Confirmado) |
| Catálogo de `MsgID` (`2,195` opcodes C↔S) | **Completado** (`MESSAGE_CATALOG.md`) | 100% (Confirmado) |
| Lógica de manejadores Lua (`LoginMod`, `SceneMod`, `TbTickMod`) | **Completado / Accesible en claro** (`7,364` chunks LuaJIT) | 100% (Confirmado) |
| Constantes de cabecera TCP (`HEAD_SIZE = 8`, `4B len` + `4B msgId`) | **Completado** (`global-metadata.dat`, `TypeDef[1823]`) | 100% (Confirmado) |
| Orden exacto de los dos `int32` en la cabecera de 8 bytes y semántica de `_readKey` / `_rc4` en `Utils.TcpClient` | **Pendiente de verificación puntual** | Hipótesis sólida (requiere Experimento 3) |

**Veredicto:** Estamos a **un único paso de verificación** de poder diseñar e implementar la Prueba de Concepto (PoC) de servidor local. Intentar escribir el servidor TCP ahora mismo sin verificar cómo `Utils.TcpClient` inicializa `_rc4` (`_readKey`) y el orden exacto de los 8 bytes de cabecera provocaría un error de desconexión inmediata (`OnGetSocketBytes msg is error, text sn=1046007, DisConnect`).

---

## 3. Recomendación para el Siguiente Paso: Experimento 3 (Fase 1.3)

Se recomienda autorizar un **Experimento 3 breve y estrictamente acotado** para cerrar la última incógnita de la capa de transporte (`Utils.TcpClient`), mediante cualquiera de estas dos vías (o ambas de forma complementaria):

### Vía A (Análisis estático en solo lectura de los métodos de `Utils.TcpClient`)
Inspeccionar en modo de solo lectura las instrucciones de los métodos de `Utils.TcpClient` (`TypeDef[1823]`: `Send_begin`, `ReceivePayload`, `DealMessage`, `readInt32FromNetwork`, `setBufferInt`) y `Utils.RC4` (`TypeDef[1830]`) en `GameAssembly.dll` utilizando las tablas de metadatos ya extraídas, con el único fin de documentar:
1. Qué escribe exactamente `Send_begin` en los 8 bytes de `_sendHeaderBuffer` (orden de `length` y `msgId`, y si `length` suma o no la cabecera).
2. Qué hace `ReceivePayload` / `DealMessage` cuando `_readKey == false` (cómo recibe o inicializa la clave de `Utils.RC4`) y en qué dirección se aplica `_rc4.Crypt`.

### Vía B (Captura pasiva de red de diagnóstico sobre sesión propia)
Si el usuario dispone de acceso a una sesión activa antes del cierre definitivo de los servidores:
- Capturar con **Wireshark** (filtro `tcp.port == 10403 or tcp.port == 10404`) los primeros 10 paquetes TCP tras pulsar *Login* para contrastar empíricamente el handshake del socket con el análisis estático de `Utils.TcpClient`.

Una vez documentados esos dos detalles en `TRANSPORT_WIRE_SPEC.md` (Experimento 3), tendremos el **100% de la especificación técnica necesaria** para pasar a la **Fase 2: Diseño de la Prueba de Concepto (PoC) de Servidor Local (`CSLogin` → `SCServerConfig` → `SCLogin` → `CSGetRoleList` → `SCRoleList` → `CSEnterGame` → `SCEnterScene`)**.
