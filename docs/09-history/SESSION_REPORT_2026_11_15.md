# Informe de Diagnóstico y Cierre de Sesión — P5X Local Emulation

**Fecha:** 15 de noviembre de 2026  
**Entorno de Trabajo:** `D:\secret\P5X` (Modo Preservación / Local Offline)  
**Servidor Local:** `D:\secret\scratch\poc_login_server.py` en `127.0.0.1:10403`  
**Ejecutables Probados:** `D:\secret\P5X\P5X.exe` (Launcher) $\rightarrow$ `D:\secret\P5X\client\pc\P5X.exe`  
**Auditoría de Integridad:** Cumplimiento estricto de `D:\secret\Rules\Rules.md`  

---

## 1. Certificación de Reglas y Cumplimiento (`Rules.md`)

De acuerdo con las reglas duras establecidas en `D:\secret\Rules\Rules.md`:
1. **Aislamiento Total de Steam:** No se interactuó, leyó, ejecutó ni modificó `C:\Program Files (x86)\Steam\...` bajo ninguna circunstancia.
2. **Espacio de Trabajo Exclusivo:** Todo el trabajo se ejecutó de forma aislada en `D:\secret\P5X` y `D:\secret\scratch`.
3. **Verificación Criptográfica de Integridad:** Se verificaron los hashes SHA-256 de los 5 binarios y metadatos del juego, manteniéndose idénticos a los del estado original:

| Binario / Metadata | Ubicación Canónica | Hash SHA-256 Verificado | Estado |
|---|---|---|:---:|
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **INTACTO** |
| `P5X.exe` (Cliente) | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | **INTACTO** |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **INTACTO** |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | **INTACTO** |
| `P5X.exe` (Launcher) | `P5X.exe` | `FE1D12F81DDA178DE6A4B86E2DEBA2162C3DD855E7726DB4B19FA036823BD39E` | **INTACTO** |

---

## 2. Síntoma Reportado y Objetivos de la Sesión

- **Estado previo confirmado:** Login real funcional, escena 3D de Shibuya (`sn: 2102`), audio y movimiento libre del personaje, diálogos y cinemáticas con NPCs operativas.
- **Problema reportado:** Ausencia total de interfaz de usuario (HUD) y menús. En pantalla aparecía la indicación de depuración y las etiquetas inferiores `[M] Map` y `[J] Mission`, pero al presionar dichas teclas no ocurría nada. El combate no podía iniciarse por falta de menús accesibles.
- **Objetivo de la sesión:** Diagnosticar la causa raíz a nivel bytecode e ingeniería inversa, solucionar el fallo desde el servidor emulador sin modificar binarios ni assets del juego, y documentar la solución.

---

## 3. Diagnóstico Forense de `Player.log`

Al inspeccionar `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\Player.log`:

```text
802: ====SceneMod: SCSceneEnterResult ====
803: ====SceneMod: OnEnterStage1 ====
806: ----CheckHeroServerPos error ------ 2102 [339.10,99.56,203.11]
807: LuaException: [string "ServerTimeMod"]:0: attempt to index a nil value
808: stack traceback:
809: 	[string "ServerTimeMod"]: in function 'GetOpenServerDay0'
810: 	[string "LoginMod"]: in function 'CheckLoginOperation'
811: 	[string "LoginMod"]: in function 'OnFirstEnterStage'
812: 	[string "LoginMod"]: in function 'OnConfEvent'
813: 	[string "ModMgr"]: in function 'OnEvent'
814: 	[string "events2"]: in function 'Brocast'
815: 	[string "SceneMod"]: in function 'SceneEnterResult'
816: 	[string "SceneMod"]: in function 'OnSCSceneEnterResult'
```

Y en la descarga de activos de `SceneLoadingMod`:
```text
Release Asset Error: UI-zhujiemian-ditu-map_EN.prefab is null. 1198.
Release Asset Error: UI-zhujiemian-youcegongnengqu01_EN.prefab is null. 1198.
```

### Mecanismo de Fallo:
1. `SceneMod:OnSCSceneEnterResult` (MsgID 1202) llama a `events2:Brocast(EVENT_STAGE.OnFirstEnterStage)`.
2. El despachador de eventos invoca a `LoginMod:OnFirstEnterStage`, que a su vez llama a `CheckLoginOperation()`.
3. `CheckLoginOperation()` ejecuta `ServerTimeMgr:GetOpenServerDay0()`.
4. Al fallar `GetOpenServerDay0()` con `LuaException: attempt to index a nil value`, la ejecución de `events2:Brocast` se cancela de forma abrupta.
5. Los módulos posteriores registrados en dicho evento (encargados de instanciar los prefabs `UI-zhujiemian-ditu-map_EN.prefab` y `UI-zhujiemian-youcegongnengqu01_EN.prefab` y enlazar las acciones de teclado `M` y `J`) **nunca fueron ejecutados**.

---

## 4. Descompilación y Causa Raíz a Nivel Bytecode

Se realizó un análisis exhaustivo del bytecode LuaJIT 2.1 utilizando `jit.util` y el motor nativo `tolua.dll`:

### 4.1. Descompilación de `ServerTimeMod:GetOpenServerDay0` (`07B3A247F1ADE14.bytes[82]`)
```lua
function ServerTimeMod:GetOpenServerDay0()
    local t1 = OSDate("*t", self:GetOpenServerTime()) -- self.mOpenServerTime es 0
    local d1 = OSTime({year = t1.year, month = t1.month, day = t1.day})
    local t2 = OSDate("*t", self:GetCurrentServerTime())
    local d2 = OSTime({year = t2.year, month = t2.month, day = t2.day})
    local diff = d2 - d1
    return Mathf.Round(diff / 86400) + 1
end
```
En la instrucción `0009: TGETS r5, r1, 'year'`, si `t1` es `nil`, Lua lanza `attempt to index a nil value`.

### 4.2. Descompilación de `OSDate` (`07B3A247F1ADE14.bytes[31]`)
```lua
function OSDate(fmt, timestamp)
    if timestamp == nil then timestamp = OSTime() end
    local r4 = os.date("*t", timestamp)
    local isdst = r4 and r4.isdst
    local offset
    if isdst then
        offset = TimeZoneDiff * 3600 - 3600
    else
        offset = TimeZoneDiff * 3600
    end
    local r2 = timestamp + offset
    return os.date(fmt, r2)
end
```

### 4.3. Descompilación de `LoginMod:OnSCLoginResult` (`E8DF29521A39C99.bytes[0]`)
En las instrucciones 0112–0130 de `LoginMod:OnSCLoginResult`:
```lua
if msg.zoneTime then
    local local_2010 = os.time({year=2010, month=1, day=1, hour=0, min=0, sec=0})
    _G.TimeZoneDiff = local_2010 - msg.zoneTime
else
    local local_2010 = os.time({year=2010, month=1, day=1, hour=0, min=0, sec=0})
    _G.TimeZoneDiff = local_2010 - 1262275200
end
```

### 4.4. La Anomalía Temporal
1. El emulador `poc_login_server.py` enviaba en `SCLoginResult` (102) el campo `zoneTime = 1700000000` (timestamp Unix de época 2023).
2. `LoginMod` calculó:
   $$\_G.TimeZoneDiff = 1262318400 - 1700000000 = -437.681.600 \text{ segundos} \quad (\approx -14 \text{ años})$$
3. Al invocar `ServerTimeMod:GetOpenServerDay0()`, `mOpenServerTime` era `0`.
4. `OSDate` calculó el tiempo ajustado:
   $$r2 = 0 + (-437.681.600) = -437.681.600 \quad (\text{año } 1956)$$
5. En la biblioteca de C de Microsoft Windows (`ucrtbase.dll` / `_localtime64_s`), cualquier timestamp negativo anterior a 1970 no es válido y la función `os.date` **retorna `nil`**.
6. `t1` se convirtió en `nil`, provocando que `t1.year` crasheara con `attempt to index a nil value` y derribara toda la secuencia de instanciación del HUD.

---

## 5. Correcciones Aplicadas en el Servidor Local

1. **`proto2_codec.py` (`encode_SCLoginResult`):**
   - Se modificó la firma para que `zoneTime` sea opcional (`Optional[int] = None`).
   - Si `zoneTime is None`, el campo tag 3 **no se incluye** en el paquete `SCLoginResult`.
   - Al no recibir `zoneTime`, `LoginMod` salta canónicamente a la rama `else` que evalúa contra la época de referencia 2010 (`local_2010 - 1262275200`), generando un offset positivo que nunca hace negativo el tiempo en Windows.

2. **`proto2_codec.py` (`encode_SCServerTime`):**
   - Se implementó el codificador para `SCServerTime` (MsgID 1136), que transporta `serverTime` en milisegundos (`int64`).

3. **`poc_login_server.py`:**
   - Se configuró `"zoneTime": None` en la respuesta `SCLoginResult` (102).
   - Se agregó la transmisión de `SCServerTime` (1136) tras `SCServerConfig` (1112) y tras `SCInitData` (1102), manteniendo el bias temporal `ServerTimeMgr.mServerTimeBiase` sincronizado de forma continua y limpia.

---

## 6. Validación Dinámica de la Corrección

Se reprodujo y verificó el comportamiento mediante `test_reproduce_exact_bug.py` utilizando `tolua.dll`:
- **Caso con Error (`TimeZoneDiff = -437681600`):**
  - `OSDate("*t", 0)` $\rightarrow$ `nil`
  - `ServerTimeMgr:GetOpenServerDay0()` $\rightarrow$ `false: chunk82:0: attempt to index a nil value` (Reproducción exacta).
- **Caso Corregido (`zoneTime = None` / `TimeZoneDiff = 43200`):**
  - `OSDate("*t", 0)` $\rightarrow$ `year: 1970`
  - `ServerTimeMgr:GetOpenServerDay0()` $\rightarrow$ `true: 1` (Éxito inmediato).

---

## 7. Documentación Actualizada

- [docs/RUNTIME_TEST_REPORT_2026_11_15.md](file:///D:/secret/docs/RUNTIME_TEST_REPORT_2026_11_15.md): Sección 10 agregada con el diagnóstico forense, descompilación de instrucciones y resolución.
- [docs/HANDLER_FIELD_CATALOG.md](file:///D:/secret/docs/HANDLER_FIELD_CATALOG.md): Entrada canónica de `SCServerTime` (MsgID 1136) incorporada con nivel de evidencia `CONFIRMADO`.
- [docs/SESSION_REPORT_2026_11_15.md](file:///D:/secret/docs/SESSION_REPORT_2026_11_15.md): Este informe integral de cierre de sesión.

---

## 8. Cierre de Servicios y Estado Final

- **Servidor Local:** Detenido y cerrado de forma segura (tarea `task-2282` cancelada). Puerto `127.0.0.1:10403` completamente liberado.
- **Procesos:** No hay procesos huérfanos ni tareas en segundo plano activas.
- **Integridad:** Los 5 binarios oficiales (`GameAssembly.dll`, `client\pc\P5X.exe`, `global-metadata.dat`, `steam_api64.dll`, `P5X.exe`) permanecen 100% intactos e inalterados.
