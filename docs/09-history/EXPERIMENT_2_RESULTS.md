# Resultados del Experimento 2 — Fase 1.2 (Análisis Estático de Cliente, Transporte y Contenedores)

**Fecha de ejecución:** 2026-11-14  
**Objetivo:** Determinar mediante análisis estático en modo de solo lectura (1) si el campo `isClientBattle` activa un motor de combate local en el cliente, (2) cómo funciona la capa de transporte y entramado TCP (`NetWorkMod` / `MsgMgr` / `LuaMsgUtils` / `MUGame.NetMod` / `Utils.TcpClient`), y (3) la especificación real de los contenedores Lua, bases de datos `ConfData*.bytes` y metadatos `global-metadata.dat`.

---

## 1. Registro de Integridad y Entropía de Archivos Analizados (Solo Lectura)

Todos los archivos del cliente en `D:\secret\P5X` fueron inspeccionados exclusivamente en modo lectura (`rb`). Se registran sus tamaños exactos, hashes SHA-256, cabeceras de 16 bytes y entropía de Shannon (calculada sobre los primeros 64 KB):

| Archivo | Ruta relativa a `D:\secret\P5X\` | Tamaño (bytes) | SHA-256 | Primeros 16 bytes (Hex) | Entropía (bits/byte) | Formato verificado |
| :--- | :--- | ---: | :--- | :--- | ---: | :--- |
| `Lua_ifiles.bytes` | `client\OuterPackage\Lua\Windows\Lua_ifiles.bytes` | 377,180 | `8107460A6C29A6E2E227A44D4F3A8D01EA60C673DC957495E1BBFBFCD5BCB3AA` | `C4 1C 00 00 00 00 00 00 DD B4 C6 05 B6 69 A2 C5` | 5.2190 | Índice binario en claro (`count = 7,364`) |
| `07B3A247F1ADE14.bytes` | `client\OuterPackage\Lua\Windows\07B3A247F1ADE14.bytes` | 1,563,494 | `1733BB806C7A8069569325AFCA989430D61B62C70C740ABC0DE692A549D5BF6A` | `56 01 00 00 8C 08 00 00 1B 4C 4A 02 0A 01 00 03` | 5.5660 | Contenedor LuaJIT 2.1 en claro (`342` chunks) |
| `2531C59CC6AD3C4.bytes` | `client\OuterPackage\Lua\Windows\2531C59CC6AD3C4.bytes` | 804,998 | `83D1A3811CCA674CFE37C85AC5320783C56DBB56C73BBE53E3BBE4E4B8D6A945` | `A4 00 00 00 FC 3A 00 00 1B 4C 4A 02 0A B6 02 00` | 5.7624 | Contenedor LuaJIT 2.1 en claro (`164` chunks) |
| `ConfigDBMap.bytes` | `client\OuterPackage\ConfData\Windows\ConfigDBMap.bytes` | 62,554 | `92018D79B5B5722808812EF04E922B0D08446E88E006D6E9D8200945A7442246` | `3C 3F 78 6D 6C 20 76 65 72 73 69 6F 6E 3D 22 31` | 4.9479 | XML UTF-8 en texto claro (`1,391` líneas) |
| `ConfDataBasic.bytes` | `client\OuterPackage\ConfData\Windows\ConfDataBasic.bytes` | 118,784 | `0A31B1ABC0D68D653280D7AECBC0B7634D87E0F9E6992181795B064997ACC935` | `97 C5 A9 27 C3 E6 01 B3 A1 B1 99 FC B5 B7 AD B5` | 7.9973 | Base de datos SQLCipher cifrada (`29 × 4096 B`) |
| `ConfDataBattle.bytes` | `client\OuterPackage\ConfData\Windows\ConfDataBattle.bytes` | 8,949,760 | `D66B5F808422E06C87B4B702CBE347D275D5FD4C999FF0EF0C060A92D5BAD504` | `A9 22 33 73 D1 92 78 D9 58 08 5E DA 5A B8 9C B5` | 7.9976 | Base de datos SQLCipher cifrada (`2185 × 4096 B`) |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | 17,648,664 | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | `AF 1B B1 FA 1F 00 00 00 10 01 00 00 B8 2E 04 00` | 4.3060 | Metadatos Unity IL2CPP v31 en claro (`0xFAB11BAF`) |

---

## 2. Resumen Ejecutivo de Hallazgos por Prioridad

### Prioridad 1 — `isClientBattle` (`SCServerConfig`, MsgID 1112)
- **Hallazgo definitivo:** `isClientBattle` es un **campo vestigial (código muerto de protocolo)** que **no se lee ni se utiliza en ningún lugar del cliente**.
- **Evidencia verificada:**
  1. Búsqueda exhaustiva en los **7,364 chunks de bytecode LuaJIT 2.1** (repartidos en los 18 paquetes `.bytes`) y en los **143,287 identificadores y literales de `global-metadata.dat`**: **0 apariciones** de `isClientBattle`.
  2. Desensamblado completo de la función manejadora `LoginMod:OnGetSCServerConfigMsg` (`E8DF29521A39C99.bytes`, chunk `0`, `Proto[43]`, 34 instrucciones): el manejador lee exclusivamente `msg.openGM`, `msg.baseTime` y `msg.timeNow`, ignorando por completo `msg.isClientBattle`.
  3. El subsistema de combate del cliente (`TbTickMod` en `07B3A247F1ADE14.bytes[95]`) opera únicamente como reproductor visual de secuencias (`DRoundSkillResult`, `SCFightRoundBattleSkill`, `SCFightActionSequence`) enviadas por el servidor.

### Prioridad 2 — Protocolo de Transporte y Entramado (`NetWorkMod` / `Utils.TcpClient`)
- **Ruta activa de serialización (`_G.isUseNewProto = true`):**
  - **Inicialización (`1410A9F67109B47.bytes[452] Proto[8]`):** Configura `pbnew.option("enum_as_value")` y `pbnew.option("int64_as_string")` y llama a `LuaMsgUtils.LoadMsgPbFile()` (que carga `allMsgPb.bytes`).
  - **Envío (`MsgMgr:SendMessage` en `07B3A247F1ADE14.bytes[64] Proto[4]`):** Elimina `msg._msg_Type_Name = nil` y llama a `LuaMsgUtils.SendMessageForLua(1, msg.protocid, msgTypeName, msg)`, delegando la codificación Protobuf y el envío por socket a C# (`MUGame.NetMod.sendByID` -> `Utils.TcpClient.Send`).
  - **Recepción (`NetWorkMod:OnGetSocketBytes` en `07B3A247F1ADE14.bytes[69] Proto[4]`):** Con `_G.isUseNewProto = true`, C# decodifica el payload Protobuf directamente a una tabla Lua antes de invocar `NetWorkMod:OnGetSocketBytes(msgId, decodedLuaTable)`, la cual despacha `ModMgr:OnMsg(msgId, msg)`.
- **Constantes de cabecera y cifrado en `Utils.TcpClient` (`TypeDef[1823]` en `global-metadata.dat`):**
  - `HEAD_SIZE = 8` bytes (`d_idx = 3270`).
  - `netdata_definelen_usebytes = 4` bytes (`d_idx = 3272`).
  - `msgdata_type_usebytes = 4` bytes (`d_idx = 3273`).
  - `MAX_BUFF_SIZE = 262,144` bytes (`256 KB`, `d_idx = 3266`).
  - `ENCRYPT = true` (`d_idx = 3271`), acompañado de los campos `_readKey (bool)` y `_rc4 (Utils.RC4)`.

### Prioridad 3 — Contenedores Lua, Configuraciones y Metadatos
- **100% del bytecode Lua (7,364 scripts) está sin cifrar:** Los 18 archivos `<HEX>.bytes` son contenedores simples con prefijos de longitud `uint32` que almacenan chunks de bytecode estándar **LuaJIT 2.1 (`1B 4C 4A 02 0A`)**.
- **`ConfigDBMap.bytes` está en texto claro (XML UTF-8):** Documenta las ~1,385 tablas de configuración (`ExcelName`) y su ubicación en los 10 archivos `ConfData*.bytes`.
- **`ConfData*.bytes` están cifrados con SQLCipher:** Páginas de 4,096 bytes con entropía ~7.997 bits/byte.
- **`global-metadata.dat` está en claro:** Formato estándar Unity IL2CPP v31 (`18,315` tipos C#, `140,823` métodos, `83,497` campos).

---

## 3. Matriz de Evidencia (Clasificación en 4 Categorías)

| Categoría | Elemento / Afirmación técnica | Evidencia verificable |
| :--- | :--- | :--- |
| **Confirmado** | `isClientBattle` no es leído ni usado por el cliente; `LoginMod:OnGetSCServerConfigMsg` solo lee `openGM`, `baseTime` y `timeNow`. | Desensamblado de `E8DF29521A39C99.bytes[0] Proto[43]` (`insns 000..033`) y búsqueda global en 7,364 chunks Lua y `global-metadata.dat`. |
| **Confirmado** | Los 18 paquetes Lua `.bytes` contienen exactamente 7,364 chunks de bytecode LuaJIT 2.1 (`1B 4C 4A 02 0A`) sin cifrado. | Escaneo completo de `Lua_ifiles.bytes` (`count = 7364`) y los 18 contenedores `.bytes` (`7364 / 7364` con magia `1B 4C 4A 02 0A`). |
| **Confirmado** | `global-metadata.dat` es un archivo IL2CPP v31 estándar sin cifrar (`magic = 0xFAB11BAF`) con 18,315 clases/tipos y 140,823 métodos. | Cabecera `AF 1B B1 FA 1F 00 00 00` y tablas `Il2CppTypeDefinition` / `Il2CppMethodDefinition`. |
| **Confirmado** | `Utils.TcpClient` (`TypeDef[1823]`) define constantes por defecto `HEAD_SIZE = 8`, `netdata_definelen_usebytes = 4`, `msgdata_type_usebytes = 4`, `MAX_BUFF_SIZE = 262144` y `ENCRYPT = true`, e incluye una instancia `Utils.RC4` (`_rc4`) y bandera `_readKey`. | Tabla `fieldDefaultValues` (`fields 5801..5820`) y definiciones de campos/métodos de `TypeDef[1823]` y `TypeDef[1830]` en `global-metadata.dat`. |
| **Confirmado** | `ConfigDBMap.bytes` es XML en claro y `ConfData*.bytes` son bases de datos SQLite cifradas con SQLCipher (`sqlcipher.dll`). | Cabecera XML de `ConfigDBMap.bytes`, entropía `7.997` de `ConfData*.bytes` y cadenas `luaopen_lsqlcipher` en `global-metadata.dat`. |
| **Indicio sólido** | La cabecera TCP de 8 bytes se compone de un entero de 32 bits en orden de red (big-endian) para longitud y un entero de 32 bits para `msgId` (`readInt32FromNetwork`, `setBufferInt`, `getBufferInt`). | Métodos `Utils.TcpClient.readInt32FromNetwork(BinaryReader)`, `setBufferInt(byte[], int, int)`, `getBufferInt(byte[])` y constantes `4 + 4 = 8`. |
| **Hipótesis** | Al conectar el socket TCP (`10403`/`10404`), el servidor envía primero un paquete inicial con la clave de sesión RC4 (leído cuando `_readKey == false`) o inicializa `_rc4` antes de intercambiar tramas Protobuf. | Presencia conjunta de `bool ENCRYPT = true`, `bool _readKey` y `Utils.RC4 _rc4` en `Utils.TcpClient` (`TypeDef[1823]`). |
| **Desconocido** | Orden exacto de los dos campos de 4 bytes en la cabecera de 8 bytes (`[len][msgId]` vs `[msgId][len]`), si `len` incluye o no los 8 bytes de cabecera, y cómo se negocia/inicializa `_rc4` (`_readKey`). | Código nativo compilado dentro de `GameAssembly.dll` (no contenido en `global-metadata.dat`) o tráfico en vivo en los puertos `10403`/`10404`. |

---

## 4. Documentos Generados en este Experimento

1. [CLIENT_BATTLE_ANALYSIS.md](file:///D:/secret/docs/CLIENT_BATTLE_ANALYSIS.md): Desensamblado y análisis exhaustivo de `isClientBattle`, `SCServerConfig` y la arquitectura de combate por turnos (`TbTickMod`).
2. [NETWORK_FRAMING_ANALYSIS.md](file:///D:/secret/docs/NETWORK_FRAMING_ANALYSIS.md): Arquitectura de transporte entre Lua (`MsgMgr`, `NetWorkMod`) y C# (`LuaMsgUtils`, `MUGame.NetMod`, `Utils.TcpClient`, `Utils.RC4`).
3. [LUA_FORMAT_ANALYSIS.md](file:///D:/secret/docs/LUA_FORMAT_ANALYSIS.md): Especificación binaria de `Lua_ifiles.bytes`, contenedores LuaJIT `.bytes`, `ConfigDBMap.bytes`, `ConfData*.bytes` y `global-metadata.dat`.
4. [FEASIBILITY_UPDATE.md](file:///D:/secret/docs/FEASIBILITY_UPDATE.md): Evaluación actualizada de viabilidad técnica y propuesta del Experimento 3 mínimo necesario antes de la Prueba de Concepto (PoC).
