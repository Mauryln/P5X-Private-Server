# Especificación de Contenedores Lua, Archivos de Configuración y Metadatos (Prioridad 3)

**Objetivo:** Documentar en modo de solo lectura las cabeceras, entropía y estructura binaria de `Lua_ifiles.bytes`, los 18 contenedores de bytecode Lua (`.bytes`), el índice `ConfigDBMap.bytes`, las bases de datos `ConfData*.bytes` y el archivo `global-metadata.dat`.

---

## 1. Índice de Scripts Lua: `Lua_ifiles.bytes`

- **Ruta:** `D:\secret\P5X\client\OuterPackage\Lua\Windows\Lua_ifiles.bytes`
- **Tamaño:** `377,180 bytes`
- **SHA-256:** `8107460A6C29A6E2E227A44D4F3A8D01EA60C673DC957495E1BBFBFCD5BCB3AA`
- **Entropía de Shannon (primeros 64 KB):** `5.2190 bits/byte` (En claro, no cifrado)
- **Primeros 32 bytes (Hex):**
  ```text
  00000000: C4 1C 00 00 00 00 00 00 DD B4 C6 05 B6 69 A2 C5  .............i..
  00000010: 10 38 35 35 45 45 45 30 33 44 37 46 39 43 32 45  .855EEE03D7F9C2E
  ```

### Estructura Binaria Verificada
El archivo es leído al inicio por `LuaInterface.LuaFileUtils.onLoadCombinedFiles()` (`TypeDef[1366]` en `global-metadata.dat`):
1. **Cabecera (8 bytes):**
   - `uint64_le entry_count = 0x0000000000001CC4` (**`7,364` entradas**, que coinciden exactamente con la suma de los chunks contenidos en los 18 paquetes `.bytes`).
2. **Registros (`7,364` registros de longitud variable):**
   Cada registro asocia el hash de 64 bits del nombre del módulo Lua (calculado por `LuaFileUtils.getHashLong(string fileName)`) con el contenedor `.bytes` combinado donde se almacena (`fileMergeInfo` en `LuaFileUtils.readLuaInCombine`):
   - `int64_le script_hash`: Hash de 8 bytes del nombre del archivo Lua (p. ej. `0xC5A269B605C6B4DD`).
   - `uint8 name_len`: Longitud de la cadena del archivo contenedor (`0x10 = 16` o `0x11 = 17` caracteres).
   - `char[name_len] archive_name`: Nombre hexadecimal del paquete contenedor sin extensión (p. ej. `"855EEE03D7F9C2E3"` o `"07B3A247F1ADE14"`).
   - Metadatos de posición/índice dentro del contenedor combinado (`26 bytes` adicionales por entrada con el índice y desplazamiento del chunk).

---

## 2. Contenedores de Bytecode Lua (`.bytes`)

En `D:\secret\P5X\client\OuterPackage\Lua\Windows\` existen **18 contenedores combinados** cuyos nombres son cadenas hexadecimales.

### 2.1. Estructura del Contenedor Combinado (100% en Claro)
Todos los 18 archivos siguen exactamente el mismo formato binario sin cifrado ni compresión:

```text
+-----------------------------------------------------------------------+
| Offset 0x00 (4 bytes): uint32_le chunk_count                          |
+-----------------------------------------------------------------------+
| Chunk #0:                                                             |
|   uint32_le chunk_0_size (N_0 bytes)                                  |
|   byte[N_0] luajit_bytecode_0 (comienza siempre con 1B 4C 4A 02 0A)   |
+-----------------------------------------------------------------------+
| Chunk #1:                                                             |
|   uint32_le chunk_1_size (N_1 bytes)                                  |
|   byte[N_1] luajit_bytecode_1 (comienza siempre con 1B 4C 4A 02 0A)   |
+-----------------------------------------------------------------------+
| ... hasta Chunk #(chunk_count - 1)                                    |
+-----------------------------------------------------------------------+
```

- **Ejemplo verificado (`07B3A247F1ADE14.bytes`):**
  - `0x00..0x03`: `56 01 00 00` -> `chunk_count = 342` (`0x0156`).
  - `0x04..0x07`: `8C 08 00 00` -> `chunk_0_size = 2,188` bytes (`0x088C`).
  - `0x08..0x0C`: `1B 4C 4A 02 0A` -> Magia estándar de **LuaJIT 2.1** (`\x1bLJ\x02`) seguida del byte de banderas `0x0A` (`BCDUMP_F_STRIP = 0x02 | BCDUMP_F_FR2 = 0x08`, es decir, bytecode de 64 bits `LJ_FR2` sin números de línea de depuración).

### 2.2. Inventario Completo de los 18 Paquetes Lua

| Paquete `.bytes` | Tamaño (bytes) | Chunks (`uint32_le`) | Chunks con magia `1B 4C 4A 02` | Módulos relevantes identificados en su interior |
| :--- | ---: | ---: | ---: | :--- |
| `07B3A247F1ADE14.bytes` | 1,563,494 | 342 | 342 (100%) | `MsgMgr` (`[64]`), `ConnectMod` (`[66]`), `NetState` (`[67]`), `NetWorkMod` (`[69]`), `TbTickMod` (`[95]`) |
| `1410A9F67109B47.bytes` | 9,858,690 | 513 | 513 (100%) | Inicializador `pbnew` / `LuaMsgUtils.LoadMsgPbFile` (`[452]`) |
| `2531C59CC6AD3C4.bytes` | 804,998 | 164 | 164 (100%) | Módulos de UI y lógica secundaria |
| `35648836B5003999.bytes` | 3,795,213 | 599 | 599 (100%) | Subsistemas de escena y eventos |
| `3CA0CE7292A92C6D.bytes` | 2,869,620 | 538 | 538 (100%) | Subsistemas de interfaz y menús |
| `51313D5089B1076D.bytes` | 5,693,853 | 328 | 328 (100%) | Tablas de protocolos heredados (`MsgTable`) |
| `606FD29D0712AD26.bytes` | 2,135,930 | 384 | 384 (100%) | Subsistemas de progresión y social |
| `61C7F54D3E0ACBA5.bytes` | 2,891,201 | 511 | 511 (100%) | Subsistemas de exploración y palacios |
| `632D7DE339D731E6.bytes` | 2,996,877 | 501 | 501 (100%) | Subsistemas de misiones y diálogos |
| `7161AA1F66A0ACA.bytes` | 4,768,546 | 620 | 620 (100%) | Presentación y secuencias de combate (`[53]`) |
| `855EEE03D7F9C2E3.bytes` | 2,608,425 | 491 | 491 (100%) | Subsistemas de inventario y equipamiento |
| `8E845EAB91B413A.bytes` | 2,812,186 | 428 | 428 (100%) | `DailyChallengeMod` (`[79]`) y modos de desafío |
| `B1A0653B2769B0BA.bytes` | 2,213,572 | 200 | 200 (100%) | Definiciones de mensajes y constantes |
| `C93802EA3694391A.bytes` | 2,299,515 | 423 | 423 (100%) | Subsistemas de gacha/contratos y tienda |
| `CE550A62BA41DEEE.bytes` | 2,289,144 | 350 | 350 (100%) | Subsistemas de sinergias (Confidants) y vida diaria |
| `E0FE49AEBE4F265D4.bytes` | 2,402,217 | 424 | 424 (100%) | Script de prueba HTTP (`[17]`) y utilidades |
| `E8DF29521A39C99.bytes` | 1,923,413 | 349 | 349 (100%) | `LoginMod` (`[0]`, manejador de `SCServerConfig` y login) |
| `F6D6BD0720ADAC3.bytes` | 1,039,500 | 199 | 199 (100%) | Módulos de configuración y localización |
| **TOTAL (18 archivos)** | **54,966,394** | **7,364** | **7,364 (100%)** | **Totalidad de la lógica Lua del cliente** |

---

## 3. Archivos de Configuración: `ConfigDBMap.bytes` y `ConfData*.bytes`

### 3.1. `ConfigDBMap.bytes` (XML UTF-8 en Claro)
- **Ruta:** `D:\secret\P5X\client\OuterPackage\ConfData\Windows\ConfigDBMap.bytes`
- **Tamaño:** `62,554 bytes` (`1,391` líneas)
- **SHA-256:** `92018D79B5B5722808812EF04E922B0D08446E88E006D6E9D8200945A7442246`
- **Entropía:** `4.9479 bits/byte`
- **Estructura:** Documento XML deserializado por `ConfigDBMap` (`TypeDef[3]`) y `ConfigDBMapRecord` (`TypeDef[5]`):
  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <ConfigDBMapRecord BasicDBName="ConfDataDefault">
    <Map ExcelName="AI" DBName="ConfDataBattle" />
    <Map ExcelName="AICondition" DBName="ConfDataBattle" />
    <Map ExcelName="AbnormalState" DBName="ConfDataBattle" />
    <Map ExcelName="AccountLevel" DBName="ConfDataBasic" />
    <Map ExcelName="Achievement" DBName="ConfDataBasic" />
    ...
  ```
- Permite conocer el nombre exacto de las **~1,385 tablas de datos** del juego (`ExcelName`) y en cuál de los 10 archivos `ConfData*.bytes` se ubica cada una (`ConfDataBasic`, `ConfDataBattle`, `ConfDataCityLife`, `ConfDataDefault`, `ConfDataDungeon`, `ConfDataEvent`, `ConfDataItem`, `ConfDataPlot`, `ConfDataRole`, `ConfDataSystem`).

### 3.2. `ConfData*.bytes` (Bases de Datos SQLite Cifradas con SQLCipher)
- **Muestras analizadas:**
  - `ConfDataBasic.bytes`: `118,784 bytes` (`29 × 4,096 bytes`), `SHA-256: 0A31B1ABC0D68D653280D7AECBC0B7634D87E0F9E6992181795B064997ACC935`, Entropía: `7.9973 bits/byte`.
  - `ConfDataBattle.bytes`: `8,949,760 bytes` (`2,185 × 4,096 bytes`), `SHA-256: D66B5F808422E06C87B4B702CBE347D275D5FD4C999FF0EF0C060A92D5BAD504`, Entropía: `7.9976 bits/byte`.
- **Diagnóstico técnico:**
  - El tamaño de todos los archivos `ConfData*.bytes` es múltiplo exacto del tamaño de página de SQLite/SQLCipher (`4,096 bytes`), y su entropía roza el máximo teórico (`8.0000 bits/byte`).
  - El cliente carga las bibliotecas nativas `sqlcipher.dll` y `SqlCipher4Unity3D.dll` (y expone `luaopen_lsqlcipher` en `global-metadata.dat`).
  - Siguiendo las condiciones de ejecución (no eludir protecciones ni cifrado), estos archivos se documentan como bases de datos SQLCipher cifradas y no se intenta extraer ni aplicar su clave criptográfica.
  - **Nota de viabilidad:** Dado que los 7,364 scripts Lua están en claro, los nombres de las tablas (`ConfigDBMap.bytes`) y los nombres de las columnas consultadas por los scripts Lua son legibles directamente desde las constantes de los chunks Lua cuando sea necesario conocer la estructura de un ID de configuración.

---

## 4. Metadatos de Unity IL2CPP: `global-metadata.dat`

- **Ruta:** `D:\secret\P5X\client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat`
- **Tamaño:** `17,648,664 bytes` (`16.83 MB`)
- **SHA-256:** `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B`
- **Entropía:** `4.3060 bits/byte` (100% en claro, sin ofuscación ni cifrado de cabecera)
- **Cabecera verificada:**
  - `magic = 0xFAB11BAF` (`AF 1B B1 FA`, estándar de Unity IL2CPP)
  - `version = 31` (`1F 00 00 00`)
- **Tablas principales verificadas:**
  - `stringLiteralData`: offset `0x00043028`, tamaño `1,000,432 bytes`.
  - `strings` (identificadores C#): offset `0x00137418`, tamaño `2,568,400 bytes` (`143,287` cadenas terminadas en nulo).
  - `methods` (`Il2CppMethodDefinition`, 36 bytes/entrada): offset `0x0041115C`, tamaño `5,069,628 bytes` (**`140,823` métodos**).
  - `parameters` (`Il2CppParameterDefinition`, 12 bytes/entrada): offset `0x00A03818`, tamaño `1,886,112 bytes` (**`157,176` parámetros**).
  - `fields` (`Il2CppFieldDefinition`, 12 bytes/entrada): offset `0x00BCFFB8`, tamaño `1,001,964 bytes` (**`83,497` campos**).
  - `typeDefinitions` (`Il2CppTypeDefinition`, 88 bytes/entrada): offset `0x00DCC68C`, tamaño `1,611,720 bytes` (**`18,315` clases/structs/enums**).
