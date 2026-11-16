# Informe de Diagnóstico y Cierre de Sesión — P5X Local Emulation

**Fecha:** 14 de noviembre de 2026 (21:55 local)  
**Entorno de Trabajo:** `D:\secret\P5X` (Modo Preservación / Local Offline)  
**Servidor Local:** `D:\secret\scratch\poc_login_server.py` en `127.0.0.1:10403`  
**Redirección DNS:** `127.0.0.1 eulogin.p5xjpupd.com` en `C:\Windows\System32\drivers\etc\hosts`  
**Auditoría de Integridad:** Cumplimiento estricto de `D:\secret\Rules\Rules.md`  

---

## 1. Certificación de Reglas y Cumplimiento (`Rules.md`)

De acuerdo con la regla dura establecida en `D:\secret\Rules\Rules.md`:
1. **Aislamiento de Steam:** Prohibido de forma categórica leer, ejecutar o modificar `C:\Program Files (x86)\Steam\steamapps\common\P5X\...`. Esta directiva se ha respetado al 100%; no se ha interactuado en ningún momento con dicha ruta.
2. **Espacio de Trabajo Exclusivo:** Todo el trabajo se ejecuta y audita exclusivamente sobre la copia limpia y sin cuentas de `D:\secret\P5X`.
3. **Verificación Criptográfica de Integridad:** Se verificaron los hashes SHA-256 de los 4 binarios y metadatos de `D:\secret\P5X`, manteniéndose idénticos a los del estado original:

| Binario / Metadata | Ruta Relativa en `D:\secret\P5X` | Hash SHA-256 Verificado | Estado |
|---|---|---|---|
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | Intacto |
| `P5X.exe` | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | Intacto |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | Intacto |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | Intacto |

---

## 2. Resultados Clave Obtenidos en la Ejecución en Vivo

### 2.1 Cero Errores de Red y Handshake Completo
- En la ejecución previa, el cliente se desconectaba a los 7 segundos con *"Error de red"* debido al temporizador `updateWeakCheck` de `NetWorkMod`, que esperaba respuesta al mensaje `14467` (`CSActivityDIYCakeQuery`).
- Tras implementar los manejadores de respuesta para los 12 mensajes de subsistemas en `poc_login_server.py`, el cliente oficial de Steam (`D:\secret\P5X\client\pc\P5X.exe`) ejecutó la secuencia completa:
  1. Handshake TCP inicial (Trama 0 con clave RC4).
  2. Autenticación de cuenta: `CSLogin` (101) $\rightarrow$ `SCLoginResult` (102, `resultCode: 1`, asignando `gameAddress: 127.0.0.1:10403`).
  3. Puerta de enlace: `CSLoginGate` (103) $\rightarrow$ `SCLoginGateResult` (104, `errorCode: 0`) + `SCServerConfig` (1112).
  4. Consulta de personajes: `CSQueryCharacters` (1001) $\rightarrow$ `SCQueryCharactersResult` (1002, Wonder).
  5. Entrada de personaje: `CSCharacterLogin` (1007) $\rightarrow$ `SCCharacterLoginResult` (1008, `resultCode: 0`) + `SCInitData` (1102, Shibuya `sn: 2102`).
  6. Intercambio de subsistemas: `1419`, `7906`, `12904`, `12901`, `127`, `12916`, `1467`, `19703`, `20101`, `2505`, `14467` (`SCActivityDIYCakeQuery` 14468), `19501`, `1261`.
- **Resultado de Red:** Total de 38 tramas intercambiadas con éxito. **Cero desconexiones de red (`0 disconnects`), cero errores `updateWeakCheck`.**

---

## 3. Diagnóstico Adversario de la Pantalla en Negro

### 3.1 Evidencia en Logs de Ejecución

Al inspeccionar `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\log_2026_11_14.log` (líneas 9051–9058):
```text
26/11/14 21:47:26.543-904 [Exception ]LuaException: [string "BattleRoleController"]:0: attempt to concatenate a nil value
stack traceback:
	[string "BattleRoleController"]: in function 'SetModelSn'
	[string "HumanController"]: in function 'SetModelSn'
	[string "HeroController"]: in function 'SetModelSn'
	[string "ControllerMod"]: in function 'CreateHero'
	[string "ControllerMod"]: in function 'RevertHeroFromFake'
	[string "SceneMod"]: in function <[string "SceneMod"]:0>
LuaInterface.LuaState:PCall(Int32, Int32)
```

Simultáneamente en `Player.log` (líneas correspondientes):
```text
SceneLoadingMod：场景加载超时，可能是:【2 主角加载】未完成。
SceneLoadingMod：场景加载超时，可能是:【6 场景资源加载】未完成。
[44075]OnEnterScene
SceneLoadingMod：切换场景【准备结束】,scene sn: 2102 最近的战斗sn: 0 scn13_shibuya
-----SceneLoadingMod：切换场景/同场景位置切换【完全结束】----scn13_shibuya
SceneLoadingMod：本次切换场景用时: 35.263秒 scn13_shibuya
Restart NPCLoadAdditiveScene
```

### 3.2 Causa Raíz Técnica Identificada
1. **Falta del campo `modelSn` en `DHuman`:**  
   En `scratch/proto2_codec.py`, la función de serialización `encode_DHuman` solo incluía los campos básicos (`id`, `name`, `level`, `sex`, `hp`, `sp`). No codificaba el campo 9 (`optional string modelSn`) ni el campo 11 (`optional int32 sn`).
2. **Fallo en `BattleRoleController:SetModelSn`:**  
   Al cargar la escena de Shibuya, `SceneMod` invoca `ControllerMod:CreateHero`, el cual delega en `HeroController:SetModelSn(modelSn)`.  
   Al ser `modelSn` un valor `nil`, la función intenta consultar `Conf.CharacterModel:Get(modelSn)` y concatena `"no ConfCharacterModel, ID " .. modelSn` (instrucción bytecode LuaJIT 105–107 en `7A4379BBA8417A9.bytes`). Esto lanza la excepción crítica `attempt to concatenate a nil value`.
3. **Bloqueo del Coordinador de Carga:**  
   Debido a que `CreateHero` abortó por la excepción Lua, la entidad del protagonista nunca fue instanciada en la escena, impidiendo la emisión del evento `SceneLoadingMgr:FinishWait(SceneLoadedType.HeroLoaded)`.  
   Por este motivo, `SceneLoadingMod` quedó congelado esperando el evento `【2 主角加载】` (carga del protagonista), alcanzando el tiempo límite de espera (35 segundos). Como `HeroLoaded` nunca se completó, la llamada `SceneLoadingMgr:TryHideBlackScreen()` jamás fue invocada, dejando la pantalla en negro (telón de carga visualmente opaco).

### 3.3 Relación con el "ID 1001"
En la base de datos de configuración del juego (`ConfData`):
- `1001` es el identificador canónico (`sn`) del protagonista Wonder en las tablas `Conf.ZhuJue` y `Conf.CharacterModel`.
- En el servidor PoC actual, el personaje de prueba utilizaba `id: 10001`, mientras que la configuración canónica de Wonder espera `sn: 1001` y su correspondiente cadena de modelo `modelSn = "1001"`.

---

## 4. Plan de Acción para la Siguiente Sesión

Para desbloquear la renderización 3D y retirar el telón negro:

1. **Actualizar `encode_DHuman` en `proto2_codec.py` y `poc_login_server.py`:**
   - Incorporar field 9: `encode_string_field(9, "1001")` (`modelSn`).
   - Incorporar field 11: `encode_varint_field(11, 1001)` (`sn`).
   - Asignar `human_id = 1001` para alinear con la configuración de `Conf.ZhuJue`.
2. **Definir Posición de Spawn Canónica en Shibuya:**
   - Extraer las coordenadas exactas de entrada (`enter_point`) para Shibuya (`sn: 2102`) en `Conf.Scene` e inyectarlas en `DInitScene.posNow` (en lugar de `0.0, 0.0, 0.0` sintético).
3. **Verificación del Flujo:**
   - Comprobar que `CreateHero` complete sin excepciones Lua.
   - Confirmar la llegada de `HeroLoaded` $\rightarrow$ envío de `CSSceneEnter` (1201) $\rightarrow$ respuesta `SCSceneEnterEnd` (1203) $\rightarrow$ llamada automática a `TryHideBlackScreen()`.

---

## 5. Actualización de Sesión (15 de noviembre de 2026) — Desbloqueo 3D y Diagnóstico de la Cámara Subterránea

### 5.1 Hito Alcanzado: Renderizado 3D y Levantamiento del Telón Negro
En la prueba de ejecución directa realizada por el usuario sobre `D:\secret\P5X\client\pc\P5X.exe`, se alcanzó un hito histórico de preservación:
- **Cero errores de red:** Conexión completa contra `127.0.0.1:10403`.
- **Audio CRIWARE y Telón Levantado:** Se escuchó la música ambiental del juego y la pantalla negra se desactivó por completo.
- **Escena 3D de Shibuya Renderizada:** La escena `scn13_shibuya` (`sn: 2102`) cargó la geometría completa de Shibuya (rascacielos, cielo azul, puentes peatonales, vallas publicitarias, árboles, colisiones `Cube (11)` y NPCs de multitud).
- **Evidencia Gráfica Empírica:** Captura documentada en `D:\secret\logs\Screenshot 2026-11-15 064721.png`, mostrando el HUD interactivo con `[J] Missions` (inferior izquierda) y el UID asignado `ID:100001` (inferior derecha).

### 5.2 Diagnóstico Técnico Adversario: ¿Por qué la cámara quedó debajo de la ciudad?
Al inspeccionar la captura y cruzarla con `Player.log` y el desensamblado del bytecode LuaJIT 2.1, se aislaron dos causas raíz exactas:

#### Causa Raíz 1: Ausencia del Prefab 3D por `modelSn` Incorrecto (`CONFIRMADO`)
1. **Traza en `Player.log`:**
   ```text
   no  ConfCharacterModel, ID 1001
   ...
   SceneLoadingMod：场景加载超时，可能是:【2 主角加载】未完成。
   ...
   LuaException: System.NullReferenceException: Object reference not set to an instance of an object.
     at MUGame.CharacterMoveBase.OnBeginInit ()
     at MUGame.HeroDirMove.Begin (MUEngine.MUActorEntity ent, Single[] gears, Single fixedSpeed)
   ```
2. **Desensamblado de `HumanController:SetModelSn` (`7A4379BBA8417A9.bytes`, Chunk 35):**
   - La función consulta `self.mModConf = Conf.CharacterModel:Get(modelSn)`.
   - Si `mModConf` es `nil`, la función imprime `no  ConfCharacterModel, ID <modelSn>` y **omite la llamada `self:Load()`**.
   - Al no ejecutarse `self:Load()`, el prefab 3D del protagonista nunca fue instanciado en el grafo de escena de Unity.
   - En consecuencia:
     - `HeroController:OnLoadRes` nunca se disparó, impidiendo la emisión de `SceneLoadingEvents.FinishWait(SceneLoadedType.HeroLoaded)`.
     - `CinemachineMgr:SetCinemachineHero` nunca pudo anclar la cámara al personaje.
     - Al carecer de entidad de seguimiento, la cámara de Unity permaneció en el origen de coordenadas mundial `(0.0, 0.0, 0.0)`, mirando hacia arriba a la malla elevada de la ciudad.
     - `MUGame.CharacterMoveBase.UpdateMove` arrojó `NullReferenceException` continuo al intentar mover un actor inexistente.
3. **Resolución del Identificador Canónico de Modelo:**
   - Mediante análisis de los chunks 17 y 167 de `E8DF29521A39C99.bytes` y chunk 36 de `07B3A247F1ADE14.bytes`, se confirmó que en `Conf.CharacterModel`:
     - `1001` es el `sn` numérico de la tabla `Conf.ZhuJue`.
     - La clave string de modelo (`modelSn`) para Wonder en el mundo real (Shibuya) es `"wonder_uniform"` (uniforme escolar canónico).
     - Para el metaverso/palacio es `"wonder_thief"`.

#### Causa Raíz 2: Desbordamiento de CRT en `SCServerConfig` (`CONFIRMADO`)
1. **Traza en `Player.log`:**
   ```text
   LuaException: [string "functions"]:0: attempt to index a nil value
   stack traceback:
   	[string "functions"]: in function 'Get0ClockTime'
   	[string "ServerTimeMod"]: in function 'SetServerTimeBiase'
   	[string "LoginMod"]: in function 'OnGetSCServerConfigMsg'
   ...
   LuaException: [string "ServerTimeMod"]:0: attempt to index a nil value
   	[string "ServerTimeMod"]: in function 'GetOpenServerDay0'
   	[string "LoginMod"]: in function 'OnFirstEnterStage'
   ```
2. **Causa Raíz:**  
   En `poc_login_server.py`, los campos `timeNow` y `baseTime` de `SCServerConfig` (1112) se enviaban en milisegundos (`1.73e12`). La biblioteca C de Windows (`localtime`) solo soporta valores hasta el año 3000; al recibir un timestamp de milisegundos (año 56830), `os.date("*t", timeNow)` devolvía `nil`, causando la excepción `attempt to index a nil value`.
3. **Corrección:**  
   Normalizado a segundos Unix estándar (`int(time.time())`).

---

## 6. Correcciones Implementadas en `D:\secret\scratch`

1. **`proto2_codec.py`:**
   - `encode_DHuman`: `model_sn = "wonder_uniform"`, `sn = 1001`, `create_time = 1700000000000`.
   - `encode_DCharacter`: `model = "wonder_uniform"`, `sn = 1001`.
   - `encode_SCServerConfig`: `timeNow` y `baseTime` en segundos Unix (`1700000000`).
2. **`poc_login_server.py`:**
   - `SCServerConfig` (1112) envía `timeNow = now_sec` y `baseTime = now_sec`.
   - `SCQueryCharactersResult` (1002) envía `model = "wonder_uniform"`.
   - `SCInitData` (1102) envía `modelSn = "wonder_uniform"` en `DHuman`.
3. **Servidor en Ejecución:**
   - Proceso background activo en `127.0.0.1:10403`.

---

## 7. Hito Histórico Alcanzado: Sesión Jugable en Shibuya 3D (Confirmado por el Usuario)

**Fecha de Validación:** 15 de noviembre de 2026 (~07:29–07:31 local)  
**Estado:** **HITO "JUGAR" COMPLETAMENTE ALCANZADO**

Tras aplicar las correcciones de `modelSn = "wonder_uniform"` y la normalización de timestamps CRT en `poc_login_server.py`, el usuario ejecutó el cliente oficial (`D:\secret\P5X\client\pc\P5X.exe`), confirmando de manera empírica e in situ la operatividad del juego:

1. **Movimiento Libre de Wonder:**
   - La entidad del protagonista se instancia con el modelo canónico de Wonder (`wonder_uniform`).
   - La cámara virtual Cinemachine se ancla de forma correcta a la espalda del personaje en tercera persona.
   - El usuario tiene control total y movimiento libre sobre Wonder en el entorno 3D de Shibuya (`sn: 2102`, `scn13_shibuya`) mediante teclado y ratón (WASD y control direccional).
2. **NPCs y Multitud Operativos:**
   - La población de la ciudad, transeúntes y NPCs con lógica interactiva pueblan la escena y responden al jugador.
3. **Diálogos y Cinemáticas Activas:**
   - Al aproximarse e interactuar con los NPCs, el sistema de interacción Lua dispara los diálogos contextuales y activa las cinemáticas in-engine correspondientes sin interrupciones ni excepciones bloqueantes.
4. **Infraestructura de Red y Compuertas Resueltas:**
   - Transporte TCP con framing de 8 bytes y cifrado RC4 bidireccional estable.
   - Handshake Protobuf2 (`CSLogin`, `CSLoginGate`, `CSQueryCharacters`, `CSCharacterLogin`, `SCInitData`) y subsistemas de queries (12 mensajes manejados) funcionando de forma armónica.
   - Cero desconexiones, cero errores `updateWeakCheck`.
5. **Evidencia Documental Registrada:**
   - Capturas de pantalla generadas durante la sesión de juego:
     - `D:\secret\logs\Screenshot 2026-11-15 072915.png`
     - `D:\secret\logs\Screenshot 2026-11-15 072928.png`
     - `D:\secret\logs\Screenshot 2026-11-15 072935.png`
     - `D:\secret\logs\Screenshot 2026-11-15 072954.png`
     - `D:\secret\logs\Screenshot 2026-11-15 072959.png`
   - Registro masivo de actividad en `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\log_2026_11_15.log` (74 MB de eventos de gameplay en vivo).

---

## 8. Verificación de Integridad Binaria (`Rules.md`)

Hashes SHA-256 auditados antes y después de las operaciones:
- `client\pc\GameAssembly.dll`: `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` (100% Idéntico)
- `client\pc\P5X.exe`: `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` (100% Idéntico)
- `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat`: `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` (100% Idéntico)
- `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll`: `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` (100% Idéntico)

---

## 9. Siguiente Fase de Desarrollo (Propuesta de Reanudación)

1. **Mapeo de CS\*/SC\* de Movimiento, Interacción y Misiones:**
   - Auditar en logs los paquetes emitidos al caminar/correr y al interactuar con puntos de interés y NPCs.
2. **Combate Stub:**
   - Responder la intención de habilidad del jugador (`CSRoundSkillList` 1325 / `CSRoundSetSkill` 1337; previamente hipotetizado como 2722) con `SCFightRoundBattleSkill` (1327, previamente 2723) y `DRoundSkillResult` mínimo (campo obligatorio `playId = 24`) para validar el flujo de encuentros por turnos en metaverso o misiones.
3. **Persistencia Local (SQLite):**
   - Implementar base de datos local SQLite para guardar estado de personaje, posición (`posNow`), progreso de misiones e inventario.
4. **Contenido de Diálogos y Misiones:**
   - Enriquecer los manejadores de misiones y tablas de diálogos locales para dar soporte a la progresión de historia.
