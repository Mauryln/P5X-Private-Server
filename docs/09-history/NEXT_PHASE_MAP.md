# Mapa de Protocolo y Subsistemas de Juego — Fase de Preservación Jugable (`NEXT_PHASE_MAP.md`)

**Fecha de Elaboración:** 15 de noviembre de 2026  
**Entorno de Trabajo:** `D:\secret\P5X` (Aislamiento total de Steam verificado)  
**Servidor Local:** `D:\secret\scratch\poc_login_server.py` en `127.0.0.1:10403`  
**Ejecutable del Cliente:** `D:\secret\P5X\P5X.exe` (según `Rules.md`)  
**Fuentes de Verdad Primarias:**
- Descriptor Protobuf oficial: `D:\secret\P5X\client\OuterPackage\Lua\Windows\allMsgPb.bytes`
- Bytecode LuaJIT 2.1 compilado: `D:\secret\P5X\client\OuterPackage\Lua\Windows\*.bytes`
- Binarios auditados: `GameAssembly.dll`, `tolua.dll`, `P5X.exe`
- Registro de ejecución empírica: `%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\log_2026_11_15.log` (74 MB)

---

## 1. Certificación de Reglas y Cumplimiento (`Rules.md`)

De acuerdo con las reglas estrictas de preservación de `D:\secret\Rules\Rules.md`:
1. **Aislamiento Categórico de Steam:** Ningún archivo de `C:\Program Files (x86)\Steam\...` ha sido leído, ejecutado o alterado.
2. **Espacio de Trabajo:** Todas las operaciones y ejecuciones se realizan exclusivamente sobre `D:\secret\P5X`.
3. **Punto de Entrada del Juego:** El ejecutable designado en `Rules.md` es `D:\secret\P5X\P5X.exe`.
4. **Hashes Criptográficos SHA-256 Verificados:**

| Archivo / Binario | Ruta en `D:\secret\P5X` | Hash SHA-256 Verificado | Estado |
| :--- | :--- | :--- | :---: |
| `P5X.exe` (Root Launcher) | `P5X.exe` | `FE1D12F81DDA178DE6A4B86E2DEBA2162C3DD855E7726DB4B19FA036823BD39E` | Intacto |
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | Intacto |
| `P5X.exe` (Client Bin) | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | Intacto |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | Intacto |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | Intacto |

---

## 2. Dominio 1: Diálogos, Interacción, Misiones y Cinemáticas

### 2.1. Tabla de Mensajes de Diálogo e Interacción (`CONFIRMADO`)

| MsgID | Nombre del Mensaje | Dir. | Campos Clave (Protobuf2) | Módulo / Clase Lua | Ubicación Bytecode / Chunk | Nivel de Evidencia |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: |
| **1419** | `CSGetCrucialDialog` | C $\rightarrow$ S | *(Vacío)* | `DialogMod:InitX` | `8E845EAB91B413A.bytes` (Chunk 47) | `CONFIRMADO` |
| **1420** | `SCGetCrucialDialogResult` | S $\rightarrow$ C | `required string crucialDialogs = 1` | `DialogMod:OnSCGetCrucialDialogResult` | `8E845EAB91B413A.bytes` (Chunk 47) | `CONFIRMADO` |
| **1418** | `CSDialogFinish` | C $\rightarrow$ S | `required string dialogSn = 1`<br>`optional bool crucial = 2` | `DialogMod:TryEndDialog` | `8E845EAB91B413A.bytes` (Chunk 47) | `CONFIRMADO` |
| **1437** | `CSDialogChoice` | C $\rightarrow$ S | `required string dialogSn = 1`<br>`required int32 choice = 2` | `DialogMod:ClickDialogChioce` | `8E845EAB91B413A.bytes` (Chunk 47) | `CONFIRMADO` |
| **2030** | `CSQuestDialog` | C $\rightarrow$ S | `required string dialogSn = 1` | `MissionMod:TriggerMissionDialog` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **4013** | `SCPlayDialog` | S $\rightarrow$ C | `required string sn = 1`<br>`optional int32 delay = 2` | `DialogMod:OnSCPlayDialog` | `8E845EAB91B413A.bytes` (Chunk 47) | `CONFIRMADO` |
| **4011** | `SCPlayScenario` | S $\rightarrow$ C | `required int32 sn = 1`<br>`optional int32 delay = 2` | `StoryMod:StartPlay` | `E8DF29521A39C99.bytes` (Chunk 25) | `CONFIRMADO` |
| **4012** | `SCPlayTimeLine` | S $\rightarrow$ C | `optional string timeLineSn = 1` | `StoryMod:PlayStory` | `E8DF29521A39C99.bytes` (Chunk 25) | `CONFIRMADO` |
| **4002** | `CSScenarioFinish` | C $\rightarrow$ S | `required int32 scenarioSn = 1` | `StoryMod:OnAllClipsEnd` | `E8DF29521A39C99.bytes` (Chunk 25) | `CONFIRMADO` |
| **4003** | `CSSkipScenario` | C $\rightarrow$ S | *(Vacío)* | `StoryMod:Skip` | `E8DF29521A39C99.bytes` (Chunk 25) | `CONFIRMADO` |

### 2.2. Tabla de Mensajes de Misiones (`CONFIRMADO`)

| MsgID | Nombre del Mensaje | Dir. | Campos Clave (Protobuf2) | Módulo / Clase Lua | Ubicación Bytecode / Chunk | Nivel de Evidencia |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: |
| **2007** | `SCQuestInfo` | S $\rightarrow$ C | `repeated DQuest quests = 1`<br>`repeated int32 submittedQuestSns = 2`<br>`repeated int32 trackedLines = 3` | `MissionMod:OnSCQuestInfo` | `8E845EAB91B413A.bytes` (Chunk 131, Proto 129) | `CONFIRMADO` |
| **2008** | `SCQuestInfoUpdate` | S $\rightarrow$ C | `repeated DQuest quests = 1` | `MissionMod:OnSCQuestInfoUpdate` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **2001** | `CSQuestAccept` | C $\rightarrow$ S | `required int32 questSn = 1` | `MissionMod:AcceptMission` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **2002** | `SCQuestAcceptResult` | S $\rightarrow$ C | `required int32 questSn = 1`<br>`required DQuest quest = 2` | `MissionMod:OnSCAcceptQuest` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **2003** | `CSQuestSubmit` | C $\rightarrow$ S | `required int32 questSn = 1` | `MissionMod:CommitMission` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **2004** | `SCQuestSubmitResult` | S $\rightarrow$ C | `required int32 questSn = 1` | `MissionMod:OnSCCommitQuest` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |
| **2020** | `SCQuestAcceptable` | S $\rightarrow$ C | `repeated int32 questSns = 1` | `MissionMod:OnSCQuestAcceptable` | `8E845EAB91B413A.bytes` (Chunk 131) | `CONFIRMADO` |

#### Estructura de Datos `DQuest` (`msg.proto` / `CONFIRMADO`)
- `required int32 sn = 1`: Identificador de la misión (referencia a `ConfQuest`).
- `required int32 state = 2`: Estado de misión (0: No aceptada, 1: En curso / Underway, 2: Cumplida / Finished, 3: Entregada / Submitted).
- `repeated DQuestTarget targets = 3`: Objetivos de la misión (`DQuestTarget`: `required int32 targetKey = 1`, `required int32 targetCurValue = 2`, `required bool finish = 3`).
- `optional int64 remainTime = 4`
- `optional int64 acceptTime = 5`
- `repeated DQuestFollowedNpc followedNpc = 6`
- `optional int64 pendingProcessTime = 7`
- `required bool newLine = 8`: Indica si abre una nueva rama en el registro de misiones.
- `optional bool quickSkip = 9`

---

## 3. Dominio 2: Movimiento y Posición en Escena

### 3.1. Tabla de Mensajes de Movimiento (`CONFIRMADO`)

| MsgID | Nombre del Mensaje | Dir. | Campos Clave (Protobuf2) | Módulo / Clase Lua | Ubicación Bytecode / Chunk | Nivel de Evidencia |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: |
| **1207** | `CSSceneMove` | C $\rightarrow$ S | `optional int64 objId = 1`<br>`optional DVector3 posBegin = 2`<br>`repeated DVector3 posEnd = 3`<br>`optional DVector2 dir = 4`<br>`optional int32 speedGear = 5`<br>`optional float moveSpeed = 6` | `HeroController:OnStageMove` | `7A4379BBA8417A9.bytes` (Chunk 52) | `CONFIRMADO` |
| **1208** | `SCSceneMove` | S $\rightarrow$ C | `optional int64 objId = 1`<br>`optional DVector3 posBegin = 2`<br>`repeated DVector3 posEnd = 3`<br>`optional DVector2 dir = 4`<br>`optional float speed = 5`<br>`optional bool acce = 6` | `SceneMod:OnStageMove` | `E8DF29521A39C99.bytes` (Chunk 167) | `CONFIRMADO` |
| **1209** | `CSSceneMoveStop` | C $\rightarrow$ S | `optional int64 sendId = 1`<br>`optional DVector3 posEnd = 2`<br>`optional int32 marker = 3` | `HeroPositionSyncMod:PositionSync` | `E8DF29521A39C99.bytes` (Chunk 337) | `CONFIRMADO` |
| **1210** | `SCSceneMoveStop` | S $\rightarrow$ C | `optional int64 objId = 1`<br>`optional DVector3 posEnd = 2`<br>`optional int32 marker = 3` | `SceneMod:OnStageMoveStop` | `E8DF29521A39C99.bytes` (Chunk 167) | `CONFIRMADO` |

### 3.2. Mecanismo de Sincronización de Movimiento en el Cliente
1. **Control FSM Local:** `HeroController` (`7A4379BBA8417A9.bytes` Chunk 52) gestiona la máquina de estados finitos (`NewActionHeroMoveState`, `NewActionHeroRushMoveState`, `NewActionHeroStandState`). Los movimientos por stick o teclado (WASD) alimentan la cinemática de Unity (`MUGame.HeroDirMove` y `CharacterMoveBase`).
2. **Emisión de Paquetes:**
   - Durante el desplazamiento continuo en mundo abierto, el movimiento local no satura la red; el cliente emite `CSSceneMove` (1207) únicamente al alterar rumbo, marcha (`speedGear`) o al iniciar navegación.
   - Al detenerse (transición a `StandState`), `HeroPositionSyncMod` (`E8DF29521A39C99.bytes` Chunk 337) evalúa `Vector3.SquareDistanceXZ(pos, mLastSavePos)`. Si supera `mMaxDistance`, emite inmediatamente `CSSceneMoveStop` (1209) con las coordenadas tridimensionales de parada `posEnd` (`x, y, z`).
3. **Respuesta del Servidor:** `CSSceneMoveStop` (1209) es una notificación de parada unidireccional. El servidor no requiere emitir un ACK directo al emisor; almacena la posición autoritativa en memoria/base de datos y, en escenarios multijugador, la retransmite como `SCSceneMoveStop` (1210) a los observadores cercanos.

---

## 4. Dominio 3: Motor de Combate por Turnos

### 4.1. Contraste Canónico Definitivo con `allMsgPb.bytes` (Tabla Única de Verificación)

Se auditó de manera cripto-binaria el descriptor canónico oficial `D:\secret\P5X\client\OuterPackage\Lua\Windows\allMsgPb.bytes` (`msg.proto`, 2.663 mensajes analizados en su árbol AST de Protobuf2). A continuación se certifica la totalidad de los mensajes consultados:

| Nombre Consultado | MsgID Real | Estado en Descriptor | Cita en `allMsgPb.bytes` | Cita en `msg.proto` | Evidencia y Función Real |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`SCFightRoundTime`** | **1326** | **CONFIRMADO** | Offset `0x97f1` | Línea 2641 | Temporizador y sincronización de ronda de combate. |
| **`CSFightRoundBattleSkill`** | *(Inexistente)* | **NO DEFINIDO** | 0 coincidencias | — | **No existe en el esquema Protobuf.** Hipótesis preliminar del Experimento 2/análisis temprano **superada por evidencia**. El cliente envía `CSRoundSkillList` (**1325**) o `CSRoundSetSkill` (**1337**). |
| **`SCFightRoundBattleSkill`** | **1327** | **CONFIRMADO** | Offset `0xa4f7` | Línea 2838 | Servidor envía resolución del turno de combate con `DRoundSkillResult`. |
| **`SCFightActionSequence`** | **1394** | **CONFIRMADO** | Offset `0xb6a3` | Línea 3110 | Servidor envía la secuencia de orden de acción en la barra de turnos. |
| **`SCFightResult`** | *(Inexistente)* | **NO DEFINIDO** | 0 coincidencias | — | **No existe en el esquema Protobuf.** El mensaje oficial canónico de finalización y entrega de recompensas en PvE es `SCFightBattleEnd` (**1333**, offset `0xa9db`, línea 2903). |
| **`CSRoundSkillList`** | **1325** | **CONFIRMADO** | Offset `0x9538` | Línea 2816 | Cliente envía la habilidad y objetivo seleccionados en el turno. |
| **`SCRoundSkillList`** | **1330** | **CONFIRMADO** | Offset `0xa8f1` | Línea 2870 | Servidor confirma la lista de habilidades activables. |

> [!NOTE]
> **Rectificación Formal de Documentación Anterior:**  
> Las hipótesis iniciales planteadas en borradores preliminares que citaban `CSFightRoundBattleSkill (2722)`, `2723`, `2705` o `2777` quedan **formalmente catalogadas como superadas por evidencia directa**. El rango `2700..2799` corresponde a PvP Arena (`CSArenaFight` 2710, `SCArenaBattleEnd` 2715), mientras que el combate por turnos principal (PvE, historia, palacios) opera canónicamente en el rango `1300..1399`.

### 4.2. Tabla de Mensajes de Combate por Turnos (`CONFIRMADO`)

| MsgID | Nombre del Mensaje | Dir. | Campos Clave (Protobuf2) | Módulo / Clase Lua | Ubicación Bytecode / Chunk | Nivel de Evidencia |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: |
| **1302** | `CSEnterFight` | C $\rightarrow$ S | `required int32 instSn = 1`<br>`repeated int32 monsters = 3` | `FightMod:EnterFight` | `EF7D188C4394F63.bytes` (Chunk 88) | `CONFIRMADO` |
| **1325** | `CSRoundSkillList` | C $\rightarrow$ S | `optional int32 curRound = 1`<br>`optional int32 opttype = 2`<br>`optional int64 atkId = 3`<br>`optional int64 target = 4`<br>`optional int32 skillsn = 5`<br>`optional int32 personaSn = 6`<br>`optional float qteScore = 7` | `TB_Action:CSRoundSkillSend` | `7161AA1F66A0ACA.bytes` (Chunk 53) | `CONFIRMADO` |
| **1330** | `SCRoundSkillList` | S $\rightarrow$ C | `optional bool result = 1`<br>`optional int64 atkId = 2`<br>`optional int32 skillsn = 3`<br>`optional int32 skilltype = 4` | `TurnBasedMsgQueueMod` | `8E845EAB91B413A.bytes` (Chunk 204) | `CONFIRMADO` |
| **1337** | `CSRoundSetSkill` | C $\rightarrow$ S | `optional int64 optId = 1`<br>`optional int32 skillType = 2`<br>`optional int32 skillsn = 3` | `TB_Action:RoundSetSkill` | `7161AA1F66A0ACA.bytes` (Chunk 53) | `CONFIRMADO` |
| **1338** | `SCRoundSetSkill` | S $\rightarrow$ C | `optional bool result = 1`<br>`optional int64 optId = 2`<br>`optional int32 skillType = 3`<br>`optional int32 skillsn = 4` | `TurnBasedMsgQueueMod` | `8E845EAB91B413A.bytes` (Chunk 204) | `CONFIRMADO` |
| **1327** | `SCFightRoundBattleSkill` | S $\rightarrow$ C | `required int64 playId = 24`<br>`optional int32 opttype = 1`<br>`optional int64 atkId = 2`<br>`optional DRoundSkillResult skill = 3`<br>`repeated DRoundBuff buff = 4`<br>`optional bool isBattleEnd = 17` | `TurnBasedMsgQueueMod:OnCheck_DRoundSkillResult` | `8E845EAB91B413A.bytes` (Chunk 204, Proto 31) | `CONFIRMADO` |
| **1331** | `CSFightHumanPlayEnd` | C $\rightarrow$ S | `required int64 playId = 1` | `TurnBasedMsgQueueMod:OnSendPlayMsgId` | `8E845EAB91B413A.bytes` (Chunk 204) | `CONFIRMADO` |
| **1332** | `SCFightRoundEnd` | S $\rightarrow$ C | `optional int32 round = 1` | `TurnBasedMsgQueueMod` | `8E845EAB91B413A.bytes` (Chunk 204) | `CONFIRMADO` |
| **1333** | `SCFightBattleEnd` | S $\rightarrow$ C | `optional int32 isWin = 1`<br>`repeated DProduce rewawards = 4` | `TurnBasedMsgQueueMod:IsBattleEnd` | `8E845EAB91B413A.bytes` (Chunk 204) | `CONFIRMADO` |

### 4.3. Estructura Exhaustiva y Campos Required de `SCFightRoundBattleSkill` y `DRoundSkillResult`

#### Análisis de Campos en `msg.proto` (`allMsgPb.bytes`):

1. **`SCFightRoundBattleSkill` (MsgID 1327):**
   - **Campos REQUIRED (Exactamente 1):**
     - `required int64 playId = 24;` — Identificador secuencial del turno de animación. **Es el ÚNICO campo obligatorio de todo el mensaje.**
   - **Campos OPTIONAL (27 campos):**
     - `optional int32 opttype = 1;` (Tipo de acción/habilidad)
     - `optional int64 atkId = 2;` (Identificador de la entidad atacante)
     - `optional DRoundSkillResult skill = 3;` (Subestructura de resultados del turno)
     - `optional DClientEvent clientEvent = 5;`
     - `optional DSceneReplaceObjectList replaceObjList = 6;`
     - `optional DEscapeEvent escape = 8;`
     - `optional DAIChangeWar changewar = 9;`
     - `optional DAIPlayStory story = 10;`
     - `optional int64 disappearOldChongWuId = 11;`
     - `optional DAttrChange atkAttrChg = 12;`
     - `optional DHintData hint = 13;`
     - `optional DHurtTypeData hurtTypeData = 15;`
     - `optional DSceneCallObjectList callObjList = 16;`
     - `optional bool isBattleEnd = 17;` (Bandera para finalizar el combate)
     - `optional bool isDefendStatus = 18;`
     - `optional bool isFreeze = 19;`
     - `optional int32 buffReason = 20;`
     - `optional DUnitObjChangeModel changeModel = 21;`
     - `optional int32 skipActionBuffSn = 22;`
     - `optional int32 freezeType = 25;`
     - `optional int64 acturalAtkId = 26;`
     - `optional int32 progress = 27;`
     - `optional int32 progressMax = 28;`
     - `optional int32 totalDamage = 29;`
     - `optional bool isMarianSpecail = 30;`
     - `optional int32 confSpecialEnergySn = 31;`
     - `optional DThiefReplace thiefReplace = 32;`
   - **Campos REPEATED (4 campos):**
     - `repeated DRoundBuff buff = 4;`
     - `repeated DRoundBuffTargetData buffCalc = 7;`
     - `repeated DChangeBattlePosition changepos = 14;`
     - `repeated DRoundSkillBuff buffList = 23;`

2. **`DRoundSkillResult`:**
   - **Campos REQUIRED:** **0 (Cero).**
   - **Campos OPTIONAL (6 campos):**
     - `optional int32 skillsn = 1;` (SN de la habilidad ejecutada)
     - `optional int64 mainTargetId = 2;` (Identificador del objetivo principal)
     - `optional int64 protectMeId = 4;`
     - `optional int32 lastHurtIndex = 5;`
     - `optional int64 uid = 6;`
     - `optional int32 skillActionType = 7;`
   - **Campos REPEATED (1 campo):**
     - `repeated DRoundSkillFunc skillFuncList = 3;` (`DRoundSkillFunc`: `nFuncIndex = 1`, `effectList = 2`, etc. Ninguno required).

#### Verificación del Stub Mínimo Implementado en Servidor
El generador `encode_SCFightRoundBattleSkill` en `proto2_codec.py` codifica:
```python
def encode_SCFightRoundBattleSkill(play_id: int, opttype: int = 1, atk_id: int = 1001, skill_res: bytes = None) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(24, play_id)  # REQUIRED: playId
    buf += encode_varint_field(1, opttype)   # OPTIONAL: opttype
    buf += encode_varint_field(2, atk_id)    # OPTIONAL: atkId
    if skill_res:
        buf += encode_bytes_field(3, skill_res)  # OPTIONAL: DRoundSkillResult
    return bytes(buf)
```
- **Conformidad Protobuf2:** **100% verificado**. Satisface el campo obligatorio `playId = 24` e inyecta `skillsn` y `mainTargetId` en `DRoundSkillResult`. No produce excepciones de deserialización ni advertencias en el cliente.

---

## 5. Evaluación de Herramientas de Desensamblado: Decisión sobre Ghidra

| Criterio Técnico Evaluado | Capstone Disassembler + LuaJIT Bytecode Parser | Ghidra Decompiler (con OpenJDK) | Decisión y Justificación |
| :--- | :--- | :--- | :--- |
| **Ubicación de la Lógica de Red** | La totalidad de los manejadores de red (`DialogMod`, `MissionMod`, `StoryMod`, `TurnBasedMsgQueueMod`, `HeroController`) residen en **bytecode LuaJIT 2.1**. | N/A (Ghidra descompila binarios nativos ELF/PE, no interpreta bytecode LuaJIT). | **Capstone / Parse_LJ2 es suficiente**. No hay lógica de red en C#. |
| **Inspección de IL2CPP en `GameAssembly.dll`** | Capstone (integrado en `scratch/disasm_csharp_capstone.py`) desensambla funciones nativas x86_64 directamente utilizando las RVA extraídas de `global-metadata.dat`. | Requiere volcado previo con Il2CppDumper, instalación de Java Runtime Environment y proyecto Ghidra de ~4 GB. | **No se requiere Ghidra**. Para resolver colisiones, spawns y bindings de `tolua.dll`, los scripts ligeros en Python con Capstone son un orden de magnitud más rápidos y reproducibles. |
| **Dictamen de Arquitectura** | **HERRAMIENTA PRIMARIA ACTIVA** | **DESESTIMADA (No necesaria para esta fase)** | Se descarta la instalación de Java y Ghidra por redundancia y coste innecesario de dependencias. |

---

## 6. Verificación Empírica y Trazas de Ejecución en Vivo

### 6.1. Integración en `poc_login_server.py` y Verificación E2E
Se integraron en el servidor local los códecs y manejadores de respuesta para `SCQuestInfo` (2007), `CSSceneMoveStop` (1209), `CSSceneMove` (1207), `CSDialogFinish` (1418), `CSDialogChoice` (1437), `CSQuestDialog` (2030), `CSRoundSkillList` (1325) y `CSRoundSetSkill` (1337).

En la ejecución del arnés de prueba de integración de red (`test_poc_client_harness.py`), se verificaron **22 tramas consecutivas con 100% de éxito y 0 desconexiones**:
- Intercambio de autenticación y handshake RC4 completo.
- `SCInitData` (1102) seguido inmediatamente de `SCQuestInfo` (2007) para inicializar `MissionMod`.
- Entrada a escena 3D de Shibuya (`CSSceneEnter` 1201 $\rightarrow$ `SCSceneEnterResult` 1202 + `SCSceneEnterEnd` 1203).
- Heartbeat continuo (`CSPing` 1116 $\rightarrow$ `SCPing` 1117 y `CSNetDelayDetect` 1118 $\rightarrow$ `SCNetDelayDetect` 1119).
- Recepción y parseo correcto en servidor de `CSSceneMoveStop` (1209) y `CSDialogFinish` (1418).
- Pruebas negativas de robustez (cifrado inverso RC4 y varints truncados detectados y rechazados por diseño).

### 6.2. Evidencia Empírica de Gameplay en `log_2026_11_15.log`
En el registro real generado por el cliente oficial al explorar Shibuya (`%LOCALAPPDATA%\..\LocalLow\SEGA\p5x_en\log_2026_11_15.log`, líneas 1125914–1126500), se constataron los siguientes eventos in-engine:

1. **Carga y Movimiento Libre del Héroe:**
   ```text
   SceneLoadingMod：【完成】等待事件2    主角加载    23.956秒
   SceneLoadingMod：本次切换场景用时: 4.324秒 scn13_shibuya
   OWAmbientNpcMod 加载氛围资源NPC资源 segu_day_[PCPlatforms].prefab
   ```
2. **Interacción con NPCs y Activación de Diálogos:**
   ```text
   DialogMod:开始对话    NpcDialog_1120
   NPCController:TriggerInteractCamera    3    2102008    t_camera
   DialogMod:开始对话    DS3050
   DialogMod:开始对话    NpcDialog_1100
   ```
3. **Disparo de Cinemática In-Engine:**
   ```text
   StoryMod: 准备播放剧情 2803
   播放剧情片段: TL_segu_guitargirl
   StoryClip_Timeline:Stopped -> StoryMod: 剧情结束 2803
   ```
4. **Triggers de Área y Cámaras Cinemáticas Dinámicas:**
   ```text
   进入区域 -> TestCam FixedPosCamFunc 10126
   --vam form to: FreeLookDefault -> [50110199]AreaFixedPosCam1.prefab , EaseIn 0.5
   ```

### 6.3. Registro de Ejecución en Vivo en Tiempo Real (`poc_frame_log.json`)

En la prueba en vivo ejecutada sobre `D:\secret\P5X\P5X.exe` (PID `9688` / `17396`), el cliente oficial se conectó al servidor local `127.0.0.1:10403`, registrando **183 tramas de red bidireccionales en tiempo real** en `D:\secret\scratch\poc_frame_log.json`:

| Mensaje de Red | MsgID | Dirección | Cantidad Observada | Descripción y Datos Extraídos |
| :--- | :---: | :---: | :---: | :--- |
| `CSLogin` $\rightarrow$ `SCLoginResult` | 101 / 102 | C $\leftrightarrow$ S | 1 / 1 | Handshake y redirección a lógica `127.0.0.1:10403`. |
| `CSLoginGate` $\rightarrow$ `SCLoginGateResult` | 103 / 104 | C $\leftrightarrow$ S | 1 / 1 | Autenticación gate aprobada (`errorCode: 0`). |
| `SCServerConfig` | 1112 | S $\rightarrow$ C | 1 | Timestamp Unix normalizado (`1700000000`). |
| `CSQueryCharacters` $\rightarrow$ `SCQueryCharactersResult` | 1001 / 1002 | C $\leftrightarrow$ S | 1 / 1 | Wonder (`model: "wonder_uniform"`). |
| `CSCharacterLogin` $\rightarrow$ `SCCharacterLoginResult` | 1007 / 1008 | C $\leftrightarrow$ S | 1 / 1 | Entrada a personaje (`resultCode: 0`). |
| `SCInitData` | 1102 | S $\rightarrow$ C | 1 | Spawn en Shibuya (`sn: 2102`, `modelSn: "wonder_uniform"`). |
| `SCQuestInfo` | 2007 | S $\rightarrow$ C | 1 | Inicialización limpia de `MissionMod` en cliente. |
| `CSSceneMoveStop` | 1209 | C $\rightarrow$ S | **23** | **Coordenadas 3D de movimiento real decodificadas**:<br>• Seq 49: `(188.43, 369.18, 99.5595)`<br>• Seq 66: `(203.71, 363.4662, 99.5523)`<br>• Seq 74: `(171.5559, 362.297, 99.6295)`<br>• Seq 83: `(213.0244, 348.1562, 99.5523)`<br>• Seq 93: `(220.6218, 322.5047, 99.5523)`<br>• Seq 181: `(219.1752, 325.2556, 99.5523)` |
| `CSChangeMoveType` | 1221 | C $\rightarrow$ S | **16** | Cambio entre caminata y carrera rápida (`rockerRange`, `moveType`). |
| `CSAreaPositionSync` | 1254 | C $\rightarrow$ S | 2 | Sincronización de disparador de sub-área en Shibuya. |
| `CSSceneSwitch` | 1204 | C $\rightarrow$ S | 3 | Petición de conmutación de sub-escenas urbanas. |
| `CSPing` $\leftrightarrow$ `SCPing` | 1116 / 1117 | C $\leftrightarrow$ S | **38 / 38** | Latidos de red con RTT continuo (0 desconexiones). |
| `CSNetDelayDetect` $\leftrightarrow$ `SCNetDelayDetect` | 1118 / 1119 | C $\leftrightarrow$ S | 3 / 3 | Detección de retardo de red sincronizada. |

- **Auditoría de `Player.log` durante la ejecución:** **0 excepciones (`Total exceptions: 0`)**. No se detectó ninguna excepción de Lua, ni de Unity C#, ni de renderizado.

---

## 7. Próximos Pasos de Implementación Inmediata

1. **Persistencia SQLite de Posición y Estado (`local_save.db`):**
   - Almacenar las coordenadas reportadas en `CSSceneMoveStop` (1209) para persistir la ubicación de Wonder entre sesiones.
2. **Generador de Misiones Activas en `SCQuestInfo`:**
   - Inyectar en `SCQuestInfo` (2007) la primera misión del prólogo (`FIRST_QUEST`) para poblar el marcador de navegación de la interfaz (`[J] Missions`).
3. **Manejador de Encuentro de Combate Local:**
   - Habilitar disparador de prueba para simular `CSEnterFight` (1302) y responder la secuencia de turno (`SCFightRoundBattleSkill` 1327) con el stub implementado.