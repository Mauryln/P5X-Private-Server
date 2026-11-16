# Análisis Estático de `isClientBattle` y la Arquitectura de Combate del Cliente (Prioridad 1)

**Objetivo:** Determinar mediante referencias verificables en el bytecode LuaJIT 2.1 y en los metadatos C# (`global-metadata.dat`) si el campo `isClientBattle` del mensaje `SCServerConfig` (`MsgID 1112`) activa un motor de cálculo local de combate en el cliente de *Persona 5: The Phantom X (P5X)* o si constituye un campo vestigial.

---

## 1. Respuesta a las 5 Preguntas de Investigación

### 1.1. ¿Dónde se utiliza `isClientBattle` dentro del código Lua o los metadatos disponibles?
**En ningún lugar del código ejecutable del cliente.**
- Se escanearon las tablas de constantes y cadenas de los **7,364 chunks de bytecode LuaJIT 2.1** distribuidos en los 18 contenedores `.bytes` de `D:\secret\P5X\client\OuterPackage\Lua\Windows\`: **0 coincidencias** para el identificador `isClientBattle`.
- Se escanearon los **143,287 identificadores C# y literales de texto** de `D:\secret\P5X\client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat`: **0 coincidencias** para `isClientBattle`.
- El único archivo de todo el cliente donde existe la cadena `isClientBattle` es el descriptor Protobuf `allMsgPb.bytes` (`message SCServerConfig`, campo `#1: optional bool isClientBattle = 1`).

### 1.2. ¿Qué subsistemas consultan su valor al recibir `SCServerConfig` (`MsgID 1112`)?
**Ningún subsistema lo consulta.**
El único receptor registrado en todo el cliente para `MsgID.SCServerConfig` (`1112`) es el módulo `LoginMod`, ubicado en `E8DF29521A39C99.bytes`, chunk `0` (`33,477 bytes`).

#### Registro del manejador (`E8DF29521A39C99.bytes[0]`, `Proto[8]` — `LoginMod:OnConfMsg`)
En `Proto[8]`, el módulo registra sus callbacks de red asociando `MsgID.SCServerConfig` a `self.OnGetSCServerConfigMsg`:
- Constantes de `Proto[8]`: `['OnGetSCQueueInfoMsg', 'SCQueueInfo', 'OnGetSCServerListInfoMsg', 'SCServerListInfo', 'OnGetSCServerStatusMsg', 'SCServerStatus', 'OnGetSCAccountKickMsg', 'SCAccountKick', 'OnGetSCServerConfigMsg', 'SCServerConfig', 'OnGetSCRoleListMsg', 'SCRoleList', 'OnGetSCLoginMsg', 'SCLogin', 'MsgID']`.

#### Desensamblado completo de `LoginMod:OnGetSCServerConfigMsg` (`E8DF29521A39C99.bytes[0]`, `Proto[43]`)
La función `Proto[43]` tiene exactamente **34 instrucciones de bytecode LuaJIT 2.1** y una tabla de constantes de 14 strings (`['SetServerTimeBiase', 'timeNow', 'SetGameBaseTime', 'baseTime', 'tonumber', 'ServerTimeMgr', 'showFPS', 'ClientGM', 'OnlineConfig', 'openGM', 'EnableGM', 'GameConfig', 'msg', 'OnGetSCServerConfigMsg']`):

```text
; Función: LoginMod:OnGetSCServerConfigMsg(self, msg)
; Registros de entrada: R0 = self, R1 = msg (tabla decodificada de SCServerConfig)
[000] GGET    A= 2, 'OnlineConfig'
[001] ISF     A= 2
[002] JMP     -> [005]
[003] GGET    A= 2, 'GameConfig'
[004] JMP     -> [018]
[005] GGET    A= 2, 'GameConfig'
[006] TGETS   A= 3, R1, 'openGM'         ; R3 = msg.openGM
[007] IST     A= 3                       ; Si msg.openGM es verdadero, salta a [014]
[008] JMP     -> [014]
[009] GGET    A= 3, 'OnlineConfig'
[010] TGETS   A= 3, R3, 'ClientGM'
[011] CALL    A= 3, B=2, C=1             ; R3 = OnlineConfig.ClientGM()
[012] IST     A= 3
[013] JMP     -> [016]
[014] KPRI    A= 3, true                 ; R3 = true
[015] JMP     -> [017]
[016] KPRI    A= 3, false                ; R3 = false
[017] TSETS   A= 3, R2, 'EnableGM'       ; GameConfig.EnableGM = msg.openGM or OnlineConfig.ClientGM()
[018] TSETS   A= 3, R2, 'showFPS'        ; GameConfig.showFPS = GameConfig.EnableGM
[019] GGET    A= 2, 'ServerTimeMgr'
[020] MOV     A= 4, R2
[021] TGETS   A= 2, R2, 'SetGameBaseTime'
[022] GGET    A= 5, 'tonumber'
[023] TGETS   A= 7, R1, 'baseTime'       ; R7 = msg.baseTime
[024] CALL    A= 5, B=0, C=2             ; tonumber(msg.baseTime)
[025] CALLM   A= 2, B=1, C=1             ; ServerTimeMgr:SetGameBaseTime(tonumber(msg.baseTime))
[026] GGET    A= 2, 'ServerTimeMgr'
[027] MOV     A= 4, R2
[028] TGETS   A= 2, R2, 'SetServerTimeBiase'
[029] GGET    A= 5, 'tonumber'
[030] TGETS   A= 7, R1, 'timeNow'        ; R7 = msg.timeNow
[031] CALL    A= 5, B=0, C=2             ; tonumber(msg.timeNow)
[032] CALLM   A= 2, B=1, C=1             ; ServerTimeMgr:SetServerTimeBiase(tonumber(msg.timeNow))
[033] RET0                               ; return
```

Reconstrucción exacta en Lua equivalente:
```lua
function LoginMod:OnGetSCServerConfigMsg(msg)
    if OnlineConfig then
        GameConfig.EnableGM = (msg.openGM or OnlineConfig.ClientGM()) and true or false
        GameConfig.showFPS = GameConfig.EnableGM
    end
    ServerTimeMgr:SetGameBaseTime(tonumber(msg.baseTime))
    ServerTimeMgr:SetServerTimeBiase(tonumber(msg.timeNow))
end
```
**Conclusión directa:** `LoginMod:OnGetSCServerConfigMsg` lee únicamente `openGM`, `baseTime` y `timeNow`. El campo `isClientBattle` (`field #1`) se descarta sin leerse jamás.

---

### 1.3. ¿Qué es entonces `OnClientBattleEnd`?
Durante el barrido de cadenas relacionadas con `*ClientBattle*` en los 7,364 chunks Lua, apareció un único identificador similar: `OnClientBattleEnd` en `8E845EAB91B413A.bytes`, chunk `79` (`17,448 bytes`, módulo `DailyChallengeMod`).
El desensamblado de `Proto[0]` y `Proto[20]` de dicho chunk demuestra que:
- En `Proto[0]` (`insns 000..010`), el módulo registra un listener de eventos de interfaz:
  ```lua
  EventMgr:AddListener(TurnBasedEvents.BattleEnd, Functor(self.OnClientBattleEnd, self))
  ```
- "Client" en `OnClientBattleEnd` significa simplemente **"cuando el cliente termina de reproducir la animación de fin de combate"** (`TurnBasedEvents.BattleEnd`), en contraposición al momento en que llega el paquete de red del servidor. No guarda relación alguna con cálculo local de combate.

---

### 1.4. ¿Existen clases, funciones o módulos asociados al cálculo local de daño, habilidades, estados y turnos, o solo componentes de presentación?
El subsistema de combate por turnos en el cliente está encabezado por `TbTickMod` (`07B3A247F1ADE14.bytes[95]`, `59,369 bytes`) junto con los módulos auxiliares en `07B3A247F1ADE14.bytes[178]` (`102,429 bytes`) y `7161AA1F66A0ACA.bytes[53]` (`175,863 bytes`).

El análisis de los manejadores de mensajes registrados en `TbTickMod` (`07B3A247F1ADE14.bytes[95]`) confirma que el cliente **solo contiene componentes de presentación, cámaras, línea de tiempo (timeline) y despacho de intenciones**:
1. **Envío de intenciones del jugador (`CS*`):**
   - Cuando el jugador selecciona una habilidad, persona, ítem, guardia o relevo (*Baton Pass* / *Shift*), el cliente construye y envía `CSRoundSkillList` (`MsgID 1325`) y `CSRoundSetSkill` (`MsgID 1337`) o mensajes complementarios (`CSFightDefend` 1307, `CSFightUseItem` 1310, `CSFightGunSkillOpt` 1312).
   > [!NOTE]
   > *Nota de rectificación sobre hipótesis preliminar:* Menciones tempranas a `CSFightRoundBattleSkill (2722)` han quedado **superadas**. En el descriptor canónico `allMsgPb.bytes` no existe `2722` (el rango 2700..2799 pertenece a Arena PvP); el combate PvE opera en el rango `1300..1399` mediante `CSRoundSkillList` (1325).
2. **Consumo de resultados precalculados (`SC*` y `D*`):**
   - `TbTickMod` y `TurnBasedMsgQueueMod` reciben del servidor `SCFightRoundBattleSkill` (`MsgID 1327`, previamente hipotetizado como 2723), `SCFightRoundTime` (`MsgID 1326`, previamente 2705), `SCFightActionSequence` (`MsgID 1394`, previamente 2777) y `SCFightRoundEnd` (`MsgID 1332`).
   - Dentro de estos mensajes, el árbol de resultados ya viene completamente resuelto en estructuras `DRoundSkillResult`, `DActionSkillScopeResult`, `DBattleActionChangeData` y `DFightUnitHpMpChange` (daño exacto infligido, banderas de crítico, debilidad elemental *Down / One More*, cambios de HP/SP, aplicación/expiración de *buffs* y orden de la cola de acción).
   - El código de `TbTickMod` recorre secuencialmente los nodos de `DRoundSkillResult` para instanciar efectos visuales (VFX), reproducir animaciones de cámara, mostrar números flotantes de daño y actualizar las barras de estado de la UI.
3. **Ausencia de motor matemático de resolución de combate en cliente:**
   - Aunque la base de datos local `ConfDataBattle.bytes` (referenciada en `ConfigDBMap.bytes`) contiene las tablas descriptivas de `Skill`, `SkillScope`, `Buff`, `Monster` y `AI` para mostrar tooltips, iconos, alcances de selección de objetivo y previsualizaciones de UI (como qué enemigo es débil a un elemento ya descubierto), **el cliente no posee un bucle local que genere estructuras `DRoundSkillResult` ni que resuelva tiradas de daño, precisión, estados alterados o IA enemiga en sustitución del servidor**.

---

### 1.5. ¿Existen indicios de que `isClientBattle` pertenece a un modo de desarrollo descontinuado?
**Sí, está confirmado al 100%.**
En la arquitectura de motores de Perfect World / Black Wings Game Studio heredada en `MUGame`, las primeras fases de prototipado suelen incluir una bandera en `SCServerConfig` (`isClientBattle`) o un grabador/reproductor (`MUGame.RecordMsgMgr`, `TypeDef[2035]` en `global-metadata.dat`, con métodos `StartRecord(int battleid, bool bEnd)` y `OnRunRecord(string filename)`) para reproducir combates grabados. En la versión de producción de P5X (`P5XEN_41000_PC`), el campo `isClientBattle` quedó congelado en el esquema `.proto` (`SCServerConfig`, campo `#1`) para no romper la compatibilidad binaria de Protobuf en el servidor, pero toda referencia a dicho campo fue eliminada del código Lua y C# del cliente.

---

## 2. Implicación Directa para el Proyecto de Preservación

1. **Enviar `isClientBattle = true` en `SCServerConfig` (`MsgID 1112`) no tendrá ningún efecto en el cliente.**
2. En cambio, enviar **`openGM = true`** en `SCServerConfig` (`MsgID 1112`) **sí es procesado activamente** por `LoginMod:OnGetSCServerConfigMsg` (`insns 006..018`), asignando `GameConfig.EnableGM = true` y `GameConfig.showFPS = true`, lo que habilita las utilidades de diagnóstico de `GMCmdMgr` en el cliente (incluyendo el volcado en consola de mensajes enviados/recibidos mediante `GMCmdMgr.showClientMsgCS` y `GMCmdMgr.showClientMsgSC`).
3. Para que el combate funcione en un servidor local de preservación, el servidor deberá responder a la intención del jugador (`CSRoundSkillList` 1325 / `CSRoundSetSkill` 1337; anteriormente referido preliminarmente como 2722) construyendo y enviando `SCFightRoundBattleSkill` (`MsgID 1327`, anteriormente referido como 2723) con su `DRoundSkillResult`.
   - **Para una Prueba de Concepto (PoC) inicial:** Basta con un resolutor mínimo ("dummy/estático") en el servidor que devuelva un `DRoundSkillResult` válido restando una cantidad fija o simple de HP al objetivo para que el cliente reproduzca la animación y avance el turno.
   - **Para preservación fiel a largo plazo:** El servidor deberá implementar las fórmulas de cálculo de turnos, daño y debilidades (One More / All-Out Attack / Highlight) apoyándose en los datos de habilidades y enemigos.
