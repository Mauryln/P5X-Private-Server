# Fase 2 — Informe de PoC de Servidor Local: Handshake TCP + Login Mínimo (`127.0.0.1`)

> **Alcance y cumplimiento normativo:** Trabajo ejecutado exclusivamente en `127.0.0.1` (sin conexión a servidores externos), en modo de **solo lectura** sobre `D:\secret\P5X` (`INTEGRITY_PRE == INTEGRITY_POST`) y con todo el código experimental aislado en `scratch/` (`proto2_codec.py`, `poc_login_server.py`, `test_poc_client_harness.py`).

---

## 1. Regla Cero — Verificación Adversaria de `Utils.RC4::Crypt` (`VA 0x180D01A50`)

Antes de escribir una sola línea del servidor PoC, se realizó un barrido exhaustivo sobre los **77.450.240 bytes** (73,86 MB) de [GameAssembly.dll](file:///D:/secret/P5X/client/pc/GameAssembly.dll) buscando todas las instrucciones `CALL rel32` (`E8`), `JMP rel32` (`E9`) y punteros de 64 bits (`QWORD`) hacia `Utils.RC4::Crypt` (`VA 0x180D01A50`, `RVA 0x00D01A50`, `FileOffset 0x00CF0450`, `TypeDef[1830]`, `Token 0x06006160`) y `Utils.RC4::.ctor(byte[])` (`VA 0x180D01B90`, `RVA 0x00D01B90`, `FileOffset 0x00CF0590`, `Token 0x06006161`).

### 1.1. Totalidad de sitios de llamada a `Utils.RC4::Crypt` (`VA 0x180D01A50`)

En todo `GameAssembly.dll` existen **exactamente 3 instrucciones `CALL E8`** (y `0` instrucciones `JMP E9`) hacia `0x180D01A50`. Las 3 pertenecen exclusivamente a la ruta de **envío (`Cliente -> Servidor`)** dentro de `Utils.TcpClient` (`TypeDef[1823]`):

| # | Función Contenedora (`TypeDef[1823]`) | Token IL2CPP | Inicio de Función (`VA`) | Sitio del `CALL` (`VA` / `RVA` / `FileOff`) | Desplazamiento | Fragmento de Bytes y Desensamblado Exacto | Nivel de Evidencia |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `Utils.TcpClient::Send_begin(int msgId, byte[] data, int dataSize)` | `0x0600610B` (`Method[24842]`) | `0x180CEDF60` | `0x180CEE10A` / `0x00CEE10A` / `0x00CECB0A` | `+0x1AA` | `48 8b 4b 78` (`mov rcx, [rbx+0x78]`)<br>`44 8b ce` (`mov r9d, esi`)<br>`41 b8 04 00 00 00` (`mov r8d, 4`)<br>`48 8b d7` (`mov rdx, rdi`)<br>`e8 41 39 01 00` (`call 0x180d01a50`) | **CONFIRMADO** |
| **2** | `Utils.TcpClient::Send(msg_base msg)` | `0x06006108` (`Method[24839]`) | `0x180CEE410` | `0x180CEE6A6` / `0x00CEE6A6` / `0x00CED0A6` | `+0x296` | `48 8b 4f 78` (`mov rcx, [rdi+0x78]`)<br>`44 8b cd` (`mov r9d, ebp`)<br>`41 b8 04 00 00 00` (`mov r8d, 4`)<br>`48 8b d3` (`mov rdx, rbx`)<br>`e8 a5 33 01 00` (`call 0x180d01a50`) | **CONFIRMADO** |
| **3** | `Utils.TcpClient::rawSend(byte[] data, int start, int end)` | `0x0600610C` (`Method[24843]`) | `0x180CEED70` | `0x180CEEDAC` / `0x00CEEDAC` / `0x00CED7AC` | `+0x03C` | `48 8b 49 78` (`mov rcx, [rcx+0x78]`)<br>`44 8b cf` (`mov r9d, edi`)<br>`48 c7 44 24 20 00 00 00 00` (`mov qword ptr [rsp+0x20], 0`)<br>`e8 9f 2c 01 00` (`call 0x180d01a50`) | **CONFIRMADO** |

Adicionalmente:
- **Punteros QWORD a `0x180D01A50`:** Existe **1 única entrada** en `.data` (`FileOffset 0x03FFF848`, `RVA 0x04001248`), correspondiente a la tabla de metadatos `g_MethodPointers` para el token `0x06006160`. No existe ninguna referencia en vtables ni delegados de recepción.
- **Sitios de llamada a `Utils.RC4::.ctor(byte[])` (`VA 0x180D01B90`):** Existen **únicamente 2 instrucciones `CALL E8`** en todo el binario:
  1. `VA 0x180CEDCF5` (`FileOffset 0x00CEC6F5`) dentro de `Utils.TcpClient::ReceivePayload` (`+0x385`, al procesar la Trama 0 cuando `_readKey == false`).
  2. `VA 0x180D15AF0` (`FileOffset 0x00D044F0`) dentro de la clase obsoleta `Utils.TcpClient__old::ReceivePayload` (`+0x3A0`).
- **Conclusión de la Regla Cero:** Existen **0 llamadas** a `Utils.RC4::Crypt` en `ReceivePayload`, `DealMessage`, `Connect` o cualquier ruta de recepción. La asimetría (`Cliente -> Servidor` cifrado con RC4 en `[4..totalLen)`, `Servidor -> Cliente` en texto plano) queda **CONFIRMADA** sin excepciones.

---

## 2. Hallazgos Críticos de la Máquina de Estados de Login y `tolua.dll!pbnew`

El análisis estático cruzado entre `GameAssembly.dll`, `tolua.dll` y el bytecode LuaJIT de `LoginMod` ([E8DF29521A39C99.bytes](file:///D:/secret/P5X/client/OuterPackage/Lua/Windows/E8DF29521A39C99.bytes) Chunk #0) y `NetWorkMod` ([07B3A247F1ADE14.bytes](file:///D:/secret/P5X/client/OuterPackage/Lua/Windows/07B3A247F1ADE14.bytes) Chunk #69) reveló tres requisitos estructurales indispensables para que el cliente complete el login sin desconectarse:

1. **Transición de Doble Conexión TCP (`connecting_gate` $\rightarrow$ `DisConnect()` $\rightarrow$ `connecting_logic`):**
   - En `LoginMod:OnSCLoginResult` (Proto #30, instrucciones `161..172`), al recibir `SCLoginResult` (`102`) con `resultCode == 0`, el cliente extrae `NewServerInfo.serverIP` y `NewServerInfo.serverPort` a partir de `msg.gameAddress` (`split_IP_Port`), guarda `msg.sessionId`, **invoca `ConnectMgr:DisConnect()` (`bc 166..169`) cerrando la primera conexión TCP, e inmediatamente llama a `self:OnTryConnectLogic()` (`bc 170..172`)**.
   - `OnTryConnectLogic` (Proto #52) cambia `mLoginState` a `ELoginState.connecting_logic` y abre una **segunda conexión TCP** hacia `gameAddress`.
   - Como `Utils.TcpClient::Connect` (`VA 0x180CED319`) ejecuta `mov byte ptr [rbx+0x70], 0` (`_readKey = false`), **el servidor local debe enviar la Trama 0 (`[int32 BE 4+K][keyBytes]`) inmediatamente en cada `accept()` TCP** (tanto en la Conexión 1 como en la Conexión 2).

2. **Decodificación Nativa `tolua.dll!pbnew_decode_and_pushmsg` y Causa Raíz de `sn=1046007`:**
   - Cuando un mensaje `Servidor -> Cliente` llega a `MUGame.NetMod::CallMsg` (`VA 0x180D82320`), el cliente comprueba `GameConfig.UseNewProtoBuf` (`[rcx+0x9e]`). Cuando está activo (`_G.isUseNewProto == true`), invoca `LuaFunction::Call_PB` (`VA 0x180BAE170`) $\rightarrow$ `LuaDLL::pbnew_decode_and_pushmsg(L, msgId, buf, len)` (`VA 0x180C162B0` $\rightarrow$ [tolua.dll](file:///D:/secret/P5X/client/pc/P5X_Data/Plugins/x86_64/tolua.dll) `RVA 0x013070`).
   - En `tolua.dll!pbnew_decode_and_pushmsg` (`0x394A43070`), la función consulta `_G.MsgTable[msgId]` (definida en `07B3A247F1ADE14.bytes` Chunk #53, donde los nombres de tipo no llevan prefijo de paquete, p. ej. `[102] = "SCLoginResult"`, `[104] = "SCLoginGateResult"`, `[1112] = "SCServerConfig"`, `[1002] = "SCQueryCharactersResult"`, `[1008] = "SCCharacterLoginResult"`) y decodifica el slice Protobuf contra [allMsgPb.bytes](file:///D:/secret/P5X/client/OuterPackage/Lua/Windows/allMsgPb.bytes).
   - **Validación estricta de etiquetas en `pbnew` (`0x394A41A98..0x394A41AAA`):** Si un mensaje recibido contiene un número de campo (`tag >> 3`) que no existe en el descriptor de `allMsgPb.bytes`, `pbnew_decode_and_pushmsg` asigna `mov dword ptr [rip+0x177db1], 2` (`rc = 2`) y aborta la llamada. Durante las pruebas con `tolua.dll`, esto permitió detectar y corregir que `SCLoginResult` (`102`) en `allMsgPb.bytes` solo define los campos `1..11` (el campo `serverUUID` existe en `CSLogin = 10` y `CSLoginGate = 6` como `int32`, pero no en `SCLoginResult`).
   - **Disparo de `sn=1046007`:** En `NetWorkMod:OnGetSocketBytes` (`07B3A247F1ADE14.bytes` Chunk #69 Proto #4, `bc 022..043`), si `msgId < 1` o `msgId >= 1000000` (lo cual ocurre de inmediato si el servidor cifra erróneamente `S -> C` con RC4, corrompiendo los bytes `[4..7]` del `msgId`), el cliente registra `"OnGetSocketBytes msg is error, text sn=1046007, DisConnect, msg id ="` e invoca `ConnectMgr:DisConnect()`.

---

## 3. Secuencia Real de Tramas Intercambiadas en `127.0.0.1:18100`

La validación extremo a extremo se ejecutó en `127.0.0.1:18100` cargando la biblioteca nativa real del cliente ([tolua.dll](file:///D:/secret/P5X/client/pc/P5X_Data/Plugins/x86_64/tolua.dll)), el esquema binario original ([allMsgPb.bytes](file:///D:/secret/P5X/client/OuterPackage/Lua/Windows/allMsgPb.bytes)) mediante `Lpb_loadfile_from_bytes` y el chunk original `protocol/MsgTable` (`07B3A247F1ADE14.bytes` Chunk #53) mediante `luaL_loadbuffer`, verificando cada trama con `pbnew.encode` y `pbnew_decode_and_pushmsg`.

### 3.1. Tabla Resumen de la Secuencia Completa (11 Tramas en 2 Conexiones TCP)

| # | Conexión TCP | Dirección | `msgId` / Tipo | `totalLen` | Cabecera en Cable (Hex) | Cabecera Descifrada (Hex) | Estado `pbnew` / Cliente | Nivel de Evidencia |
| :- | :---: | :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **01** | Conn #1 (Login) | `S -> C` | `TRAMA_0` (`Handshake_RC4_Key`) | 20 B | `00 00 00 14` | `00 00 00 14` | `_rc4 = new RC4(16B)`, `_readKey = true` | **CONFIRMADO** |
| **02** | Conn #1 (Login) | `C -> S` | `101` (`CSLogin`) | 134 B | `00 00 00 86 35 e2 cc 46` | `00 00 00 86 00 00 00 65` | Cifrado RC4 en `[4..134)` | **CONFIRMADO** |
| **03** | Conn #1 (Login) | `S -> C` | `102` (`SCLoginResult`) | 73 B | `00 00 00 49 00 00 00 66` | `00 00 00 49 00 00 00 66` | `rc=0` $\rightarrow$ `DisConnect()` + `OnTryConnectLogic()` | **CONFIRMADO** |
| **04** | Conn #2 (Gate) | `S -> C` | `TRAMA_0` (`Handshake_RC4_Key`) | 20 B | `00 00 00 14` | `00 00 00 14` | `_rc4 = new RC4(16B)`, `_readKey = true` | **CONFIRMADO** |
| **05** | Conn #2 (Gate) | `C -> S` | `103` (`CSLoginGate`) | 149 B | `00 00 00 95 35 e2 cc 44` | `00 00 00 95 00 00 00 67` | Cifrado RC4 en `[4..149)` | **CONFIRMADO** |
| **06** | Conn #2 (Gate) | `S -> C` | `104` (`SCLoginGateResult`) | 10 B | `00 00 00 0a 00 00 00 68` | `00 00 00 0a 00 00 00 68` | `rc=0`, `errorCode=0` (`08 00` Proto2 `required`) | **CONFIRMADO** |
| **07** | Conn #2 (Gate) | `S -> C` | `1112` (`SCServerConfig`) | 30 B | `00 00 00 1e 00 00 04 58` | `00 00 00 1e 00 00 04 58` | `rc=0`, `isClientBattle=false`, `openGM=false` | **CONFIRMADO** |
| **08** | Conn #2 (Gate) | `C -> S` | `1001` (`CSQueryCharacters`) | 8 B | `00 00 00 08 e9 ec 36 42` | `00 00 00 08 00 00 03 e9` | Cuerpo vacío (0 B); `msgId` cifrado con RC4 | **CONFIRMADO** |
| **09** | Conn #2 (Gate) | `S -> C` | `1002` (`SCQueryCharactersResult`) | 29 B | `00 00 00 1d 00 00 03 ea` | `00 00 00 1d 00 00 03 ea` | `rc=0`, 1 `DCharacter` (`id=10001`, `"Wonder"`) | **CONFIRMADO** |
| **10** | Conn #2 (Gate) | `C -> S` | `1007` (`CSCharacterLogin`) | 15 B | `00 00 00 0f 2b 11 fc 90` | `00 00 00 0f 00 00 03 ef` | Cifrado RC4 en `[4..15)`, `humanId=10001` | **CONFIRMADO** |
| **11** | Conn #2 (Gate) | `S -> C` | `1008` (`SCCharacterLoginResult`) | 12 B | `00 00 00 0c 00 00 03 f0` | `00 00 00 0c 00 00 03 f0` | `rc=0`, `resultCode=0` $\rightarrow$ `CharacterLoginSuccess` | **CONFIRMADO** |

---

### 3.2. Detalle de Tramas, Bytes en Cable y Payloads Decodificados (Ofuscados)

#### Trama `#01` (Conn #1, `S -> C`) y Trama `#04` (Conn #2, `S -> C`) — `TRAMA_0` (`Handshake_RC4_Key`)
- **Cabecera (4B BE):** `00 00 00 14` (`totalLen = 20`)
- **Payload (16B clave RC4 en claro):** `50 35 58 4c 6f 63 61 6c 4b 65 79 32 30 32 36 21` (`"P5XLocalKey2026!"`)
- **Efecto en cliente:** `ReceivePayload` lee `keyLen = 20 - 4 = 16`, instancia `new Utils.RC4(keyBytes)` y activa `_readKey = true`.

#### Trama `#02` (Conn #1, `C -> S`) — `CSLogin` (`msgId = 101`)
- **Cabecera en cable (8B):** `00 00 00 86 35 e2 cc 46`
- **Cabecera descifrada (8B):** `00 00 00 86 00 00 00 65` (`totalLen = 134`, `msgId = 101`)
- **Payload decodificado (datos sensibles ofuscados):**
  ```json
  {
    "account": "<REDACTED:16B>",
    "password": "",
    "token": "<REDACTED:19B>",
    "channelId": "steam",
    "mediaId": "49",
    "version": "1.0.0",
    "resVersion": 1,
    "phoneInfo": {
      "deviceId": "<REDACTED:15B>",
      "deviceModel": "PC",
      "deviceSys": "Windows 11",
      "deviceRam": "16384",
      "mac": "",
      "idfa": "",
      "os": 0,
      "language": "English"
    },
    "sdkType": 0,
    "serverUUID": 1,
    "channelPlatform": "PC"
  }
  ```

#### Trama `#03` (Conn #1, `S -> C`) — `SCLoginResult` (`msgId = 102`)
- **Cabecera en cable (8B texto plano):** `00 00 00 49 00 00 00 66` (`totalLen = 73`, `msgId = 102`)
- **Payload Proto2 (65B hex):**
  `08 00 12 10 <account:16B> 18 80 e2 cf aa 06 20 01 2a 0f 31 32 37 2e 30 2e 30 2e 31 3a 31 38 31 30 30 30 a1 8d 06 38 1e 40 00 48 00 5a 08 31 33 39 36 35 32 33 37`
- **Campos Proto2 (`required` incluidos explícitamente con valor `0`/`false`):**
  - `1: resultCode = 0` (`08 00`, `required`)
  - `2: account = "<REDACTED:16B>"`
  - `3: zoneTime = 1700000000` (`18 80 e2 cf aa 06`)
  - `4: serverId = 1` (`20 01`)
  - `5: gameAddress = "127.0.0.1:18100"` (`2a 0f ...`)
  - `6: sessionId = 100001` (`30 a1 8d 06`)
  - `7: timeout = 30` (`38 1e`)
  - `8: prepareReconnection = false` (`40 00`, `required`)
  - `9: isNeedUpdate = false` (`48 00`, `required`)
  - `11: revision = "13965237"` (`5a 08 ...`)

#### Trama `#05` (Conn #2, `C -> S`) — `CSLoginGate` (`msgId = 103`)
- **Cabecera en cable (8B):** `00 00 00 95 35 e2 cc 44`
- **Cabecera descifrada (8B):** `00 00 00 95 00 00 00 67` (`totalLen = 149`, `msgId = 103`)
- **Payload decodificado (ofuscado):**
  `account="<REDACTED:16B>"`, `sessionId=100001`, `token="<REDACTED:19B>"`, `sdkType=0`, `serverUUID=1`, `channelPlatform="PC"`, `steamId="<REDACTED:17B>"`, `distinctId="<REDACTED:10B>"`, `phoneInfo={...}`.

#### Trama `#06` (Conn #2, `S -> C`) — `SCLoginGateResult` (`msgId = 104`)
- **Cabecera en cable (8B texto plano):** `00 00 00 0a 00 00 00 68` (`totalLen = 10`, `msgId = 104`)
- **Payload Proto2 (2B hex):** `08 00` (`required int32 errorCode = 1` con valor `0`).

#### Trama `#07` (Conn #2, `S -> C`) — `SCServerConfig` (`msgId = 1112`)
- **Cabecera en cable (8B texto plano):** `00 00 00 1e 00 00 04 58` (`totalLen = 30`, `msgId = 1112`)
- **Payload Proto2 (22B hex):** `08 00 10 00 18 80 d0 95 ff bc 31 20 80 d0 95 ff bc 31 28 80 e1 01`
- **Campos Proto2:**
  - `1: isClientBattle = false` (`08 00`, `required`)
  - `2: openGM = false` (`10 00`, `required`)
  - `3: timeNow = 1700000000000` (`18 80 d0 95 ff bc 31`, `required`)
  - `4: baseTime = 1700000000000` (`20 80 d0 95 ff bc 31`, `required`)
  - `5: timeZone = 28800` (`28 80 e1 01`, `optional`)

#### Trama `#08` (Conn #2, `C -> S`) — `CSQueryCharacters` (`msgId = 1001`)
- **Cabecera en cable (8B):** `00 00 00 08 e9 ec 36 42`
- **Cabecera descifrada (8B):** `00 00 00 08 00 00 03 e9` (`totalLen = 8`, `msgId = 1001`)
- **Payload:** Vacío (`0` bytes). Obsérvese que `e9 ec 36 42` es el `msgId` (`00 00 03 e9`) cifrado con el keystream RC4 tras consumir los 145 bytes previos de `CSLoginGate`.

#### Trama `#09` (Conn #2, `S -> C`) — `SCQueryCharactersResult` (`msgId = 1002`)
- **Cabecera en cable (8B texto plano):** `00 00 00 1d 00 00 03 ea` (`totalLen = 29`, `msgId = 1002`)
- **Payload Proto2 (21B hex):** `0a 13 08 91 4e 12 06 57 6f 6e 64 65 72 18 01 20 01 28 01 58 01`
- **Campos Proto2:** `characters[0] = { id = 10001 (required), name = "Wonder", profession = 1, level = 1, sex = 1, sn = 1 }`.

#### Trama `#10` (Conn #2, `C -> S`) — `CSCharacterLogin` (`msgId = 1007`)
- **Cabecera en cable (8B):** `00 00 00 0f 2b 11 fc 90`
- **Cabecera descifrada (8B):** `00 00 00 0f 00 00 03 ef` (`totalLen = 15`, `msgId = 1007`)
- **Payload en cable (7B cifrado):** `43 29 63 f6 c6 d7 43`
- **Payload descifrado (7B Proto2):** `08 91 4e 10 12 18 01` (`humanId = 10001`, `age = 18`, `adult = true`).

#### Trama `#11` (Conn #2, `S -> C`) — `SCCharacterLoginResult` (`msgId = 1008`)
- **Cabecera en cable (8B texto plano):** `00 00 00 0c 00 00 03 f0` (`totalLen = 12`, `msgId = 1008`)
- **Payload Proto2 (4B hex):** `08 00 10 01` (`required int32 resultCode = 0`, `optional ELoginType loginType = 1`).
- **Resultado en cliente:** `LoginMod:OnSCCharacterLoginResult` evalúa `resultCode <= 0` y emite `EVENT_LOGIN.CharacterLoginSuccess` sin desconexión.

---

### 3.3. Pruebas Negativas / Adversarias Ejecutadas

1. **`[NEG-1]` Simulación de cifrado RC4 en `Servidor -> Cliente`:**
   - Al cifrar los bytes `[4..10)` de `SCLoginGateResult (104)` con `RC4("P5XLocalKey2026!")`, `readInt32FromNetwork(4)` en el cliente lee `msgId = 904055883` (`0x35E2CC4B`), fuera del rango `[1..999999]`, disparando de inmediato:
     `OnGetSocketBytes msg is error, text sn=1046007, DisConnect, msg id = 904055883`.
2. **`[NEG-2]` Payload Protobuf truncado/corrupto (`08 80 80 80`):**
   - `tolua.dll!pbnew_decode_and_pushmsg` devuelve `rc = 1` (error de decodificación wire), provocando que `LuaFunction::Call_PB` (`VA 0x180BAE170`) aborte la entrega del mensaje.

---

## 4. Diagnóstico de Barreras Previas a TCP en `P5X.exe` y Siguiente Paso

### 4.1. Barreras Previas a TCP en el Ejecutable `P5X.exe` sin Modificar (`CONFIRMADO`)
Aunque la pila TCP + RC4 + `tolua.dll!pbnew` + `LoginMod` completa los 6 pasos contra `127.0.0.1:18100`, el ejecutable completo `P5X.exe` en modo de solo lectura posee **3 compuertas previas** antes de invocar `ConnectMgr:OnTryConnectServer`:
1. **`SteamAPI_RestartAppIfNecessary` (`steam_api64.dll`):** Comprobación de sesión activa de Steam al iniciar el proceso.
2. **`LoginMod:LoadServerList` (`E8DF29521A39C99.bytes` Chunk #0 Proto #69):** Cuando `GameConfig.IsDownloadServerList` es `true`, descarga por HTTP el JSON de lista de servidores (`_G.ServerListDownLoadURL`) y verifica que `tonumber(ServerListData.luaver) <= _G.luaDataVersionNumber` (mostrando error `1000085`/`1000086`/`1000087` si falla) para poblar `LastInfo.serverIP` y `LastInfo.serverPort`.
3. **Compuerta `OneSDKMgr:IsSDKLoggedIn()` (`LoginMod:EnterLogin` Proto #66 y `LoginMod:CSLogin` Proto #23):** Si `OneSDKMgr:IsSDKAvailable()` es `true` y `OneSDKMgr:IsSDKLoggedIn()` devuelve `false`, `LoginMod:CSLogin()` imprime `"CSLogin sdk not login"`, invoca `OneSDKMgr:Login()` y retorna sin enviar `CSLogin (101)`.

### 4.2. Siguiente Paso Propuesto (Fase 2.2)
1. **Continuación post-login (`1008` $\rightarrow$ Entrada a Escena):** Tras `EVENT_LOGIN.CharacterLoginSuccess`, el cliente espera la sincronización inicial de personaje y escena (`SCInitData` / `SCEnterScene` / `CSLoginEnd`). Documentar y emular los mensajes mínimos posteriores a `SCCharacterLoginResult (1008)` para alcanzar la carga de una escena jugable offline en `127.0.0.1`.
2. **Redirección limpia de `ServerListDownLoadURL` a `127.0.0.1`:** Servir en `127.0.0.1` el JSON local de `LoadServerList` con `ip = "127.0.0.1"`, `port = 18100` y `luaver = _G.luaDataVersionNumber`.

---

## 5. Verificación de Integridad (`INTEGRITY_PRE` vs `INTEGRITY_POST`)

| Archivo | Hash SHA-256 (`INTEGRITY_PRE`) | Hash SHA-256 (`INTEGRITY_POST`) | Estado |
| :--- | :--- | :--- | :--- |
| [GameAssembly.dll](file:///D:/secret/P5X/client/pc/GameAssembly.dll) | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **INTACTO (`CONFIRMADO`)** |
| [global-metadata.dat](file:///D:/secret/P5X/client/pc/P5X_Data/il2cpp_data/Metadata/global-metadata.dat) | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **INTACTO (`CONFIRMADO`)** |
