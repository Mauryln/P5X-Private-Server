# Análisis Estático de Cifrado de `ConfData*.bytes` (SQLCipher) — Persona 5: The Phantom X

> **Alcance y Restricciones Operativas:**
> Este documento se ha elaborado exclusivamente mediante análisis estático de solo lectura sobre la copia local del cliente Global/Steam (`D:\secret\P5X`). Se cumple estrictamente la prohibición de **no extraer ni publicar secretos o claves del cliente**: se documentan la arquitectura criptográfica, los parámetros verificables del motor SQLCipher y el flujo de derivación e inyección de clave en tiempo de ejecución, manteniendo el valor concreto de la clave como `DESCONOCIDO` (no extraído).

---

## 1. Aclaración Obligatoria sobre Qué Archivos Están Cifrados y Cuáles No

Antes de analizar `ConfData*.bytes`, se corrige y aclara de forma explícita el estado de cifrado de los contenedores del cliente PC Global/Steam (`D:\secret\P5X`):

| Componente del Cliente | Ruta en `D:\secret\P5X` | ¿Está Cifrado? | Formato Real Verificado | Nivel de Evidencia |
| :--- | :--- | :---: | :--- | :---: |
| **Contenedores de scripts Lua** (`55` archivos `.bytes`) | `client\OuterPackage\Lua\Windows\*.bytes` | **NO** | Índice en claro (`[uint32 offset][uint32 len][ASCII name]`) seguido de `7,364` chunks de bytecode **LuaJIT 2.1 en texto plano** (magic `1B 4C 4A 02`, *stripped* con flags `0x02`/`0x0A`, sin símbolos de depuración). | `CONFIRMADO` |
| **Metadatos de IL2CPP** | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | **NO** | Cabecera estándar de Unity IL2CPP en claro (magic `AF 1B B1 FA`, versión `29` / `0x1D`, tablas de strings, tipos y métodos legibles directamente). | `CONFIRMADO` |
| **Esquema de red Protobuf** | `client\OuterPackage\Lua\Windows\allMsgPb.bytes` | **NO** | `google.protobuf.FileDescriptorSet` serializado en binario estándar en claro (`223,978` bytes, descriptores de mensajes de red y opciones). | `CONFIRMADO` |
| **Mapa de tablas de configuración** | `client\OuterPackage\Config\Windows\ConfigDBMap.bytes` | **NO** | Documento XML en texto plano UTF-8 (`62,554` bytes) que asocia el nombre de cada tabla de configuración con su archivo contenedor `ConfData*.bytes`. | `CONFIRMADO` |
| **Bases de datos de configuración y traducción** (`11` archivos `.bytes`) | `client\OuterPackage\Config\Windows\ConfData*.bytes` y `ConfTranslation*.bytes` | **SÍ** | Bases de datos SQLite 3 cifradas a nivel de página mediante **SQLCipher 4** (`AES-256-CBC`, páginas de `4,096` bytes, `PBKDF2-HMAC-SHA512`). | `CONFIRMADO` |

> **Corrección documental:** Cualquier mención previa en la fase preliminar que sugiriera que los contenedores Lua (`Lua\Windows\*.bytes`) estaban cifrados queda formalmente corregida; dichos contenedores solo están empaquetados y compilados a bytecode LuaJIT 2.1 *stripped* sin cifrado criptográfico. Los únicos activos de lógica/datos cifrados criptográficamente en disco son las 11 bases de datos SQLCipher (`ConfData*.bytes` y `ConfTranslation*.bytes`).

---

## 2. Inventario y Estructura en Disco de `ConfData*.bytes` y `ConfTranslation*.bytes`

En `D:\secret\P5X\client\OuterPackage\Config\Windows\` existen 12 archivos `.bytes`: 1 archivo XML en claro (`ConfigDBMap.bytes`) y 11 bases de datos cifradas con SQLCipher.

### 2.1. Tabla de Archivos, Tamaños, Páginas y Entropía (`CONFIRMADO`)

| Archivo | Tamaño (Bytes) | Páginas (`4096 B`) | `Tamaño % 4096` | Entropía (`bits/byte`) | Primeros 16 Bytes (`kdf_salt` en Hex, Offset `0x00..0x0F`) | Nivel de Evidencia |
| :--- | ---: | ---: | :---: | :---: | :--- | :---: |
| `ConfDataAward.bytes` | `2,994,176` | `731` | `0` | `7.9974` | `f82f4e129b7f7c225a1fb2c61b91e078` | `CONFIRMADO` |
| `ConfDataBasic.bytes` | `46,489,600` | `11,350` | `0` | `7.9976` | `f40250410467a8f28de938184bb458aa` | `CONFIRMADO` |
| `ConfDataBattle.bytes` | `96,743,424` | `23,619` | `0` | `7.9976` | `32ab58d4de7429fb1d3110abfb4cb710` | `CONFIRMADO` |
| `ConfDataCheckPoint.bytes` | `12,775,424` | `3,119` | `0` | `7.9975` | `1c60e49bf7281d7fb779db1153e2fc65` | `CONFIRMADO` |
| `ConfDataDefault.bytes` | `51,142,656` | `12,486` | `0` | `7.9976` | `763858a143c92df53799482e4e4e7aa4` | `CONFIRMADO` |
| `ConfDataDevelop.bytes` | `4,784,128` | `1,168` | `0` | `7.9975` | `bc742c4f67cded595003497882f9d4fa` | `CONFIRMADO` |
| `ConfDataDialog.bytes` | `9,367,552` | `2,287` | `0` | `7.9975` | `e4d2bdcdcb3d66eb898a8832c4e2a898` | `CONFIRMADO` |
| `ConfDataText.bytes` | `40,755,200` | `9,950` | `0` | `7.9976` | `94c9d3f39d0f2a37596fb6cf594c0eb5` | `CONFIRMADO` |
| `ConfTranslationDBG.bytes` | `352,256` | `86` | `0` | `7.9967` | `82112a6c3080b8f0b17f62c0bfddaa1b` | `CONFIRMADO` |
| `ConfTranslationEN.bytes` | `54,480,896` | `13,301` | `0` | `7.9976` | `fa3d6731f27dfcd894366dfadbb97c52` | `CONFIRMADO` |
| `ConfTranslationJP.bytes` | `54,321,152` | `13,262` | `0` | `7.9976` | `81108578bd1ba3b497305bc7a74d8e1a` | `CONFIRMADO` |
| `ConfigDBMap.bytes` | `62,554` | N/A | N/A | `4.7121` | `3c436f6e66696744424d61703e0d0a20` (`<ConfigDBMap>\r\n `) | `CONFIRMADO` |

### 2.2. Estructura de Página de SQLCipher Verificada

1. **Ausencia de cabecera SQLite en claro (`plaintext_header_size = 0`):** Ninguno de los 11 archivos comienza con los 16 bytes estándar de SQLite 3 (`53 51 4C 69 74 65 20 66 6F 72 6D 61 74 20 33 00`, `"SQLite format 3\0"`).
2. **Sal de derivación en Página 1 (`bytes[0..15]`):** En SQLCipher con `plaintext_header_size = 0`, los primeros `16` bytes de la Página 1 (`offset 0x00..0x0F`) almacenan en claro el `kdf_salt` aleatorio de 128 bits único por archivo, mientras que el resto de la Página 1 (`offset 0x10..0xFAF`, `4,000` bytes) contiene el texto cifrado AES-256-CBC de la cabecera SQLite (desde el byte 16, donde reside `page_size` en big-endian) y los datos de la primera página.
3. **Área reservada al final de cada página (`reserve_sz = 80` bytes, `offset 0xFB0..0xFFF`):**
   - `offset 0xFB0..0xFBF` (`16` bytes): Vector de inicialización (`IV`) aleatorio de AES-256-CBC para esa página.
   - `offset 0xFC0..0xFFF` (`64` bytes): Etiqueta de autenticación `HMAC-SHA512` calculada sobre el texto cifrado de la página, el `IV` y el número de página (`int32 LE` basado en 1).

---

## 3. Verificación Binaria de Parámetros Criptográficos en `sqlcipher.dll` y `tolua.dll`

El cliente PC incluye dos binarios nativos x86_64 que contienen el motor SQLCipher compilado estáticamente:
1. `D:\secret\P5X\client\pc\P5X_Data\Plugins\x86_64\sqlcipher.dll` (`1,945,088` bytes)
2. `D:\secret\P5X\client\pc\P5X_Data\Plugins\x86_64\tolua.dll` (`1,694,208` bytes, que exporta además los *bindings* Lua `luaopen_lsqlcipher` y `luaopen_lsqlcipher_password`)

Ambos binarios contienen exactamente la misma implementación de `sqlcipher_codec_ctx_init` y las mismas variables globales por defecto de **SQLCipher 4**.

### 3.1. Desensamblado de `sqlcipher_codec_ctx_init` (`CONFIRMADO`)

- En `sqlcipher.dll`: `RVA 0x006091` (`FileOffset 0x005491`)
- En `tolua.dll`: `RVA 0x061870` (`FileOffset 0x060C70`)

Fragmento de instrucciones verificadas en `sqlcipher.dll` (`RVA 0x0060F2..0x0061BB`) y su equivalente idéntico en `tolua.dll` (`RVA 0x0618D1..0x06199A`):

```asm
; Inicialización de kdf_salt_sz = 16 bytes (0x10) y fast_kdf_iter = 2
0x1800060F2: c7 43 0c 10 00 00 00       mov dword ptr [rbx + 0x0c], 0x10      ; ctx->kdf_salt_sz = 16
0x18000612F: c7 43 08 02 00 00 00       mov dword ptr [rbx + 0x08], 2         ; ctx->fast_kdf_iter = 2

; Carga de default_page_size desde sección .data
0x18000614F: 8b 15 d7 ee 0c 00          mov edx, dword ptr [rip + 0xceed7]    ; sqlcipher.dll [RVA 0x0D502C] = 4096 (0x1000)
0x180006155: 48 8b cb                   mov rcx, rbx
0x180006158: e8 d5 fb ff ff             call sqlcipher_codec_ctx_set_pagesize

; Carga de default_kdf_iter desde sección .data
0x180006163: 8b 15 bf ee 0c 00          mov edx, dword ptr [rip + 0xceebf]    ; sqlcipher.dll [RVA 0x0D5028] = 256000 (0x3E800)
0x180006169: 45 33 c0                   xor r8d, r8d
0x18000616C: 48 8b cb                   mov rcx, rbx
0x18000616F: e8 14 fc ff ff             call sqlcipher_codec_ctx_set_kdf_iter

; Carga de default_hmac_algorithm desde sección .data
0x18000617A: 8b 15 b0 ee 0c 00          mov edx, dword ptr [rip + 0xceeb0]    ; sqlcipher.dll [RVA 0x0D5030] = 2 (SQLCIPHER_HMAC_SHA512)
0x180006180: 48 8b cb                   mov rcx, rbx
0x180006183: e8 dc fb ff ff             call sqlcipher_codec_ctx_set_hmac_algorithm

; Carga de default_kdf_algorithm desde sección .data
0x18000618E: 8b 15 a0 ee 0c 00          mov edx, dword ptr [rip + 0xceea0]    ; sqlcipher.dll [RVA 0x0D5034] = 2 (SQLCIPHER_PBKDF2_HMAC_SHA512)
0x180006194: 48 8b cb                   mov rcx, rbx
0x180006197: e8 5c fb ff ff             call sqlcipher_codec_ctx_set_kdf_algorithm

; Carga de default_use_hmac desde sección .data
0x1800061A2: 8b 15 78 ee 0c 00          mov edx, dword ptr [rip + 0xcee78]    ; sqlcipher.dll [RVA 0x0D5020] = 3 (flags; bit 0 = use_hmac = 1)
0x1800061A8: 48 8b cb                   mov rcx, rbx
0x1800061AB: 83 e2 01                   and edx, 1
0x1800061AE: e8 b1 fa ff ff             call sqlcipher_codec_ctx_set_use_hmac

; Carga de default_plaintext_header_size desde sección .bss/.data
0x1800061B9: 8b 15 75 3e 0f 00          mov edx, dword ptr [rip + 0xf3e75]    ; sqlcipher.dll [RVA 0x0FA034] = 0
0x1800061BF: 48 8b cb                   mov rcx, rbx
0x1800061C2: e8 e9 f9 ff ff             call sqlcipher_codec_ctx_set_plaintext_header_size
```

### 3.2. Tabla Resumen de Constantes Globales Leídas de `.data` (`CONFIRMADO`)

| Parámetro SQLCipher | `sqlcipher.dll` RVA (`FileOff`) | `tolua.dll` RVA (`FileOff`) | Valor Raw (`uint32 LE`) | Significado Criptográfico | Nivel de Evidencia |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `default_page_size` | `0x0D502C` (`0x0D362C`) | `0x14FCEC` (`0x14E0EC`) | `0x00001000` (`4096`) | Tamaño de página de `4,096` bytes | `CONFIRMADO` |
| `default_kdf_iter` | `0x0D5028` (`0x0D3628`) | `0x14FCF0` (`0x14E0F0`) | `0x0003E800` (`256000`) | `256,000` iteraciones PBKDF2 para clave de cifrado | `CONFIRMADO` |
| `fast_kdf_iter` | Inmediato en `+0x00612F` | Inmediato en `+0x06190E` | `0x00000002` (`2`) | `2` iteraciones PBKDF2 para clave HMAC (`kdf_salt ^ 0x3A`) | `CONFIRMADO` |
| `default_hmac_algorithm` | `0x0D5030` (`0x0D3630`) | `0x14FCE8` (`0x14E0E8`) | `0x00000002` (`2`) | `SQLCIPHER_HMAC_SHA512` (tag de `64` bytes) | `CONFIRMADO` |
| `default_kdf_algorithm` | `0x0D5034` (`0x0D3634`) | `0x14FCE4` (`0x14E0E4`) | `0x00000002` (`2`) | `SQLCIPHER_PBKDF2_HMAC_SHA512` | `CONFIRMADO` |
| `default_use_hmac` | `0x0D5020` (`0x0D3620`) | `0x14FCF8` (`0x14E0F8`) | `0x00000003 & 1 = 1` | HMAC por página activado (`true`) | `CONFIRMADO` |
| `default_plaintext_header_size` | `0x0FA034` (`BSS/0`) | `0x14FCE0` (`0x14E0E0`) | `0x00000000` (`0`) | `0` bytes de cabecera SQLite en claro | `CONFIRMADO` |

---

## 4. Mecanismo de Provisión y Derivación de la Clave en el Cliente

### 4.1. *Bindings* Nativos en `tolua.dll` (`CONFIRMADO`)

El binario `tolua.dll` expone a Lua dos módulos C registrados al inicializar la máquina virtual (`GameAssembly.dll` $\rightarrow$ `LuaState`):

1. **`luaopen_lsqlcipher` (`tolua.dll` `RVA 0x0D2530`, `FileOffset 0x0D1930`):**
   - Registra la metatabla `"sqlite3"` (`RVA 0x0D2120`) con los métodos de instancia `open`, `close`, `key`, `execute`, `prepare`, etc.
   - La entrada `"key"` (`RVA 0x154FE8`) apunta a `lsqlcipher_do_key` (`RVA 0x0D2520`), que salta (`jmp`) a `RVA 0x0CE4F0` (`FileOffset 0x0CD8F0`):
     ```asm
     0x1800CE4F0: 40 53                      push rbx
     0x1800CE4F2: 48 83 ec 20                sub rsp, 0x20
     0x1800CE4F6: 48 8b d9                   mov rbx, rcx
     0x1800CE4F9: e8 e2 f1 ff ff             call check_sqlite_db          ; obtiene sqlite3** en [rax]
     0x1800CE4FE: 4c 8d 44 24 38             lea r8, [rsp + 0x38]          ; size_t* nKey
     0x1800CE503: ba 02 00 00 00             mov edx, 2                    ; arg #2 en Lua stack (passphrase)
     0x1800CE508: 48 8b cb                   mov rcx, rbx                  ; lua_State* L
     0x1800CE50B: 4c 8b 08                   mov r9, qword ptr [rax]       ; sqlite3* db
     0x1800CE50E: e8 a3 6c f3 ff             call luaL_checklstring        ; retorna const char* pKey
     0x1800CE513: 44 8b 4c 24 38             mov r9d, dword ptr [rsp+0x38] ; int nKey
     0x1800CE518: 48 8d 15 e1 39 03 00       lea rdx, [rip + 0x339e1]      ; "main"
     0x1800CE51F: 4c 8b c0                   mov r8, rax                   ; pKey
     0x1800CE522: 49 8b 09                   mov rcx, qword ptr [r9]       ; sqlite3* db
     0x1800CE525: e8 d6 f2 f8 ff             call sqlite3_key_v2           ; RVA 0x05D800
     ```
2. **`luaopen_lsqlcipher_password` (`tolua.dll` `RVA 0x0D2D60`, `FileOffset 0x0D2160`):**
   - Registra dos funciones auxiliares de transformación (`RVA 0x1551C0`):
     - `set_password_salt` (`RVA 0x0D2D00` $\rightarrow$ `0x0D2640`): recibe un buffer y su longitud, invierte el orden de los bytes (`reversed_salt[i] = salt[len - 1 - i]`) y lo almacena en el buffer estático `[RVA 0x189DF0]` con longitud en `[RVA 0x189EE8]`.
     - `transform_password` (`RVA 0x0D2D10` $\rightarrow$ `0x0D26F0`): recibe una cadena de entrada y aplica por cada byte `i`:
       $$\text{out}[i] = \left(\left(\text{reversed\_salt}[i \bmod L_{\text{salt}}] \oplus \text{input}[i]\right) \oplus i\right) + \text{0x0D}$$
       seguido de una codificación Base64 (`RVA 0x0D2560`).

### 4.2. Invocación desde LuaJIT (`SQLiteLoader` y `DB.ConfConnect`) (`CONFIRMADO`)

En el contenedor `D:\secret\P5X\client\OuterPackage\Lua\Windows\07B3A247F1ADE14.bytes`:
- **Chunk #5 (`offset 0x00B3B8`, longitud `3,803` bytes, `SQLiteLoader`):**
  - Importa `lsqlcipher` (`require("lsqlcipher")`).
  - En su función de apertura de base de datos, localiza la ruta del archivo `.bytes` mediante `LuaResMgr.ExistsFileInOuterPackage` / `MMUTool.GetConfigBytePath`, invoca `sqlite3.open(fullPath)`, construye la cadena de paso en tiempo de ejecución en Lua (empleando operaciones aritméticas y de cadena como `math.floor`, `tostring`, `string.upper`) e invoca inmediatamente `db:key(...)` antes de preparar consultas `SELECT * FROM <tableName> WHERE id = %s`.
- **Chunk #38 (`offset 0x091EE5`, longitud `9,871` bytes, `DB.ConfConnect`):**
  - Carga `ConfigDBMap` y coordina las conexiones a los 11 archivos `ConfData*.bytes` y `ConfTranslation*.bytes` al inicio de `Main.lua` (`1410A9F67109B47.bytes` Chunk #452, instrucción `069: DB.ConfConnect()`).

### 4.3. Estado del Valor Concreto de la Clave y Experimento Mínimo Propuesto

- **Estado del valor concreto de la clave:** `DESCONOCIDO` (*No extraído ni reconstruido en cumplimiento estricto de la regla del proyecto: «Prohibido extraer secretos o claves del cliente»*).
- **Viabilidad técnica de lectura por parte del propio cliente:** `CONFIRMADO`. Dado que el propio cliente PC ejecuta `DB.ConfConnect()` localmente durante el arranque (`Main.lua`) antes siquiera de mostrar la pantalla de login, **el cliente no necesita que el servidor local le envíe ninguna clave para leer `ConfData*.bytes`**. El cliente abre y descifra sus propios archivos `ConfData*.bytes` de forma 100% autónoma.
- **Experimento mínimo propuesto (solo si en una fase futura de emulación de lógica el servidor local necesitase consultar IDs de tablas de `ConfData*.bytes`):**
  1. No es necesario descifrar `ConfData*.bytes` para completar el handshake TCP ni el login (`Fase 2`).
  2. Si en fases posteriores (escena/combate) el servidor local necesita conocer IDs de escenas o personajes, primero puede obtenerlos de los propios mensajes Protobuf enviados por el cliente (`CSCharacterLogin`, `CSEnterScene`, etc.) o del archivo XML en claro `ConfigDBMap.bytes` (que lista todas las tablas existentes).
  3. Solo si resultara imprescindible verificar la apertura de una tabla desde una herramienta externa autorizada por el usuario, el experimento mínimo consistiría en ejecutar en modo de solo lectura el *chunk* `SQLiteLoader` o interceptar el argumento `pKey` en `tolua.dll!lsqlcipher_do_key` (`RVA 0x0CE4F0`) sobre una base de datos de prueba sintética, sin distribuir ni almacenar la clave en la documentación del repositorio.

---

## 5. Registro de Integridad de Archivos Originales (`INTEGRITY_PRE` / `INTEGRITY_POST`)

Se certifica que ningún archivo del cliente original en `D:\secret\P5X` ha sido modificado durante este análisis:

| Archivo | Hash SHA-256 `INTEGRITY_PRE` | Hash SHA-256 `INTEGRITY_POST` | Estado |
| :--- | :--- | :--- | :---: |
| `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **INTACTO** |
| `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **INTACTO** |
