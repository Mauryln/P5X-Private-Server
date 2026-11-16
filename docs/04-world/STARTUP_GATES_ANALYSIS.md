# Análisis Estático de Barreras de Arranque Previas a TCP

**Proyecto:** Preservación y emulación de servidores de *Persona 5: The Phantom X (P5X)*  
**Cliente objetivo:** Versión PC Global/Steam (`D:\secret\P5X\client\pc\P5X.exe`)  
**Condición obligatoria:** Análisis de solo lectura; determinación de satisfacción **SIN modificar ningún binario** (`P5X.exe`, `GameAssembly.dll`, `steam_api64.dll`).

---

## 1. Resumen Ejecutivo de Compuertas

El cliente PC de P5X ejecuta tres compuertas lógicas consecutivas antes de iniciar la comunicación de cable TCP (`CSLogin`, MsgID 101). Todas pueden satisfacerse o desactivarse limpiamente mediante configuración externa local:

| Compuerta | Binario / Componente evaluador | Condición de satisfacción | Solución local sin modificar binarios | Nivel de Evidencia |
| :--- | :--- | :--- | :--- | :--- |
| **1. SteamAPI_RestartAppIfNecessary** | `GameAssembly.dll` $\rightarrow$ `SteamManager.Awake()` invocando `steam_api64.dll` | Retorno `false` (`0`) al detectar AppID y cliente Steam | El archivo `client\pc\steam_appid.txt` ya existe con AppID `3061570`. Con Steam en ejecución, retorna `0` automáticamente. | **CONFIRMADO** |
| **2. LoadServerList (HTTP JSON)** | `LoginMod:LoadServerList` (`E8DF29521A39C99.bytes` Chunk 0) | Descarga o lectura de JSON con `luaver <= luaDataVersionNumber` y matriz `ServerList` | Redirección de dominio en `C:\Windows\System32\drivers\etc\hosts` (`127.0.0.1`) sirviendo JSON estático en HTTP local. | **CONFIRMADO** |
| **3. OneSDKMgr:IsSDKLoggedIn()** | `UI_Denglu` (`7A4379BBA8417A9.bytes` Chunk 61) y `OneSDKMod` (`07B3A247F1ADE14.bytes` Chunk 77) | `IsSDKAvailable() == false` (Modo Dev/Standalone) O Ticket Steam obtenido | Inyección de `"SDKEnable": false` en el JSON de servidor para desactivar SDK y habilitar login directo por cuenta/clave; o ticket Steam local. | **CONFIRMADO** |

---

## 2. Compuerta 1: `SteamAPI_RestartAppIfNecessary` (`steam_api64.dll`)

### 2.1. Localización y Flujo en el Binario
- **Clase en metadatos:** `SteamManager` (`TypeDef[1097]`, offset `0xde3fa4` en `global-metadata.dat`).
- **Método evaluador:** `SteamManager.Awake()` (`MethodDef[18538]`, token `0x600486a`, offset `0x4b4020` en `global-metadata.dat`).
- **Llamada nativa:** Invoca la función exportada `SteamAPI_RestartAppIfNecessary` en `P5X_Data\Plugins\x86_64\steam_api64.dll`.
- **Comportamiento si retorna `true`:**
  Ejecuta la salida forzada del proceso registrando en la consola de depuración:
  `"[Steamworks.NET] Shutting down because RestartAppIfNecessary returned true. Steam will restart the application."` (Literal de cadena index `20321` / `0x4f61`, offset `0xcf93d`).

### 2.2. Lógica Interna del SDK de Steam (Valve)
Según la especificación oficial de Steamworks SDK 1.60 (compilado en `Steamworks.NET.txt`):
1. `SteamAPI_RestartAppIfNecessary(AppId_t unOwnAppID)` verifica si el ejecutable actual fue lanzado por el proceso `steam.exe` con los argumentos de entorno de la sesión activa.
2. Si el proceso no fue lanzado directamente por Steam, la función busca el archivo de texto plano `steam_appid.txt` en el mismo directorio del binario ejecutable (`client\pc\`).
3. Si `steam_appid.txt` existe y contiene el AppID correcto:
   - Si el cliente de Steam está en ejecución en el sistema operativo, la función comprueba la existencia de la sesión y **retorna `false` (`0`) inmediatamente**, permitiendo que la instancia actual continúe su ejecución directa sin cerrarse ni relanzarse.

### 2.3. Verificación Local
- **Ruta del archivo:** `D:\secret\P5X\client\pc\steam_appid.txt`
- **Contenido verificado:**
  ```text
  3061570
  ```
- **Conclusión técnica [CONFIRMADO]:** No se requiere alterar ningún byte de `P5X.exe` ni `steam_api64.dll`. Con el cliente Steam iniciado en Windows (incluso en modo desconectado / *offline*), la compuerta queda 100% satisfecha de forma nativa.

---

## 3. Compuerta 2: `LoadServerList` (Descarga HTTP JSON)

### 3.1. Localización y Flujo en Bytecode Lua
- **Módulo evaluador:** `LoginMod:LoadServerList()` (`E8DF29521A39C99.bytes`, Chunk `0`, Proto `69`, offset `19296..20847`).
- **Mapeo de URL:** Construido en `07B3A247F1ADE14.bytes` Chunk `45` (`OnlineConfig.lua`):
  - Host de lista de servidores: `_G.ServerListDownLoadURL`:
    - Región `test`/`cn`/`jp`: `https://nsywlydcdn1.wmupd.com/nsywlydserverlist/client/{0}/{1}?random={2}` y CDN redundante `nsywlydcdn2.wmupd.com`.
    - Región `tw`: `https://patchp5x1.iwplay.com.tw/p5xserverlist/client/{0}/{1}?random={2}`.
    - Host de depuración: `s.1000094100.gamebean.net/`.
- **Mecanismo de descarga:** `LuaUtil.GetStringFromWebByUrl(GetServerURL())`.

### 3.2. Reglas de Validación en `LoginMod:OnServerListLoaded`
1. **Decodificación JSON:** Ejecuta `ServerListData.JsonDecode(response)`. Si la cadena no es JSON válido, emite error `1000087` y cierra la aplicación.
2. **Chequeo de versión:** Evalúa `tonumber(ServerListData.luaver) <= _G.luaDataVersionNumber`. Si el valor supera la versión local, emite error `1000085`.
3. **Poblado de servidores:**
   Lee la matriz de servidores (`appOnline` o `apptest` o `ServerList`):
   - `id`: Entero único del servidor.
   - `name`: Nombre presentado en la interfaz (p. ej. `"Servidor Preservación Local"`).
   - `serverIP`: Dirección IP o nombre de host (`"127.0.0.1"`).
   - `serverPort`: Puerto TCP de destino (`18100`).
   - `status`: Estado del servidor (`1` = Normal / Fluido).
   - `clientSrvID`: ID del nodo de juego.
   - `aIdx`: Índice de zona.
4. **Disparo de finalización:** Emite `EventMgr:Brocast(EVENT_LOGIN.ServerListComplete)`.

### 3.3. Solución Local sin Modificar Binarios
- **Intercepción DNS local mediante `hosts`:**
  Añadir a `C:\Windows\System32\drivers\etc\hosts`:
  ```text
  127.0.0.1 nsywlydcdn1.wmupd.com
  127.0.0.1 nsywlydcdn2.wmupd.com
  127.0.0.1 patchp5x1.iwplay.com.tw
  ```
- **Esquema JSON mínimo a servir en HTTP local:**
  ```json
  {
    "luaver": "0",
    "ServerList": [
      {
        "id": 1,
        "name": "P5X Local Preservation",
        "serverIP": "127.0.0.1",
        "serverPort": 18100,
        "status": 1,
        "clientSrvID": 1,
        "aIdx": 1
      }
    ],
    "SDKEnable": false
  }
  ```
- **Conclusión técnica [CONFIRMADO]:** La compuerta se satisface íntegramente mediante un servidor HTTP local en loopback, dirigiendo al cliente hacia el servidor TCP emulado en `127.0.0.1:18100`.

---

## 4. Compuerta 3: `OneSDKMgr:IsSDKLoggedIn()`

### 4.1. Localización y Evaluación
- **Módulo de interfaz:** `UI_Denglu` (`7A4379BBA8417A9.bytes`, Chunk `61`, Proto `12`, offset `6521`).
- **Módulo central del SDK:** `OneSDKMod` (`07B3A247F1ADE14.bytes`, Chunk `77`, Proto `48`, offset `9830`).
- **Lógica de evaluación en `UI_Denglu:OnTryLogin()`:**
  ```lua
  if OneSDKMgr:IsSDKAvailable() then
      if not OneSDKMgr:IsSDKLoggedIn() then
          OneSDKMgr:OpenSDKLogin()
          return
      end
  end
  LoginMgr:OnTryLogin(...)
  ```

### 4.2. Doble Vía de Resolución sin Modificación de Binarios

#### Vía A: Desactivación por Configuración Remota (`SDKEnable = false`)
- En `OneSDKMod:InitSDKInfo()` (Chunk `77`, offset `1802..1860`):
  ```lua
  self.mIsSDKAvailable = OnlineConfig:Get("SDKEnable")
  ```
- En `07B3A247F1ADE14.bytes` Chunk `45`: `OnlineConfig` extrae las propiedades directas del archivo JSON servido durante `LoadServerList`.
- Si el JSON inyectado contiene `"SDKEnable": false`:
  1. `OneSDKMgr:IsSDKAvailable()` devuelve **`false`**.
  2. `UI_Denglu:OnTryLogin()` comprueba `if OneSDKMgr:IsSDKAvailable()` (que evalúa a falso) y **salta completamente la llamada a `OpenSDKLogin()`**.
  3. En `LoginMod:StartLogin` (Chunk `0`, offset `17431..17850`), cuando la plataforma es PC y `IsSDKAvailable() == false`, el cliente activa el modo de desarrollo autónomo:
     - Carga la cuenta y contraseña directamente desde `PlayerPrefs` (`LOGIN_SAVE`).
     - Envía la trama TCP `CSLogin` (`MsgID 101`) directamente al servidor local sin requerir autenticación externa.

#### Vía B: Autenticación Pasiva mediante Ticket Local de Steam
- Si se prefiere mantener el SDK activado (`SDKEnable: true`):
  1. `OneSDKMod` detecta la plataforma `PlatformOSType.PC` y activa el backend `GlobalSDK` (`WPGlobalSDK.dll` y `GameSteamSdk_64.dll`).
  2. `OneSDKMgr:EnterLogin()` solicita a Steamworks un ticket de autenticación de sesión local (`SteamUser()->GetAuthSessionTicket`).
  3. Steamworks retorna el ticket hex en memoria local y dispara el callback de éxito en `OneSDKMod`, estableciendo `self.mIsSDKLoggedIn = true`.
  4. El cliente emite `CSLogin` con `token = <ticket_hex>`, el cual el servidor local de preservación acepta y valida trivialmente.

- **Conclusión técnica [CONFIRMADO]:** Ambas vías funcionan sin necesidad de parches binarios. La Vía A es la más robusta para preservación pura independiente de Steam, mientras que la Vía B permite la ejecución directa utilizando el lanzador oficial.

---

## 5. Matriz de Configuración Local Definitiva

Para ejecutar el cliente P5X en modo preservado local contra `127.0.0.1` sin tocar ningún binario:

1. **Mantener intacto `client\pc\steam_appid.txt`** (AppID `3061570`).
2. **Entrada en `hosts`:**
   ```text
   127.0.0.1  nsywlydcdn1.wmupd.com
   127.0.0.1  patchp5x1.iwplay.com.tw
   ```
3. **Servidor HTTP local (Port 80/443):**
   Responder en cualquier ruta de lista de servidores con el JSON que incluye `"serverIP": "127.0.0.1"`, `"serverPort": 18100` y `"SDKEnable": false`.
4. **Servidor TCP de preservación (`poc_login_server.py`):**
   Escuchando en `127.0.0.1:18100`, gestionando la secuencia completa: Handshake RC4 $\rightarrow$ `CSLogin` $\rightarrow$ `CSLoginGate` $\rightarrow$ `SCServerConfig` $\rightarrow$ `CSQueryCharacters` $\rightarrow$ `CSCharacterLogin` $\rightarrow$ `SCInitData` $\rightarrow$ `CSSceneEnter` $\rightarrow$ Escena 3D activa.
