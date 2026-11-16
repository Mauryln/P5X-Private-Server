# Resultados del Experimento 1 — Fase 1.1 (`EXPERIMENT_1_RESULTS.md`)

## 1. Registro de Ejecución e Integridad

| Parámetro | Valor Verificado |
|---|---|
| **Fecha de ejecución** | `2026-11-14` |
| **Archivo origen analizado (solo lectura)** | `D:\secret\P5X\client\OuterPackage\Lua\Windows\allMsgPb.bytes` |
| **Tamaño del archivo origen** | `223.978 bytes` |
| **Hash SHA-256 antes del experimento** | `2D4AEE2C04A861414317F7403D933793D4CB932F393F53D2229B8DA6119F3700` |
| **Hash SHA-256 después del experimento** | `2D4AEE2C04A861414317F7403D933793D4CB932F393F53D2229B8DA6119F3700` *(Inalterado)* |
| **Entorno de ejecución** | Python `3.15.2` (64-bit) sin instalar paquetes externos (decodificador puro del formato de cable oficial `google.protobuf.FileDescriptorSet`). |
| **Errores durante la decodificación** | **0 errores.** El 100% de los `223.978 bytes` fue parseado y re-serializado desde el árbol sintáctico (AST) produciendo exactamente el mismo hash SHA-256. |

---

## 2. Archivos Generados en `D:\secret\docs\`

| Archivo Generado | Tamaño | Hash SHA-256 | Descripción |
|---|---|---|---|
| [options.proto](file:///D:/secret/docs/options.proto) | `124 bytes` | *(Ver tabla de verificación)* | Definición de la extensión `google.protobuf.MessageOptions` (`optional int32 msgid = 54321;`). |
| [msg.proto](file:///D:/secret/docs/msg.proto) | `393.604 bytes` | *(Ver tabla de verificación)* | Esquema Proto2 completo reconstruido con las **37 enumeraciones** y los **2.663 mensajes** del juego. |
| [PROTOBUF_ANALYSIS.md](file:///D:/secret/docs/PROTOBUF_ANALYSIS.md) | Documental | — | Análisis técnico del `FileDescriptorSet`, opciones de compilación, prueba de equivalencia y limitaciones. |
| [MESSAGE_CATALOG.md](file:///D:/secret/docs/MESSAGE_CATALOG.md) | `196.052 bytes` | — | Catálogo completo de dominios, las 37 enumeraciones, desglose campo por campo de los mensajes prioritarios e índice de los 2.195 mensajes de red. |
| [NETWORK_DEPENDENCIES.md](file:///D:/secret/docs/NETWORK_DEPENDENCIES.md) | Documental | — | Diagramas de secuencia y especificación de los mensajes exactos para Login, Personaje, Escena y Combate. |
| [EXPERIMENT_1_RESULTS.md](file:///D:/secret/docs/EXPERIMENT_1_RESULTS.md) | Documental | — | Este informe de evidencias, conclusiones y propuesta del Experimento 2. |

---

## 3. Conclusiones Principales Basadas en Evidencia

1. **Esquema de red 100% recuperado sin tocar ejecutables:** `allMsgPb.bytes` contiene la totalidad del contrato de comunicación cliente-servidor (`msg.proto`, 2.663 mensajes y 37 enumeraciones).
2. **Problema del mapeo de `MsgID` resuelto por completo:** Cada uno de los **2.195 mensajes de red** (`1.070 CS*` y `1.125 SC*`) lleva incrustado su identificador numérico de protocolo (`msgid`) en la opción de mensaje `54321` (por ejemplo: `CSLogin = 101`, `SCLoginResult = 102`, `CSLoginGate = 103`, `SCLoginGateResult = 104`, `CSQueryCharacters = 1001`, `CSCharacterLogin = 1007`, `SCInitData = 1102`, `SCServerConfig = 1112`, `CSSceneEnter = 1201`, `SCSceneEnterResult = 1202`, `CSRoundSkillList = 1325`, `SCFightRoundBattleSkill = 1327`, `SCFightSpecialActionResult = 1399`).
3. **Descubrimiento del flag `isClientBattle` en `SCServerConfig` (`MsgID 1112`):** El paquete de configuración del servidor incluye `required bool isClientBattle = 1` y `required bool openGM = 2`. Si el cliente conserva la lógica de `isClientBattle`, podría delegarse la resolución de combates al propio cliente local.
4. **Criterio de éxito E1.1 superado al 100%:** Se han identificado todos los mensajes y campos obligatorios (`required`) y opcionales para iniciar sesión, cargar personaje, entrar en escena y ejecutar turnos de combate.

---

## 4. Recomendación del Siguiente Experimento (Experimento 2 — Fase 1.2)

Con el esquema Protobuf (`msg.proto`) y todos los `MsgID` (`54321`) ya documentados, **solo quedan dos incógnitas técnicas antes de poder interpretar una captura de red real**:
1. **Cómo están empaquetados los archivos `.bytes` de Lua (`OuterPackage\Lua\Windows\*.bytes`) y configuración (`ConfData*.bytes`):** Verificar en modo de solo lectura si pueden leerse para comprobar cómo usa el cliente `SCServerConfig.isClientBattle` y cómo construye los paquetes en Lua.
2. **Cuál es el formato de cabecera TCP (Framing) en `NetMod` (`GameAssembly.dll` / `global-metadata.dat`):** Determinar cuántos bytes preceden al payload Protobuf en los puertos `10403` y `10404` (ej. longitud + `msgid` + número de secuencia/flags) y si existe cifrado en la capa de socket.

### Propuesta de Experimento 2 (Mínimo, Reversible y 100% Solo Lectura)
- **Objetivo:** Inspeccionar en modo de solo lectura las cabeceras y estructura de `D:\secret\P5X\client\OuterPackage\Lua\Windows\Lua_ifiles.bytes` (y un archivo `.bytes` de Lua/Config) junto con los nombres de clases y métodos de red registrados en `D:\secret\P5X\client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat`.
- **Condiciones:** Sin modificar ningún archivo de `D:\secret\P5X`, sin ejecutar el juego y guardando la documentación resultante únicamente en `D:\secret\docs\`.
