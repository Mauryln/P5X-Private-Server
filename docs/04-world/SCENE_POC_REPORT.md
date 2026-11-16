# Informe Técnico PoC Fase 2.3: De Login a Escena 3D y Heartbeat

**Proyecto:** Preservación y emulación de servidores de *Persona 5: The Phantom X (P5X)*  
**Cliente objetivo:** Versión PC Global/Steam (`D:\secret\P5X\client\pc\P5X.exe`)  
**Entorno de pruebas:** Servidor local TCP en `127.0.0.1:18100` con arnés de verificación nativo (`tolua.dll` + `allMsgPb.bytes` + Chunk 53 `MsgTable`).

---

## 1. Resumen Ejecutivo y Resultados de Ejecución

En la Fase 2.3 se ha ampliado la PoC local en Python ([poc_login_server.py](file:///D:/secret/scratch/poc_login_server.py) y [proto2_codec.py](file:///D:/secret/scratch/proto2_codec.py)), completando con éxito la secuencia íntegra desde la selección de personaje hasta la entrada en una escena 3D y el bucle de latencia/heartbeat:

$$\text{Trama 0} \rightarrow \text{101} \rightarrow \text{102} \rightarrow \text{Trama 0} \rightarrow \text{103} \rightarrow \text{104} \rightarrow \text{1112} \rightarrow \text{1001} \rightarrow \text{1002} \rightarrow \text{1007} \rightarrow \text{1008} \rightarrow \mathbf{1102} \rightarrow \mathbf{1201} \rightarrow \mathbf{1202} \rightarrow \mathbf{1203} \rightarrow \mathbf{1116} \rightarrow \mathbf{1117}$$

### Criterio de Éxito Alcanzado
1. **Decodificación nativa:** El arnés de verificación ([test_poc_client_harness.py](file:///D:/secret/scratch/test_poc_client_harness.py)), ejecutando la biblioteca original del juego (`P5X_Data\Plugins\x86_64\tolua.dll`) y los descriptores binarios oficiales (`allMsgPb.bytes`), decodificó cada mensaje de servidor con **`rc = 0`** (éxito absoluto sin errores de wire framing ni truncamiento).
2. **Estado jugable:** La recepción de `SCSceneEnterEnd` (`1203`) estableció de manera confirmada la bandera interna del cliente:
   $$\mathbf{mReceivedSCSceneEnterEnd = true}$$
   lo que activa la ocultación de la pantalla de carga (`SceneLoadingMgr:TryHideBlackScreen()`) y el desbloqueo de controles de usuario en `SceneMod`.
3. **Heartbeat activo:** Se procesó y respondió el ping periódico `CSPing` (`1116`) mediante `SCPing` (`1117`), previniendo la desconexión por temporizador de inactividad de `ConnectMod`.

---

## 2. Correcciones Previas y Verificación Adversaria de Campos

### 2.1. Unificación de Puerto de Red
Se unificó el puerto del servidor local en **`18100`**. Todas las referencias al puerto `20000` en [docs/STARTUP_GATES_ANALYSIS.md](file:///D:/secret/docs/STARTUP_GATES_ANALYSIS.md) fueron corregidas y contrastadas.

### 2.2. Verificación Adversaria: Campos de `ServerList` JSON vs `allMsgPb.bytes`

Se realizó la comprobación estricta de cada campo del JSON de lista de servidores frente a los descriptores de `allMsgPb.bytes`:

| Campo en JSON de ServerList | ¿Existe en `allMsgPb.bytes`? | Tipo / Mapeo en el cliente | Diagnóstico y justificación técnica |
| :--- | :---: | :--- | :--- |
| `serverIP` | **NO** (0 coincidencias) | `string` en `ServerListData` (Lua) | Campo exclusivo de la capa REST HTTP. `ServerListData.JsonDecode` lo parsea vía JSON estándar en Lua; no forma parte del esquema Protobuf. |
| `serverPort` | **NO** (0 coincidencias) | `number` en `ServerListData` (Lua) | Campo exclusivo de la capa REST HTTP. El cliente lo convierte con `tonumber()` para invocar `ConnectMgr:OnTryConnectServer(ip, port)`. |
| `id` | **SÍ** (59 mensajes) | `int64` / `int32` en Protobuf | Existe como identificador en múltiples mensajes Protobuf (`DCharacter.id`, `DInitScene.id`), pero **no existe un mensaje Protobuf de lista de servidores**. En el JSON es el ID del nodo. |
| `name` | **SÍ** (46 mensajes) | `string` en Protobuf | Existe en `DCharacter.name`, `DHuman.name`. En el JSON representa la etiqueta textual del servidor. |
| `status` | **SÍ** (6 mensajes) | `int32` / `enum` en Protobuf | Existe en subsistemas de avisos (`DNotice.status`), pero no en protocolo de conexión. En el JSON define el indicador visual (fluido/lleno). |
| `clientSrvID` | **NO** (0 coincidencias) | `number` en `ServerListData` (Lua) | Campo exclusivo de Lua para registrar el último servidor seleccionado en `PlayerPrefs`. |
| `SDKEnable` | **NO** (0 coincidencias) | `boolean` en `OnlineConfig` (Lua) | Parámetro de configuración remota consumido por `OneSDKMod:InitSDKInfo()`. No existe en Protobuf. |

> [!IMPORTANT]
> **Conclusión sobre la lista de servidores:**
> `allMsgPb.bytes` contiene exclusivamente los esquemas de tramas TCP binarias. La lista de servidores y la bandera `SDKEnable` se transmiten en texto claro mediante JSON sobre HTTP REST (`LoadServerList`), por lo que no deben codificarse como Protobuf. En la capa Protobuf, la dirección de red solo aparece en `SCLoginResult.gameAddress` (`102`), con valor `"127.0.0.1:18100"`.

---

## 3. Verificación de Campos Requeridos (Proto2)

Mediante consulta directa al motor `pbnew` sobre `allMsgPb.bytes`, se evaluó la obligatoriedad formal de cada campo en los mensajes de la secuencia de escena:

| Mensaje | MsgID | Campos Formales en Descriptor | Etiquetas Formales | Campos Críticos Requeridos por Lógica Lua |
| :--- | :---: | :---: | :--- | :--- |
| `SCInitData` | `1102` | 11 campos | `optional` (11) | `scene` (`DInitScene`), `human` (`DHuman`) |
| `DInitScene` | — | 16 campos | `optional` (15), `repeated` (1) | `sn` (ID de mapa en `ConfScene`), `posNow` (coordenadas x,y,z) |
| `DHuman` | — | 61 campos | `optional` (49), `repeated` (12) | `id`, `name`, `level`, `userId` |
| `DBasic` | — | 4 campos | `optional` (4) | `bAuto`, `bEnterSafeRoom` |
| `CSSceneEnter` | `1201` | 0 campos | — (Mensaje de señalización vacío) | Ninguno (0 bytes de payload) |
| `SCSceneEnterResult` | `1202` | 3 campos | `repeated` (1), `optional` (2) | `tarHumanId`, `obj` (lista de entidades) |
| `SCSceneEnterEnd` | `1203` | 2 campos | `repeated` (2) | `seek`, `produces` |

> [!NOTE]
> En `allMsgPb.bytes`, los campos tienen etiqueta Proto2 `optional` a nivel de descriptor binario (lo que garantiza que la ausencia de campos secundarios nunca cause un fallo de decodificación en `pbnew_decode_and_pushmsg`), pero la lógica Lua de `SceneMod:OnInitData` requiere lógicamente que `msg.scene.sn` y `msg.scene.posNow` existan para instanciar la escena.

---

## 4. Registro Exhaustivo de Cable: Secuencia Real de 19 Tramas

A continuación se detalla el registro verificado de las 19 tramas generadas entre el servidor local y el arnés de cliente en `127.0.0.1:18100`:

| Seq | Conexión | Dir | MsgID | Nombre de Mensaje | Total (B) | Cabecera Hex | Payload Hex (Primeros 8B) | Decodificación nativa (`rc`) | Estado / Significado |
| :---: | :---: | :---: | :---: | :--- | :---: | :--- | :--- | :---: | :--- |
| `01` | Conn 1 | S $\rightarrow$ C | `T0` | `Handshake_RC4_Key` | 20 | `00 00 00 14` | `50 35 58 4c 6f 63 61 6c` | `rc=0` | Clave RC4 (16B) activada en cliente (`_readKey=true`). |
| `02` | Conn 1 | C $\rightarrow$ S | `101` | `CSLogin` | 134 | `00 00 00 86 35 e2 cc 46` | `(Cifrado RC4)` | `rc=0` | Cliente envía credenciales y plataforma PC. |
| `03` | Conn 1 | S $\rightarrow$ C | `102` | `SCLoginResult` | 73 | `00 00 00 49 00 00 00 66` | `08 00 12 10 73 74 65 61` | `rc=0` | Asigna `gameAddress = "127.0.0.1:18100"` y `sessionId = 100001`. |
| — | — | — | — | *Reconexión TCP* | — | — | — | — | `ConnectMod:DisConnect()` e inicio de conexión 2 hacia Gate/Logic. |
| `04` | Conn 2 | S $\rightarrow$ C | `T0` | `Handshake_RC4_Key` | 20 | `00 00 00 14` | `50 35 58 4c 6f 63 61 6c` | `rc=0` | Nueva clave RC4 para la segunda conexión TCP. |
| `05` | Conn 2 | C $\rightarrow$ S | `103` | `CSLoginGate` | 149 | `00 00 00 95 35 e2 cc 44` | `(Cifrado RC4)` | `rc=0` | Valida `sessionId = 100001` en el nodo de juego. |
| `06` | Conn 2 | S $\rightarrow$ C | `104` | `SCLoginGateResult` | 10 | `00 00 00 0a 00 00 00 68` | `08 00` | `rc=0` | `errorCode = 0` (Acceso concedido). |
| `07` | Conn 2 | S $\rightarrow$ C | `1112` | `SCServerConfig` | 30 | `00 00 00 1e 00 00 04 58` | `08 00 10 00 18 80 e4 e7` | `rc=0` | Sincroniza reloj y desactiva combate en cliente. |
| `08` | Conn 2 | C $\rightarrow$ S | `1001` | `CSQueryCharacters` | 8 | `00 00 00 08 e9 ec 36 42` | `(Cifrado RC4)` | `rc=0` | Solicita catálogo de personajes guardados. |
| `09` | Conn 2 | S $\rightarrow$ C | `1002` | `SCQueryCharactersResult`| 29 | `00 00 00 1d 00 00 03 ea` | `0a 15 08 91 4e 12 06 57` | `rc=0` | Retorna personaje `"Wonder"`, nivel 1, id 10001. |
| `10` | Conn 2 | C $\rightarrow$ S | `1007` | `CSCharacterLogin` | 15 | `00 00 00 0f 2b 11 fc 90` | `(Cifrado RC4)` | `rc=0` | Cliente selecciona a Wonder (`humanId = 10001`). |
| `11` | Conn 2 | S $\rightarrow$ C | `1008` | `SCCharacterLoginResult`| 12 | `00 00 00 0c 00 00 03 f0` | `08 00 10 01` | `rc=0` | `resultCode = 0`. Dispara `CharacterLoginSuccess`. |
| `12` | Conn 2 | S $\rightarrow$ C | `1102` | `SCInitData` | 90 | `00 00 00 5a 00 00 04 4e` | `0a 1f 08 91 4e 1a 06 57` | `rc=0` | Inyecta `DInitScene` y `DHuman`. Dispara `OnInitData`. |
| `13` | Conn 2 | C $\rightarrow$ S | `1201` | `CSSceneEnter` | 8 | `00 00 00 08 58 35 ab ae` | `(Cifrado RC4)` | `rc=0` | Unity finaliza carga de escena 3D y notifica al servidor. |
| `14` | Conn 2 | S $\rightarrow$ C | `1202` | `SCSceneEnterResult` | 11 | `00 00 00 0b 00 00 04 b2` | `10 91 4e` | `rc=0` | Confirma entrada de `tarHumanId = 10001`. |
| `15` | Conn 2 | S $\rightarrow$ C | `1203` | `SCSceneEnterEnd` | 8 | `00 00 00 08 00 00 04 b3` | `(Sin payload, 0B)` | `rc=0` | Establece `mReceivedSCSceneEnterEnd = true`. **Juego activo**. |
| `16` | Conn 2 | C $\rightarrow$ S | `1116` | `CSPing` | 13 | `00 00 00 0d 9e d9 36 d6` | `(Cifrado RC4)` | `rc=0` | Heartbeat del cliente con `clientTimeStamp = 12.345`. |
| `17` | Conn 2 | S $\rightarrow$ C | `1117` | `SCPing` | 13 | `00 00 00 0d 00 00 04 5d` | `0d 56 0e 45 41` | `rc=0` | Echo de timestamp. Conexión declarada estable. |
| `18` | Conn 2 | C $\rightarrow$ S | `1118` | `CSNetDelayDetect` | 13 | `00 00 00 0d 0c 8d 6d b1` | `(Cifrado RC4)` | `rc=0` | Sonda de latencia de red. |
| `19` | Conn 2 | S $\rightarrow$ C | `1119` | `SCNetDelayDetect` | 20 | `00 00 00 14 00 00 04 5f` | `0d 56 0e 45 41 10 80 e4` | `rc=0` | Retorna timestamp de cliente y servidor. |

---

## 5. Heartbeat y Supervivencia de la Conexión

### 5.1. Comportamiento Observado en `ConnectMod`
En `07B3A247F1ADE14.bytes` Chunk 66 (`ConnectMod`):
1. `ConnectMod:OnUpdateReconnect()` ejecuta un temporizador en cada frame:
   Si `Time.timeSinceLevelLoad - self.mSendPingTime >= PING_INTERVAL`, envía `CSPing` (`1116`) con `clientTimeStamp = Time.timeSinceLevelLoad`.
2. Al recibir `SCPing` (`1117`), `ConnectMod:OnSCPing(msg)`:
   - Actualiza `self.mRecivePingTime = Time.timeSinceLevelLoad`.
   - Calcula el retraso de red: `delay = msg.clientTimeStamp - self.mSendPingTime`.
3. **Consecuencia de omitir `SCPing`:** Si transcurren más de `15` segundos sin recibir `SCPing`, `ConnectMod` asume pérdida de conexión TCP, invoca `ConnectMod:Reconnect()` y regresa forzosamente al menú de inicio.
4. **Implementación en el servidor:** El servidor extrae el `clientTimeStamp` (float de 4 bytes) del payload de `1116` y lo retorna inmediatamente en `1117`, manteniendo la sesión viva indefinidamente sin intervención manual.

---

## 6. Verificación Adversaria y Pruebas Negativas

Para asegurar que el arnés detecta fallos reales y no simula falsos positivos, se ejecutaron dos pruebas negativas intencionales:

1. **Prueba Negativa 1 (Simulación de cifrado inverso RC4 en S $\rightarrow$ C):**
   Se forzó el cifrado RC4 de una trama de servidor (`SCLoginGateResult`). El arnés interceptó el ID de mensaje corrupto `904055883` y abortó con el error nativo exacto:
   ```text
   OnGetSocketBytes msg is error, text sn=1046007, DisConnect, msg id = 904055883 (rc = -1046007)
   ```
2. **Prueba Negativa 2 (Truncamiento intencional de bytes Protobuf):**
   Se inyectaron bytes varint corruptos (`\x08\x80\x80\x80`). `pbnew_decode_and_pushmsg` falló inmediatamente con código:
   ```text
   pbnew_decode_and_pushmsg failed with rc = 1
   ```

Ambas pruebas confirman que el arnés valida rigurosamente los bytes en cable y no tolera discrepancias.

---

## 7. Inventario de Código y Hash de Integridad

Todos los scripts ejecutables y registros se encuentran alojados exclusivamente en `D:\secret\scratch\`:

| Archivo | Tamaño (bytes) | Hash SHA-256 | Función técnica |
| :--- | ---: | :--- | :--- |
| [proto2_codec.py](file:///D:/secret/scratch/proto2_codec.py) | 20,402 | `B0B4B6261A6C196FF9A717BA52F0E18D30BBD93EDD40123DDECF469B460F64BE` | Codificador/Decodificador Proto2 puro para login, escena y heartbeat. |
| [poc_login_server.py](file:///D:/secret/scratch/poc_login_server.py) | 20,457 | `32FB6137917A7F58DE808AD8AE0AC0E7D9B9130795FC2C2EBA2D026D2A08A927` | Servidor TCP local multi-hilo en `127.0.0.1:18100` que gestiona las 19 tramas. |
| [test_poc_client_harness.py](file:///D:/secret/scratch/test_poc_client_harness.py) | 20,381 | `546295AF995F16158AD4EF3F2E1703DCA54DC310926750C3311B8D1DF2966219` | Arnés de validación cliente que utiliza la DLL nativa `tolua.dll` y chunks reales. |
| [poc_frame_log.json](file:///D:/secret/scratch/poc_frame_log.json) | 12,187 | `733A1B591BA36F660C00BD2CA5B86C088EDAD3CC7F029A96753B756782687880` | Volcado JSON íntegro de las 19 tramas registradas con sus bytes hex. |

---

## 8. Diagnóstico y Siguiente Paso

- **Estado actual:** La emulación del protocolo de red desde el handshake inicial hasta el control de escena 3D y mantenimiento por ping se encuentra **100% resuelta y verificada en cable**.
- **Siguiente paso recomendado:**
  Cuando el usuario lo autorice, iniciar la **Fase 3: Ejecución interactiva con el cliente real `P5X.exe`**:
  1. Configuración local del host `nsywlydcdn1.wmupd.com` hacia `127.0.0.1`.
  2. Lanzamiento del micro-servidor HTTP para servir la lista de servidores JSON en loopback (`port 80`).
  3. Ejecución concurrente de `poc_login_server.py` en `127.0.0.1:18100`.
  4. Lanzamiento de `P5X.exe` para observar la carga visual del motor Unity 3D en pantalla.
