# Mapa de Protocolo de Comunicación Cliente-Servidor (PROTOCOL_MAP.md)

**Proyecto:** Preservación Comunitaria y Reconstrucción Fiel de Servidor — *Persona 5: The Phantom X (P5X)*  
**Fuente Primaria:** `allMsgPb.bytes` (2.663 definiciones, 2.195 MsgIDs) y capturas de red en vivo (183 tramas reales).

---

## 1. Estructura de Transporte (Zeus Wire Protocol)

```text
+-------------------+-----------------+-----------------+------------------------+
| Length (4B BE)    | MsgID (2B BE)   | Seq (2B BE)     | Protobuf Payload (N B) |
+-------------------+-----------------+-----------------+------------------------+
```
- Cifrado de transporte: RC4 activado tras Trama 0 (`[len][key]`).

---

## 2. Mapa de Mensajes por Dominio

### 2.1 Autenticación, Login y Configuración Inicial

| MsgID | Nombre de Mensaje | Dirección | Descripción y Campos Clave | Estado / Validación |
| :---: | :--- | :---: | :--- | :---: |
| **101** | `CSLogin` | C $\to$ S | Solicitud inicial con token y cuenta. | `CONFIRMADO EN VIVO` |
| **102** | `SCLoginResult` | S $\to$ C | Retorna `gameAddress`, `sessionId`. `zoneTime` debe ser `None`. | `CONFIRMADO EN VIVO` |
| **103** | `CSLoginGate` | C $\to$ S | Saludo a la pasarela de lógica con `sessionId`. | `CONFIRMADO EN VIVO` |
| **104** | `SCLoginGateResult` | S $\to$ C | Aceptación de compuerta (`errorCode = 0`). | `CONFIRMADO EN VIVO` |
| **1112**| `SCServerConfig` | S $\to$ C | Sincronización base: `openGM`, `baseTime`, `timeNow`. | `CONFIRMADO EN VIVO` |
| **1136**| `SCServerTime` | S $\to$ C | Timestamp epoch en milisegundos (`int64 serverTime`). | `CONFIRMADO EN VIVO` |
| **1001**| `CSQueryCharacters` | C $\to$ S | Petición de lista de avatares creados. | `CONFIRMADO EN VIVO` |
| **1002**| `SCQueryCharactersResult`| S $\to$ C | Lista de personajes (`DCharacter`). | `CONFIRMADO EN VIVO` |
| **1007**| `CSCharacterLogin` | C $\to$ S | Selección de personaje para entrar al juego. | `CONFIRMADO EN VIVO` |
| **1008**| `SCCharacterLoginResult`| S $\to$ C | Confirmación de entrada con `roleId`. | `CONFIRMADO EN VIVO` |
| **1102**| `SCInitData` | S $\to$ C | Estructura masiva con datos del jugador (`DHuman`, `DOpenWorld`).| `CONFIRMADO EN VIVO` |

### 2.2 Escena, Posicionamiento y Mundo

| MsgID | Nombre de Mensaje | Dirección | Descripción y Campos Clave | Estado / Validación |
| :---: | :--- | :---: | :--- | :---: |
| **1201**| `CSSceneEnter` | C $\to$ S | Petición de carga de escena por `sceneId`. | `CONFIRMADO EN VIVO` |
| **1202**| `SCSceneEnterResult` | S $\to$ C | Carga mapa: `sceneSn`, `pos` (`DVector3`), `dir` (`DVector2`). | `CONFIRMADO EN VIVO` |
| **1203**| `SCSceneEnterEnd` | S $\to$ C | Señal de finalización de carga de mapa. | `CONFIRMADO EN VIVO` |
| **1204**| `CSSceneSwitch` | C $\to$ S | Cambio dinámico de escenario / teletransporte. | `CONFIRMADO EN VIVO` |
| **1205**| `SCSceneSwitch` | S $\to$ C | Parámetros del nuevo escenario de destino. | `CONFIRMADO EN VIVO` |
| **1208**| `CSSceneMove` | C $\to$ S | Streaming continuo de movimiento del avatar. | `CONFIRMADO EN VIVO` |
| **1209**| `CSSceneMoveStop` | C $\to$ S | Posición y rotación final al detenerse. | `CONFIRMADO EN VIVO` |
| **1253**| `SCAreaPosSync` | S $\to$ C | Sincronización de entidades en el área. | `CONFIRMADO EN VIVO` |
| **1254**| `CSAreaPosSync` | C $\to$ S | Confirmación de sincronización de área. | `CONFIRMADO EN VIVO` |

### 2.3 Diálogos, Misiones y Cinemáticas

| MsgID | Nombre de Mensaje | Dirección | Descripción y Campos Clave | Estado / Validación |
| :---: | :--- | :---: | :--- | :---: |
| **1419**| `CSGetCrucialDialog` | C $\to$ S | Consulta de diálogos críticos activos. | `CONFIRMADO EN VIVO` |
| **1420**| `SCGetCrucialDialogResult`| S $\to$ C | `required string crucialDialogs = 1`. | `CONFIRMADO EN VIVO` |
| **1418**| `CSDialogFinish` | C $\to$ S | Notificación de cierre de diálogo. | `CONFIRMADO` |
| **1437**| `CSDialogChoice` | C $\to$ S | Selección de opción de diálogo (`choice`). | `CONFIRMADO` |
| **2007**| `SCQuestInfo` | S $\to$ C | Lista de misiones activas (`DQuest`). | `CONFIRMADO` |
| **2001**| `CSQuestAccept` | C $\to$ S | Aceptación de misión (`questSn`). | `CONFIRMADO` |
| **2003**| `CSQuestSubmit` | C $\to$ S | Entrega de misión completada. | `CONFIRMADO` |
| **4011**| `SCPlayScenario` | S $\to$ C | Disparo de cinemática/escenario. | `CONFIRMADO` |
| **4002**| `CSScenarioFinish` | C $\to$ S | Fin de reproducción de cinemática. | `CONFIRMADO` |

### 2.4 Combate PvE (Módulo `TbTickMod`)

| MsgID | Nombre de Mensaje | Dirección | Descripción y Campos Clave | Estado / Validación |
| :---: | :--- | :---: | :--- | :---: |
| **1302**| `CSEnterFight` | C $\to$ S | Inicio de combate. | `STUB CODEC` |
| **1326**| `SCFightRoundTime` | S $\to$ C | Sincronización de temporizador de turno. | `STUB CODEC` |
| **1325**| `CSRoundSkillList` | C $\to$ S | Habilidad seleccionada por el jugador en su turno. | `STUB CODEC` |
| **1327**| `SCFightRoundBattleSkill` | S $\to$ C | Resolución del turno: daño, efectos, animaciones. | `STUB CODEC` |
| **1330**| `SCRoundSkillList` | S $\to$ C | Confirmación de recepción de acción de turno. | `STUB CODEC` |
| **1331**| `CSFightHumanPlayEnd`| C $\to$ S | Cliente terminó de reproducir animaciones de turno. | `STUB CODEC` |
| **1332**| `SCFightRoundEnd` | S $\to$ C | Cierre formal del turno de combate. | `STUB CODEC` |
| **1333**| `SCFightBattleEnd` | S $\to$ C | Fin del combate y resumen de recompensas. | `STUB CODEC` |
| **1394**| `SCFightActionSequence` | S $\to$ C | Ordenamiento dinámico de la barra de acciones. | `STUB CODEC` |

### 2.5 Keepalive y Red

| MsgID | Nombre de Mensaje | Dirección | Descripción | Estado / Validación |
| :---: | :--- | :---: | :--- | :---: |
| **1116**| `CSPing` | C $\to$ S | Heartbeat periódico del cliente. | `CONFIRMADO EN VIVO` |
| **1117**| `SCPing` | S $\to$ C | Respuesta inmediata de latencia. | `CONFIRMADO EN VIVO` |
| **1118**| `CSNetDelayDetect` | C $\to$ S | Medición de calidad de conexión. | `CONFIRMADO EN VIVO` |
| **1119**| `SCNetDelayDetect` | S $\to$ C | Retorno de detección de retardo. | `CONFIRMADO EN VIVO` |
