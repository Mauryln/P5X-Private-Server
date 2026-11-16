# Registro Técnico de Descubrimientos de Ingeniería Inversa (REVERSE_ENGINEERING.md)

**Proyecto:** Preservación Comunitaria y Reconstrucción Fiel de Servidor — *Persona 5: The Phantom X (P5X)*  
**Ámbito de Trabajo:** `D:\secret\P5X` (Aislamiento absoluto de la instalación de Steam según `Rules.md`)  
**Herramientas de Análisis:** REA (Reverse Engineer Anything MCP), Ghidra (`C:\Tools\Ghidra`), LuaJIT 2.1 bytecode decompiler, UnityPy.

---

## 1. Verificación Criptográfica de Binarios Analizados

| Binario / Artefacto | Ruta Canónica | Hash SHA-256 Verificado | Estado |
| :--- | :--- | :--- | :---: |
| `GameAssembly.dll` | `client\pc\GameAssembly.dll` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **INTACTO** |
| `P5X.exe` (Cliente) | `client\pc\P5X.exe` | `1AEFAE93BC4EEA217185360D7C103CB2F125B60CED88D28E7A627EDF878D0666` | **INTACTO** |
| `global-metadata.dat` | `client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **INTACTO** |
| `steam_api64.dll` | `client\pc\P5X_Data\Plugins\x86_64\steam_api64.dll` | `1ADD7F151FA644870A735AE86E68D1F019F296130D8E7C0A7ED3ECC7482DCCBC` | **INTACTO** |
| `P5X.exe` (Launcher) | `P5X.exe` | `FE1D12F81DDA178DE6A4B86E2DEBA2162C3DD855E7726DB4B19FA036823BD39E` | **INTACTO** |
| `allMsgPb.bytes` | `client\OuterPackage\Lua\Windows\allMsgPb.bytes` | `2D4AEE2C04A861414317F7403D933793D4CB932F393F53D2229B8DA6119F3700` | **INTACTO** |

---

## 2. Descubrimientos de Criptografía y Framing de Red

### 2.1 Handshake Trama 0 (RC4 Key Exchange)
- **Confirmado por:** Análisis dinámico y desensamblado de `Utils.RC4`.
- **Estructura:** El servidor emite una trama preliminar `[int32 BE 4 + K][keyBytes]`.
- El cliente invoca `Utils.RC4(keyBytes)` e inicializa su cifrador de flujo RC4 descartando los primeros 1024 bytes de keystream (*drop 1024*).
- Ambas direcciones de tráfico posterior utilizan este cifrador de flujo con claves independientes o sincronizadas.

### 2.2 Encuadre de Tramas Zeus (Zeus Framing)
- **Cabecera de 8 bytes:**
  - `length`: 4 bytes uint32 Big-Endian (longitud total del paquete excluyendo los 4 bytes de longitud).
  - `msg_id`: 2 bytes uint16 Big-Endian (identificador Protobuf de mensaje).
  - `seq`: 2 bytes uint16 Big-Endian (número de secuencia incremental).
- **Cuerpo:** Payload Protobuf2 serializado.

---

## 3. Descubrimientos en IL2CPP y C# (`GameAssembly.dll`)

### 3.1 Resolución de Recursos Multilenguaje (`ProjectResource`)
- **Tipo en metadata:** Type 15774 (`MUEngine.Implement.ProjectResource`).
- **`ProjectResource.InitMap` (VA `0x1822931b0`):**
  - Lee `I18NAssetMap.xml`.
  - Extrae `BaseKey` buscando el último guion bajo `_` (`String.LastIndexOf('_')`).
  - Almacena en `m_assetMap` (`Dictionary<string, HashSet<string>>`).
- **`ProjectResource.RelocateI18NAssetName` (VA `0x182294480`):**
  - Consulta `BaseKey` en `m_assetMap`.
  - Si el idioma actual de Unity (`Application.systemLanguage`) es distinto de `MainLanguage` (ej. `"EN"`), concatena `_EN.prefab`.
  - Si `Application.systemLanguage` es `Japanese`, o el idioma no coincide con `MultiLanguages`, carga la variante `_JP` o el asset base.
- **Detección de Idioma de Unity:**
  - En `UnityPlayer.dll`, `Application.systemLanguage` se determina mediante `kernel32!GetUserDefaultLCID()`.
  - El launcher `Config.ini` y parámetros de línea de comandos (`-language`) no tienen efecto sobre el cliente.

### 3.2 Hashing y Ofuscación de AssetBundles Zeus
- **Algoritmo:** BKDR Hash (`ebx = (ebx * 131) + ch; ebx &= 0x7FFFFFFF`).
- **Ofuscación de cabecera:** $\text{Offset} = (\text{BKDR}(bundleName) \ \& \ 31) + 8$.
- **Catálogo de Hashes (`105\assetMapName.txt`):**
  - Contiene indexados los hashes BKDR de 137,467 assets, correspondientes a rutas canónicas con prefijo en mayúsculas (`UI-zhujiemian-ditu-map_EN.prefab`).
  - **Corrección de métrica (Auditoría Cripto-Binaria):** De las 26 claves del `m_Container` del bundle original `005\ui_mainui498d6b82.bundle`, **únicamente 1 de 26** (`model-bullet.prefab`, hash `414846988`) concuerda tal cual en minúsculas. Las otras 25 solo concuerdan si se convierten a mayúsculas canónicas (`UI-...`).
  - **Dictamen:** Hipótesis de "Capa 3 (m_Container) confirmada" degradada formalmente a **PROBABLE HASTA RESULTADO A/B**.

---

## 4. Descubrimientos en Bytecode LuaJIT 2.1

### 4.1 Refutación de `isClientBattle`
- **Escaneo exhaustivo:** 7,364 chunks en 18 contenedores `.bytes` y 143,287 símbolos en `global-metadata.dat`.
- **Resultado:** 0 referencias a `isClientBattle` en código ejecutable.
- `LoginMod:OnGetSCServerConfigMsg` (`E8DF29521A39C99.bytes[0]`, Proto 43) lee únicamente `openGM`, `baseTime` y `timeNow`. El campo `isClientBattle` se descarta sin procesar.
- **Conclusión:** El cliente P5X no calcula combates en local. Toda la resolución lógica (daño, habilidades, turnos) debe ser provista por el servidor.

### 4.2 Anomalía Temporal y Fix de `zoneTime`
- `LoginMod:OnSCLoginResult` calcula `_G.TimeZoneDiff = local_2010 - msg.zoneTime`.
- Si `zoneTime` se provee como época Unix (~1.700.000.000), produce un offset negativo masivo que convierte tiempos de servidor en fechas anteriores a 1970.
- En la biblioteca C de Windows (`ucrtbase.dll`), `os.date` retorna `nil` para timestamps negativos, crasheando `ServerTimeMod:GetOpenServerDay0()`.
- **Solución confirmada:** Omitir el campo opcional `zoneTime` (`zoneTime = None`) en `SCLoginResult` (102).
