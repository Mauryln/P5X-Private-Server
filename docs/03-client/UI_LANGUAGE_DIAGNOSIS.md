# Diagnóstico Técnico Forense: Carga de UI y Resolución de Idioma (EN vs Prefabs JP)

**Fecha:** 15 de Noviembre de 2026  
**Objetivo:** Determinar la causa raíz exacta de la ausencia de la interfaz de usuario (HUD, minimapa, menú de funciones, SNS, barra de acción en combate) en el cliente local `D:\secret\P5X\P5X.exe`, documentar exhaustivamente las 4 vías de investigación bajo la regla de no modificar binarios ni assets, y certificar el estado criptográfico de la instalación.

---

## 1. Verificación Criptográfica de Integridad (Regla de Parada)

Ningún archivo binario ejecutable (`.exe`, `.dll`), metadatos (`global-metadata.dat`) ni asset bundles (`.bundle`) ha sido modificado o alterado. Los 5 binarios canónicos de la instalación local conservan sus hashes originales intactos:

| Binario Canónico | Ruta Relativa | SHA-256 Canónico Verificado | Estado |
| :--- | :--- | :--- | :--- |
| **GameAssembly.dll** | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **INTACTO** |
| **P5X.exe (Cliente)** | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | **INTACTO** |
| **global-metadata.dat**| `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **INTACTO** |
| **steam_api64.dll** | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | **INTACTO** |
| **P5X.exe (Launcher)**| `P5X.exe` | `FE1D12F81DDA178DE6A4B86E2DEBA2162C3DD855E7726DB4B19FA036823BD39E` | **INTACTO** |

*Restricción absoluta cumplida: 0 accesos a `C:\Program Files (x86)\Steam\...`.*

---

## 2. Síntoma y Evidencia Forense en Runtime

Al ejecutar el juego contra el servidor local de desarrollo (`poc_login_server.py`), la escena 3D de Shibuya carga correctamente, el jugador puede moverse con controles físicos y hablar con NPCs (diálogos e interacciones activas). Sin embargo, el HUD permanece completamente vacío (pantalla limpia sin UI), tal como se documentó en:
- Captura de referencia esperada: `D:\secret\Real-game\WhatsApp Image 2026-11-15 at 12.46.49 PM.jpeg` (Minimapa superior izquierdo, barra de eventos superior, menú inferior derecho "MENU, TASK, THIEVES DEN, CITY, METAVERSE").
- Captura de falla en runtime: `D:\secret\Bugs\Screenshot 2026-11-15 124738.png` (Mundo 3D renderizado, sin ningún elemento de HUD).

### Registro de Errores en `Player.log`
En el log de runtime del motor Unity (`Player_hud_fail.log`):
```text
Línea 171: System Language:EN
Línea 443: 解析I18NAssetMap.xml...
Línea 444: 启用多语言混包资源：主语言 [JP]，多语言 [EN]
...
Línea 862: Release Asset Error: UI-zhujiemian-ditu-map_EN.prefab  is null. 1510.
Línea 863: Release Asset Error: UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab  is null. 1510.
Línea 864: Release Asset Error: UI-zhujiemian-sns-new_EN.prefab  is null. 1510.
Línea 865: Release Asset Error: UI-zhujiemian-youcegongnengqu01_EN.prefab  is null. 1510.
```

---

## 3. Investigación Exhaustiva de las 4 Vías

### Vía 1: Configuración Local del Launcher (`Config.ini`)
- **Ubicación inspeccionada:** `D:\secret\P5X\P5XLaunch\Config\Config.ini`
- **Valores presentes:**
  ```ini
  [UPDATE_CONFIG]
  Language=en
  SupportLanguages=en;
  Branch=P5XEN_Steam
  LaunchFilePath=P5XGame.exe
  LaunchCmdLine=/launcher
  ```
- **Auditoría de Desensamblado de `WmglLauncher` (`P5X.exe`):**
  Se desensambló la rutina de lanzamiento (`0x140003b00..0x140003dfb`). El launcher lee únicamente las claves `Patcher`, `GameID`, `Client`, `LaunchType` y `LaunchCmdLine`. La línea de comandos resultante invocada hacia el cliente es:
  `client\pc\P5X.exe /launcher` o `client\pc\P5X.exe /directly`.
  **No transfiere ningún parámetro de idioma a la línea de comandos.**
- **Auditoría en el Cliente (`client\pc\P5X.exe` y `GameAssembly.dll`):**
  Se realizó un escaneo por string y metadatos (`global-metadata.dat`). Existen **0 referencias** a `Config.ini`. El ejecutable del cliente y la librería `GameAssembly.dll` no abren, no buscan y no conocen el archivo `Config.ini`.
- **Conclusión Vía 1:** Modificar `Language=jp` o `Language=ja` en `Config.ini` es 100% inocuo e inoperante para el cliente en ejecución.

---

### Vía 2: Parámetros de Lanzamiento CLI del Cliente
- **Auditoría de CLI Arguments en `GameAssembly.dll` y `global-metadata.dat`:**
  Se analizaron todas las cadenas de texto que inician con `-` y `--` y las llamadas a `Environment.GetCommandLineArgs`.
  - Argumentos reconocidos por el juego: Únicamente switches estándar de Unity (`-screen-fullscreen`, `-screen-width`, `-screen-height`, `-batchmode`, `-nographics`, `-logFile`, `/launcher`, `/directly`).
  - No existe soporte para `-language`, `-culture`, `-locale`, `-region`, `-lang` ni `-jp`.
- **Mecanismo Nativo de Unity Engine:**
  Se analizó `client\pc\UnityPlayer.dll`. La API de Unity `Application.systemLanguage` está implementada invocando directamente la API Win32 de Windows:
  `kernel32!GetUserDefaultLCID()`.
  El motor Unity Standalone Player no posee ningún flag CLI nativo para alterar el retorno de `GetUserDefaultLCID()`.
- **Conclusión Vía 2:** Ningún parámetro CLI soportado por el binario permite forzar el idioma del sistema.

---

### Vía 3: Protocolo de Red (Mensajes Protobuf del Servidor)
- **Auditoría bit a bit en `docs/msg.proto`:**
  Se inspeccionó la definición formal de los mensajes de inicialización y sincronización:
  1. `SCLoginResult` (MsgID 102): Contiene `resultCode`, `account`, `zoneTime`, `serverId`, `gameAddress`, `sessionId`, `timeout`, `prepareReconnection`, `isNeedUpdate`, `failText`, `revision`.
  2. `SCServerConfig` (MsgID 1112): Contiene `isClientBattle`, `openGM`, `timeNow`, `baseTime`, `timeZone`.
  3. `SCLoginGateResult` (MsgID 104): Contiene `errorCode`.
  4. `SCInitData` (MsgID 1102): Contiene contenedores de datos del jugador (`human`, `scene`, `consume`, `material`, etc.).
  5. `ServerListData`: Contiene lista de servidores (`appOnline`).
- **Conclusión Vía 3:** Ningún paquete del protocolo transporta identificadores de cultura, idioma de interfaz o directivas de paquetes de recursos. La capa de red es completamente agnóstica de la localización de prefabs de la UI.

---

### Vía 4: Selección de Prefabs en C# y Distribución de Bundles
- **Auditoría de Bundles (16.050 archivos en `OuterPackage\Bundles\Windows`):**
  - En `OuterPackage\Bundles\Windows\005\ui_mainui498d6b82.bundle`:
    - Reside el prefab: `UI-zhujiemian-ditu-map_JP.prefab` (Minimapa).
    - Residen los prefabs: `UI-zhujiemian_JP` y `UI-zhujiemian_EN`.
    - **No existe** `UI-zhujiemian-ditu-map_EN.prefab`.
  - En `OuterPackage\Bundles\Windows\059\shared_36e08d0e.bundle`:
    - Reside `UI-zhujiemian-youcegongnengqu01-huodong`.
    - **No existe** `UI-zhujiemian-youcegongnengqu01_EN.prefab`.
  - En todos los 16.050 bundles locales:
    - **Cero ocurrencias** de `UI-zhujiemian-sns-new_EN.prefab` y `UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab`.
- **Mecanismo de Selección en C# (`GameAssembly.dll`):**
  1. En la inicialización del motor (`EngineInitManager`), se carga el archivo `I18NAssetMap.xml` contenido en `OuterPackage\Bundles\Windows\070\i18n_manifest277deefb.bundle`.
  2. La configuración declara:
     ```xml
     <MUI18NAssetMap>
       <MainLanguage>JP</MainLanguage>
       <MultiLanguages>
         <string>EN</string>
       </MultiLanguages>
       <Assets>...</Assets>
     </MUI18NAssetMap>
     ```
  3. El motor consulta `Application.systemLanguage`. En una máquina Windows con formato regional en inglés (`en-US`), `GetUserDefaultLCID()` retorna `0x0409` (1033) $\to$ `System Language:EN`.
  4. La clase `MUEngine.Implement.ProjectResource` ejecuta su método `RelocateI18NAssetName`:
     Al detectar que el idioma actual (`EN`) se encuentra en la lista `MultiLanguages`, reescribe de forma forzada los nombres de los prefabs solicitados por los módulos Lua (`UIMgr` en chunk 31 y 36) concatenando `_EN.prefab`:
     - `UI-zhujiemian-ditu-map` $\to$ `UI-zhujiemian-ditu-map_EN.prefab`
     - `UI-zhujiemian-youcegongnengqu01` $\to$ `UI-zhujiemian-youcegongnengqu01_EN.prefab`
     - `UI-zhujiemian-sns-new` $\to$ `UI-zhujiemian-sns-new_EN.prefab`
     - `UI-zhandou-guaiwuxingdongtiao-ver2` $\to$ `UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab`
  5. Como estos prefabs con sufijo `_EN` no existen en los bundles empaquetados limpios, el AssetLoader arroja el error de puntero nulo (`is null. 1510`), cancelando la instanciación visual de la interfaz.
  6. En el cliente oficial en producción, los assets `_EN` eran descargados a demanda por el sistema de CDN/Hotfix Zeus hacia `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\Res`.
- **Auditoría de PlayerPrefs (`PREFERED_USER_LANGUAGE`):**
  Se analizó la clase `GameConfig` (Type 24). Contiene el campo `PREFERED_USER_LANGUAGE_KEY`, pero los métodos `GetPerferedUserLanguage` y `SetUserLanguage` fueron despojados (stripped) durante la compilación Release de IL2CPP, apuntando a stubs vacíos (`0x1804f43f0: ret 0`). No hay lectura activa de esta clave en el registro de Windows (`HKCU\Software\SEGA\p5x_en`).

---

## 4. Solución Limpia y No Invasiva

Dado que el cliente determina el idioma únicamente a través de la llamada nativa Win32 `GetUserDefaultLCID()` de `UnityPlayer.dll`, **no es necesario ni admisible modificar ningún archivo, asset o binario del juego**.

### La Vía Limpia Encontrada
Para que el cliente reconozca el idioma principal canónico (`JP`), instancie los prefabs `_JP` existentes y active el HUD al 100%:

1. **Ajuste Regional del Usuario de Windows (Reversible sin tocar el juego):**
   - El motor consulta el LCID del perfil de usuario de Windows (`HKCU\Control Panel\International\Locale`).
   - Configurando el Formato Regional de Windows en **Japanese (Japan)** (`ja-JP` / LCID `0x0411` = 1041):
     - `GetUserDefaultLCID()` retorna `0x0411`.
     - `Application.systemLanguage` retorna `Japanese`.
     - El motor entra en modo `MainLanguage: JP`.
     - `RelocateI18NAssetName` carga directamente los prefabs base y `_JP` presentes en `005\ui_mainui498d6b82.bundle`.
2. **Alternativa sin cambiar la configuración global de Windows (Launcher Wrapper):**
   - Ejecutar el cliente mediante un script lanzador liviano o herramienta estándar de locale (ej. `Locale Emulator` o script Win32 que aplique `SetThreadLocale(0x0411)` o inyecte temporalmente el LCID japonés en el proceso de `P5X.exe`).
   - Esto mantiene el sistema operativo en inglés mientras el proceso `P5X.exe` percibe `System Language:JA/JP`.

---

## 5. Resumen de Conclusiones

| Vía Evaluada | Factible sin Modificar Assets/Binarios | Motivo Técnico Formal |
| :--- | :---: | :--- |
| **1. Launcher `Config.ini`** | **NO** | `P5X.exe` y `GameAssembly.dll` no leen `Config.ini`; el launcher no propaga flags de idioma. |
| **2. Parámetros CLI (`-language`)** | **NO** | Unity Player e IL2CPP no tienen flags de línea de comandos para sobreescribir `Application.systemLanguage`. |
| **3. Protocolo de Red (`msg.proto`)** | **NO** | `SCLoginResult` y `SCServerConfig` no tienen campos de idioma; la UI es 100% resuelta en cliente. |
| **4. Selección C# / Bundles** | **SÍ (vía Locale OS)** | La selección depende de `Application.systemLanguage` vs `MainLanguage:JP`. Al iniciar con locale japonés, se usan los prefabs `_JP` locales existentes sin alterar ningún archivo del juego. |
