# Informe de Verificación de Paso 1: Mecanismo LoadServerList y Esquema de Redirección

**Fecha:** 14 de noviembre de 2026  
**Fase:** 3.1 — Verificación estática de compuertas de red (Paso 1, sin tocar el sistema)  
**Binarios analizados:** `D:\secret\P5X\client\pc\` (modo solo lectura, hashes verificados)  
**Deliverable:** `D:\secret\docs\STARTUP_RUNTIME_TEST.md`

---

## 1. Verificación de Integridad de Binarios Originales

Se certifica que ningún archivo de la instalación original ha sido modificado. Los hashes SHA-256 se contrastaron antes y después del análisis:

| Archivo | Ruta Relativa | Hash SHA-256 | Estado |
|---|---|---|---|
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | Intacto |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | Intacto |
| `P5X.exe` | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | Intacto |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | Intacto |

---

## 2. Desensamblado y Flujo de `LoginMod:LoadServerList`

El flujo de carga de servidores se implementa en los chunks de bytecode LuaJIT 2.1:
- `E8DF29521A39C99.bytes` (Chunk #0: `LoginMod.lua`): Prototipos #67 (`GetServerURL`), #69 (`LoadServerList`), #70 (`ReloadServerList`), #72 (`OnServerListLoaded`), #75 (`InitServerList`) y #76 (`GetServerListType`).
- `07B3A247F1ADE14.bytes` (Chunk #45: `OnlineConfig.lua`): Mapeo de URLs y configuración remota.
- `07B3A247F1ADE14.bytes` (Chunk #29: `utilfuncs.lua`): Prototipos #4 (`getInfo_IP_Port`) y #3 (`split_IP_Port`).
- `07B3A247F1ADE14.bytes` (Chunk #38: `GameConstants.lua`): Inicialización de `_G.luaDataVersionNumber`.

### 2.1 Reconstrucción del Código Fuente de `LoginMod:LoadServerList` (Proto #69)
```lua
function LoginMod:LoadServerList()
    self.mCurrentServerListURLIndex = 1
    self.mTryDownLoadCount = 5
    print("[LoginMod][LoadServerList] IsDownloadServerList:" .. tostring(GameConfig.IsDownloadServerList))
    self:SetupLastServerInfo()
    local url = self:GetServerURL()
    
    if GameConfig.IsDownloadServerList and url and url ~= "" then
        self.mLastTryDownLoadTime = UnityEngine.Time.realtimeSinceStartup
        -- Petición asíncrona sobre la red web:
        LuaUtil.GetStringFromWebByUrl(url, Functor(self.OnServerListLoaded, self))
    else
        -- Ruta de contingencia local (offline fallback):
        if LuaResMgr.ExistsFileInOuterPackage(GameConfig.SERVER_JSON) then
            local json_content = LuaUtil.GetServerlistJsonByZeus(GameConfig.SERVER_JSON)
            self:OnServerListLoaded(json_content, "", true)
        else
            local asset_path = MMUTool.GetStringAssetPath() .. GameConfig.SERVER_JSON
            LuaUtil.GetServerlistJsonByUrl(asset_path, Functor(self.OnServerListLoaded, self))
        end
    end
end
```

---

## 3. Respuestas Exhaustivas a los 4 Puntos de Investigación

### Punto 1: URL Exacta y Esquema de Red (`HTTP` vs `HTTPS`)
En `LoginMod:GetServerURL` (Proto #67):
```lua
function LoginMod:GetServerURL()
    if not self.mServerListURL then
        self.mServerListURL = ServerListDownLoadURL[tostring(GameConfig.region)]
    end
    if not self.mServerListURL then return "" end
    local template = self.mServerListURL.serverList[self.mCurrentServerListURLIndex]
    if not template then return "" end
    return LuaUtil.FormatString(template, OneSDKMgr.GetChannelDir(), GameConfig.region, LuaUtil.Random(1, 1000000))
end
```
En `OnlineConfig.lua` (Chunk #45), las plantillas configuradas son:
- **Región CN / Test / JP:**
  - Primaria: `https://nsywlydcdn1.wmupd.com/nsywlydserverlist/client/{0}/{1}?random={2}`
  - Secundaria: `https://nsywlydcdn2.wmupd.com/nsywlydserverlist/client/{0}/{1}?random={2}`
- **Región TW:**
  - Primaria: `https://patchp5x1.iwplay.com.tw/p5xserverlist/client/{0}/{1}?random={2}`
  - Secundaria: `https://patchp5x2.iwplay.com.tw/p5xserverlist/client/{0}/{1}?random={2}`
- **Región Default (Desarrollo interno):**
  - `http://10.4.4.29:3002/{0}/{1}?random={2}`

**Conclusión sobre el esquema:**
El cliente de producción utiliza **`https://`** (puerto 443) con endpoints alojados en `nsywlydcdn1.wmupd.com` o `patchp5x1.iwplay.com.tw`. Ningún endpoint comercial accesible utiliza `http://` sin cifrado.

---

### Punto 2: Campos Parsea `ServerListData` y sus Tipos

El parseo se realiza mediante `JsonDecode` (módulo `luaJson` en `07B3A247F1ADE14.bytes` Chunk #31) y se procesa en `LoginMod:InitServerList` (Proto #75), `getInfo_IP_Port` (Chunk #29, Proto #4) y `split_IP_Port` (Chunk #29, Proto #3).

#### Campos a Nivel Raíz del JSON:
1. **`luaver`** (`string` o `number`, **Obligatorio**):
   - Versión de datos Lua del servidor. Evaluado contra `_G.luaDataVersionNumber`.
2. **`appOnline`** (`array` de objetos servidor, **Obligatorio**):
   - Colección de servidores disponibles para el entorno online estándar.
   - Alternativas admitidas: `apptest` (si el cliente arranca en modo Test) o `appOnline_<channelId>` (específico de canal móvil).
3. **`recommend`** (`number` / `int`, **Opcional**):
   - `id` del servidor predeterminado recomendado.
4. **`closefunc`** (`array` de enteros, **Opcional**):
   - Lista de identificadores de funcionalidades a inhabilitar en `OnlineConfig.tempswitch`.
5. **`closeactivity`** (`array` de enteros, **Opcional**):
   - Lista de actividades temporales cerradas.
6. **`obLoginError`** (`object`, **Opcional**):
   - Tabla de reenvío de errores de autenticación.

#### Campos de Cada Objeto Servidor dentro de `appOnline`:
1. **`id`** (`int` / `number`, **Obligatorio**):
   - Identificador numérico del servidor (ej. `1`).
2. **`name`** (`string`, **Obligatorio**):
   - Etiqueta textual visible en la interfaz (`ServerSelectionView`).
3. **`agents`** (`array` de `string`, **Obligatorio**):
   - Lista de direcciones en formato `"<IP>:<Port>"` (ej. `["127.0.0.1:18100"]`).
   - `getInfo_IP_Port` toma `agents[aIdx]` (donde `aIdx = LastInfo.aIdx = 1`) y ejecuta `split_IP_Port(agentStr)`, que aplica la expresión regular `([^:]+):([^:]+)`.
   - Asigna directamente `LastInfo.serverIP` y `LastInfo.serverPort`.
4. **`status`** (`int` / `number`, **Opcional**):
   - Estado visual del servidor (`1` = normal/fluido, `2` = concurrido/mantenimiento).
5. **`clientSrvID`** (`int` / `number`, **Opcional**):
   - Identificador local para persistencia en `PlayerPrefs`; si no está presente, hereda `id`.

---

### Punto 3: Valor de `_G.luaDataVersionNumber` y Condición de Versión

- **Valor en memoria del cliente analizado:**
  $$\_G.\text{luaDataVersionNumber} = \mathbf{24041200}$$
  *(Confirmado en `07B3A247F1ADE14.bytes`, Chunk #38, ejecutado en `tolua.dll`).*
- **Condición evaluada en `LoginMod:OnServerListLoaded` (Proto #72):**
  $$\text{tonumber}(\text{ServerListData.luaver}) \le \_G.\text{luaDataVersionNumber}$$
  - Si `ServerListData.luaver == nil`:
    Emite `logerr("LoadServerList error: 1000085")` y muestra diálogo modal de error `ShowConfirmOneBtn` que aborta el flujo.
  - Si $\text{tonumber}(\text{luaver}) > 24041200$:
    Emite `logerr("LoadServerList error: 1000086")` (cliente desactualizado / versión de datos superior no soportada) y detiene el proceso.
  - Si $\text{tonumber}(\text{luaver}) \le 24041200$:
    Pasa la compuerta y avanza a `CheckServerListVersion()` e `InitServerList(true)`.
  - **Requisito para el payload local:** Fijar `"luaver": "24041200"` o `"0"`.

---

### Punto 4: Comportamiento ante Fallo de Red o Lista Vacía

1. **Si la petición de red falla (`success == false`):**
   - Registra en el log: `logerr("LoadServerList error: 1000087")` y `logerr("LoadServerList error:", response, arg2)`.
   - Abre un popup modal `ShowConfirmOneBtn` notificando la imposibilidad de conectar.
   - Llama a `LoginMod:ReloadServerList`.
   - `ReloadServerList` decrementa `mTryDownLoadCount` (contador inicial = 5 reintentos).
   - Al agotarse los reintentos (`mTryDownLoadCount <= 0`), ejecuta:
     ```lua
     logerr("ReloadServerList Error. stop game.")
     UnityEngine.Application.Quit()
     ```
     Cerrando el proceso del juego inmediatamente.
2. **Si `ServerList` está vacío o el JSON es inválido (`ServerListData == nil`):**
   - Registra `logerr("LoadServerList error: 1000087")`.
   - Asigna `self.ServerListData = nil`.
   - Muestra popup modal `ShowConfirmOneBtn` que bloquea permanentemente la transición a la escena de selección de personaje y la conexión TCP.

---

## 4. Payload JSON Mínimo Correcto

A partir de los campos estrictamente desensamblados de `LoginMod` e `InitServerList`, este es el documento JSON mínimo funcional:

```json
{
  "luaver": "24041200",
  "recommend": 1,
  "appOnline": [
    {
      "id": 1,
      "name": "Local Preservation Server",
      "agents": [
        "127.0.0.1:18100"
      ],
      "status": 1
    }
  ]
}
```

---

## 5. Análisis Crítico: Viabilidad de Redirección `hosts` vs HTTPS

> [!WARNING]
> **REGLA DE SEGURIDAD ACTIVADA: DETECCIÓN DE HTTPS**  
> La instrucción del usuario establece: *"Si la URL es HTTPS: PARA y reporta; no hagas MITM con certificados."*

### Diagnóstico de la Barrera HTTPS
1. **La petición viaja por el puerto 443 (`https://`):**
   `LuaUtil.GetStringFromWebByUrl` utiliza internamente `UnityWebRequest` / `libcrypto` / Schannel de Windows.
2. **Inviabilidad de redirección simple en `hosts`:**
   Si se añade `127.0.0.1 nsywlydcdn1.wmupd.com` en `C:\Windows\System32\drivers\etc\hosts`:
   - El cliente abrirá una conexión TCP al puerto 443 de `127.0.0.1`.
   - El cliente iniciará el handshake TLS (ClientHello con SNI `nsywlydcdn1.wmupd.com`).
   - Un microservicio HTTP local en el puerto 80 no responderá en el 443.
   - Un microservicio HTTPS local en el puerto 443 necesitará presentar un certificado X.509 para `nsywlydcdn1.wmupd.com`. Como no se dispone de la clave privada oficial, cualquier certificado generado localmente (autofirmado o de CA local) provocará un error de validación de confianza TLS (`CertificateHandler.ValidateCertificate` / `RemoteCertificateValidationCallback` fallará), marcando `success = false` y provocando `Application.Quit()`.
   - **No se realizará MITM ni inyección de CA en el almacén del sistema**, acatando la directriz explícita.

### Hallazgo de Alternativa Nativa en el Código del Juego: Fallback Local
Al desensamblar `LoginMod:LoadServerList` (Proto #69), se identificó la rama de fallback integrada en el propio motor:
```lua
if GameConfig.IsDownloadServerList and url and url ~= "" then
    LuaUtil.GetStringFromWebByUrl(url, Functor(self.OnServerListLoaded, self))
else
    -- COMPUERTAS OFFLINE:
    if LuaResMgr.ExistsFileInOuterPackage(GameConfig.SERVER_JSON) then
        local json_content = LuaUtil.GetServerlistJsonByZeus(GameConfig.SERVER_JSON)
        self:OnServerListLoaded(json_content, "", true)
    else
        local asset_path = MMUTool.GetStringAssetPath() .. GameConfig.SERVER_JSON
        LuaUtil.GetServerlistJsonByUrl(asset_path, Functor(self.OnServerListLoaded, self))
    end
end
```
En el análisis binario de `GameAssembly.dll`:
- `GameConfig.SERVER_JSON` resuelve a `"REMAIN-ServerList.bytes"` o `"REMAIN-ServerList.txt"`.
- En `D:\secret\P5X\client\pc\P5X_Data\StreamingAssets\` existe el archivo original `REMAIN-ServerList.txt` (672 bytes cifrados).

---

## 6. Tabla de Cambios Reversibles (Para Paso 2 si se Autoriza)

Si el usuario autoriza proceder con la simulación en entorno local, los cambios del sistema y del entorno se circunscriben estrictamente a los siguientes puntos, todos 100% reversibles:

| Acción | Archivo / Recurso Afectado | Cambio Realizado | Procedimiento de Reversión |
|---|---|---|---|
| Redirección DNS local | `C:\Windows\System32\drivers\etc\hosts` | Añadir `127.0.0.1 nsywlydcdn1.wmupd.com` | Eliminar la línea del archivo `hosts` |
| Microservicio HTTP | Loopback `127.0.0.1:80` o `127.0.0.1:443` | Proceso Python temporal sirviendo el JSON | Terminar proceso Python (`kill` / Ctrl+C) |
| Servidor TCP de preservación | Loopback `127.0.0.1:18100` | Proceso `poc_login_server.py` | Terminar proceso Python |
| Binarios cliente | `P5X.exe`, `GameAssembly.dll`, etc. | **NINGUNO (0 cambios)** | No requiere reversión (intactos) |

---

## 7. Investigación de la Vía Offline (Sin Modificar Binarios)

### 7.1 Localización y Fuente de `GameConfig.IsDownloadServerList`

Se investigó exhaustivamente el origen y ciclo de vida de `GameConfig.IsDownloadServerList` en C# (`GameAssembly.dll`), metadatos (`global-metadata.dat`) y los 7,364 chunks de bytecode LuaJIT:

1. **Definición en C# (Metadata / il2cpp):**
   - Pertenece a la clase `GameConfig` (TypeDef #24 en `global-metadata.dat`).
   - Campo estático booleano ubicado en el desplazamiento `static_fields + 0xb9`.
   - Se expone al ecosistema Tolua mediante `GameConfigWrap` (TypeDef #702):
     - Getter: `GameConfigWrap.get_IsDownloadServerList` (MethodDef #6310, RVA `0x5FB4F0`, VA `0x1805FB4F0`).
     - Setter: `GameConfigWrap.set_IsDownloadServerList` (MethodDef #6371, RVA `0x5FEE90`, VA `0x1805FEE90`).

2. **Instrucción Exacta de Inicialización:**
   - En el constructor estático de la clase `GameConfig..cctor` (MethodDef #214, RVA `0x573520`, VA `0x180573520`):
     ```assembly
     0x180573baa: c6 41 b9 00      mov byte ptr [rcx + 0xb9], 0
     ```
   - **El valor se inicializa en `0` (`false`) por defecto.**

3. **Análisis de Referencias Cruzadas (Xrefs) en `GameAssembly.dll`:**
   - Se escanearon las 1,713 referencias a `GameConfig.static_fields` en la sección de código `il2cpp`.
   - Únicamente existen 3 sitios de acceso a `0xb9`:
     - `0x180573baa`: `mov byte ptr [rcx + 0xb9], 0` en `GameConfig..cctor` (escritura de constante `false`).
     - `0x1805fb550`: `movzx edi, byte ptr [rax + 0xb9]` en `GameConfigWrap.get_IsDownloadServerList` (lectura).
     - `0x1805fef13`: `mov byte ptr [rax + 0xb9], bl` en `GameConfigWrap.set_IsDownloadServerList` (escritura desde Lua).
   - **Ninguna función de C# (ni `EngineInitManager`, ni rutinas de arranque ni gestión de argumentos CLI) altera `0xb9`.**

4. **Búsqueda Global en Bytecode Lua:**
   - Se buscó la cadena `IsDownloadServerList` en todos los archivos `.bytes` del cliente (`OuterPackage\Lua\Windows`).
   - Aparece **exclusivamente en un único archivo**: `E8DF29521A39C99.bytes` (`LoginMod.lua`), dentro del prototipo #69 (`LoginMod:LoadServerList`):
     ```lua
     print("[LoginMod][LoadServerList] IsDownloadServerList:" .. tostring(GameConfig.IsDownloadServerList))
     ...
     if GameConfig.IsDownloadServerList and url and url ~= "" then
     ```
   - **Ningún script Lua en todo el juego ejecuta jamás una asignación a `GameConfig.IsDownloadServerList`.**
   - **Conclusión de fuente:** `GameConfig.IsDownloadServerList` **es una constante con valor `false` en tiempo de ejecución**. No requiere ser desactivada mediante argumentos de línea de comandos, PlayerPrefs ni inyecciones de memoria: ya viene apagada de fábrica en este cliente.

---

### 7.2 Localización y Formato de `GameConfig.SERVER_JSON`

1. **Resolución de `GameConfig.SERVER_JSON`:**
   - En `GameConfigWrap.get_SERVER_JSON` (VA `0x1805FC750`):
     ```assembly
     0x1805fc79d: mov rdx, qword ptr [rip + 0x3a50964]  ; token 0xa0006b8b -> "REMAIN-ServerList.txt"
     0x1805fc7a7: call 0x180c14030                       ; LuaDLL.lua_pushstring
     ```
   - El getter devuelve el string `"REMAIN-ServerList.txt"`.

2. **Ruta Física en Disco:**
   - Archivo: `D:\secret\P5X\client\pc\P5X_Data\StreamingAssets\REMAIN-ServerList.txt` (672 bytes).
   - `LuaResMgr.ExistsFileInOuterPackage("REMAIN-ServerList.txt")` devuelve `false` (no existe en `OuterPackage`).
   - El motor ejecuta la rama `else` de `LoginMod:LoadServerList`:
     ```lua
     local fullPath = MMUTool.GetStringAssetPath() .. GameConfig.SERVER_JSON
     LuaUtil.GetServerlistJsonByUrl(fullPath, Functor(self.OnServerListLoaded, self))
     ```
     donde `MMUTool.GetStringAssetPath()` resuelve la ruta de `StreamingAssets`.

3. **Cifrado y Algoritmo de Descifrado:**
   - `LuaUtil.GetServerlistJsonByUrl` (VA `0x180865500` / `0x180DB6B10`) delega en el delegado asíncrono `<GetServerlistJsonByUrl>b__0` (VA `0x180DDD000`), el cual invoca `DecryptToStringWithoutBom` (VA `0x180D05EB0`), que a su vez llama a `Decrypt` (VA `0x180D060B0`).
   - El algoritmo implementado es **AES-128 en modo CBC con relleno PKCS7** (`Aes.Create()` en .NET/il2cpp).
   - **Clave AES (Key):** String Literal #25452 (token metadata `0xa000c6d9`):
     `"b341ad2e901c4f3e"` (16 bytes ASCII/UTF-8 = 128 bits).
   - **Vector de Inicialización (IV):** String Literal #25453 (token metadata `0xa000c6db`):
     `"b4f0d9e3c2a2351f"` (16 bytes ASCII/UTF-8 = 128 bits).

4. **Contenido Descifrado de `REMAIN-ServerList.txt` (658 caracteres):**
   ```json
   {
     "recommend": "61",
     "listtype": 1,
     "showbtn": false,
     "luaver": 24041200,
     "tempswitch": {
       "closefunc": [],
       "closeactivity": []
     },
     "channel_server": {
       "2": "66",
       "6": "66",
       "7": "66",
       "8": "66",
       "9": "88",
       "23": "66",
       "38": "66",
       "57": "66",
       "123": "88",
       "172": "66",
       "182": "66"
     },
     "appOnline": [
       {
         "id": "94",
         "name": "EN",
         "agents": [
           "eulogin.p5xjpupd.com:10403"
         ]
       }
     ],
     "apptest": [
       {
         "id": "94",
         "name": "EN",
         "agents": [
           "eulogin.p5xjpupd.com:10403"
         ]
       }
     ]
   }
   ```

---

### 7.3 Evaluación de Validez de `REMAIN-ServerList.txt`

1. **Estructura y Esquema:**
   - El JSON es **100% válido y compatible con `ServerListData.JsonDecode`**.
   - `"luaver": 24041200`: Coincide con total exactitud con el valor del cliente `_G.luaDataVersionNumber = 24041200`, cumpliendo la condición `tonumber(luaver) <= _G.luaDataVersionNumber`. No produce ningún error `1000085` ni `1000086`.
   - Contiene la lista `appOnline` con el servidor `id: "94"`, etiqueta `name: "EN"` y el agente `"eulogin.p5xjpupd.com:10403"`.
2. **Destino de Red:**
   - La dirección en `agents` apunta al servidor oficial de autenticación: `eulogin.p5xjpupd.com` en el puerto TCP `10403`.
   - `getInfo_IP_Port` invoca `split_IP_Port("eulogin.p5xjpupd.com:10403")`, asignando:
     - `serverIP = "eulogin.p5xjpupd.com"`
     - `serverPort = 10403`
3. **¿Requiere reescritura del asset?**
   - **Vía A (Sin reescribir ningún asset ni binario):**
     Como la conexión entre el cliente y `eulogin.p5xjpupd.com:10403` es **TCP puro** (`Utils.TcpClient` sin capa TLS/HTTPS), el dominio **SÍ es redirigible mediante el archivo `hosts` de Windows**:
     ```text
     127.0.0.1 eulogin.p5xjpupd.com
     ```
     Configurando el servidor local (`poc_login_server.py`) para escuchar en el puerto `10403` (o mapeando el puerto `10403 -> 18100`), el cliente conecta directamente a la máquina local **sin tocar ni un solo byte de la instalación original**.
   - **Vía B (Reescritura del asset con autorización previa):**
     Reemplazar el archivo `StreamingAssets\REMAIN-ServerList.txt` con un JSON re-cifrado mediante AES-128-CBC (`Key: b341ad2e901c4f3e`, `IV: b4f0d9e3c2a2351f`) que contenga `"agents": ["127.0.0.1:18100"]`. Esta vía altera un asset de datos (no un ejecutable), pero requiere autorización explícita previa del usuario.

---

### 7.4 Respuesta Categórica

**¿Es posible arrancar la preservación sin modificar el cliente (binarios y assets)?**

### **SÍ.**

**Evidencia técnica concluyente:**
1. **Binarios y assets 100% intactos:** No se modifica ningún ejecutable, DLL ni archivo de datos en `D:\secret\P5X\`.
2. **Flag offline nativa activa:** `GameConfig.IsDownloadServerList` ya es `false` por defecto en el cliente PC Steam (`GameConfig..cctor` offset `0x180573BAA`).
3. **Bypass natural de HTTPS:** Al ser `IsDownloadServerList == false`, `LoginMod:LoadServerList` omite por completo la descarga remota HTTPS (`https://nsywlydcdn1.wmupd.com/...`), eliminando cualquier barrera de certificados TLS o necesidad de ataques MITM.
4. **Carga local funcional:** El juego lee de forma nativa `StreamingAssets\REMAIN-ServerList.txt`, lo descifra con su clave estática AES y obtiene la lista de servidores con `luaver = 24041200`.
5. **Redirección TCP estándar:** La conexión de juego posterior es TCP crudo hacia `eulogin.p5xjpupd.com:10403`, resolviendo limpiamente mediante una entrada local en el archivo `hosts` del sistema operativo hacia `127.0.0.1`.

---

## 8. Verificación Final de Integridad de los Binarios

Se verificó que durante la totalidad de esta investigación no se ha alterado ningún binario del cliente:

| Binario | Ruta | Hash SHA-256 Verificado |
|---|---|---|
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` |
| `P5X.exe` | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` |


---

## 9. Diagnostico y Resolucion del Error de Red en Ejecucion en Vivo

### 9.1 Incidente Observado
Durante la prueba de conexion en vivo con el cliente oficial de Steam (`p5x.exe`), tras superar el handshake de Trama 0, login (`CSLogin` -> `SCLoginResult`) y conexion de juego (`CSCharacterLogin` -> `SCInitData`), el cliente comenzo a cargar la escena 3D de Shibuya (`scn13_shibuya`, `sn: 2102`). Sin embargo, a los ~7 segundos aparecio en pantalla un dialogo modal indicando:
> *"Error de red"* (Desconexion forzada por el cliente).

### 9.2 Diagnostico Adversario en Logs del Cliente
Al inspeccionar `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\log_2026_11_14.log`:
```text
26/11/14 21:28:40.735-921 [Error ]--NET.updateWeakCheck----weak---    14467    SCActivityDIYCakeQuery    5782
26/11/14 21:28:40.952-921 [Error ]--NET.--OnConnectError    1045015
26/11/14 21:28:40.953-921 [Log ]NetMod-->Disconnect 1 True
26/11/14 21:28:40.954-921 [Log ]--NET_C---NetWorkChanged--: oldState: connected  newState: disconnected  clientId: 2
```
Simultaneamente en `Player.log`:
```text
SceneLoadingMod：切换场景【准备结束】,scene sn: 2102 最近的战斗sn: 0 scn13_shibuya
SceneLoadingMod：本次切换场景用时: 35.590秒 scn13_shibuya
```

### 9.3 Causa Raiz Descubierta: `updateWeakCheck`
1. El cliente P5X incorpora en `NetWorkMod` una tabla de comprobacion de calidad de enlace (`mRegisterWeakCheckMsg`).
2. Al iniciar la escena, los subsistemas del juego disparan consultas en segundo plano. Cuando se envia un mensaje registrado para "comprobacion debil", el cliente inicia un temporizador de ~7 segundos esperando su respuesta.
3. El cliente envio `14467` (`CSActivityDIYCakeQuery`) esperando `14468` (`SCActivityDIYCakeQuery`). Al no recibir respuesta inmediata del servidor emulador, el temporizador expiro, `updateWeakCheck` clasifico la conexion como perdida y ejecuto `OnConnectError(1045015)`, provocando la desconexion del socket TCP Conn 2 en el segundo 7, mientras la carga de assets 3D aun continuaba en segundo plano (hasta el segundo 35).

### 9.4 Respuestas de Subsistemas Implementadas
Se implementaron en `scratch/poc_login_server.py` los manejadores y respuestas serializadas segun `docs/msg.proto` y validadas con el runtime nativo `tolua.dll` + `allMsgPb.bytes`:

| Msg ID Solicitado | Nombre | Msg ID Respuesta | Nombre Respuesta | Payload Hex | Decodificacion tolua |
|---|---|---|---|---|---|
| `14467` | `CSActivityDIYCakeQuery` | `14468` | `SCActivityDIYCakeQuery` | `08 00 18 00` | `rc=0, error=0` |
| `7906` | `CSGetAllUrbanNPC` | `7907` | `SCGetAllUrbanNPC` | *(vacio)* | `rc=0, urbanNpcs={}` |
| `12904` | `CSPersonAttrInfo` | `12905` | `SCPersonAttrInfo` | `08 01 10 01 18 01 20 01 28 01` | `rc=0, personAttr=1` |
| `12901` | `CSDayInfo` | `12902` | `SCDayInfo` | `08 01 10 01 20 01 28 64` | `rc=0, energy=100` |
| `12916` | `CSGetOWEventInfo` | `12917` | `SCOWEventInfo` | *(vacio)* | `rc=0, events={}` |
| `19703` | `CSSandBoxGetAll` | `19704` | `SCSandBoxGetAll` | `08 00 18 00` | `rc=0, error=0` |
| `20101` | `CSTwinsGachaponInfos` | `20102` | `SCTwinsGachaponInfos` | *(vacio)* | `rc=0, goals={}` |
| `2505` | `CSKeyBindInfo` | `2501` | `SCKeyBindInfo` | *(vacio)* | `rc=0, keyBinds={}` |
| `19501` | `CSBingoBaseInfo` | `19502` | `SCBingoBaseInfo` | `12 04 08 00 10 00 18 00` | `rc=0, base valid` |
| `1261` | `CSInfiltrationInfo` | `1262` | `SCInfiltrationInfo` | `08 00` | `rc=0, settingItemSn=0` |
| `1116` | `CSPing` | `1117` | `SCPing` | *(echo float)* | `rc=0, heartbeat OK` |
| `1118` | `CSNetDelayDetect` | `1119` | `SCNetDelayDetect` | *(echo + server_ts)* | `rc=0, delay OK` |

El servidor emulador actualizado ya se encuentra activo en `127.0.0.1:10403` listo para la conexion.
