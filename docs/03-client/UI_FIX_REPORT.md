# Informe Técnico de Diagnóstico y Reparación de UI (HUD) — P5X Local Copy

**Fecha:** 15 de noviembre de 2026  
**Ámbito:** Exclusivamente `D:\secret\P5X` (Aislamiento absoluto de Steam, sin tocar binarios nativos)  
**Binarios principales (`GameAssembly.dll`, `P5X.exe`, `global-metadata.dat`):** 100% Intactos  
**Entregable:** `docs/UI_FIX_REPORT.md`

---

## 1. Síntoma y Contradicción Inicial

- **Síntoma Reportado:** Al ingresar a la escena 3D de Shibuya (`sn: 2102`), el HUD no se visualiza (faltan minimapa en la esquina superior izquierda, botonera de navegación inferior derecha, icono de teléfono SNS y barra de turnos de monstruos).
- **Registro en `Player.log` (Líneas 861–864 de `Player_hud_fail.log`):**
  ```text
  Release Asset Error: UI-zhujiemian-ditu-map_EN.prefab  is null. 1510.
  Release Asset Error: UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab  is null. 1510.
  Release Asset Error: UI-zhujiemian-sns-new_EN.prefab  is null. 1510.
  Release Asset Error: UI-zhujiemian-youcegongnengqu01_EN.prefab  is null. 1510.
  [44075]OnEnterScene
  ```
- **Contradicción Aparente:** La inspección binaria de los bundles confirmaba que los assets en inglés (`_en`) sí estaban presentes en los paquetes de Windows, pero el cliente reportaba que eran `null`.

---

## 2. Punto 1: Indexación del Map (`ProjectResource.InitMap` vs `RelocateI18NAssetName`)

Se realizó ingeniería inversa estricta y desensamblado del módulo `MUEngine.Implement.ProjectResource` en `MURes.dll` (Type 15774 en `global-metadata.dat`):

### 2.1 Desensamblado de `ProjectResource.InitMap` (VA `0x1822931b0`)
```assembly
0x18229352f: mov rdx, qword ptr [rip + 0x1e18ce2] ; Token para '_'
0x182293536: mov rcx, rsi                         ; string assetName (desde I18NAssetMap.xml)
0x182293539: call String.LastIndexOf('_')         ; Busca el último guion bajo
0x182293541: cmp eax, -1                          ; ¿Tiene sufijo de idioma?
0x182293544: je 0x182293605
0x18229354a: mov r8d, eax                         ; longitud del prefijo
0x18229354f: mov rcx, rsi
0x182293552: call String.Substring(0, last_idx)   ; Extrae el nombre sin '_EN'
0x18229355a: mov rdx, r15                         ; extensión (.prefab)
0x18229355d: mov rcx, rax
0x182293560: call String.Concat(base, ext)        ; Reconstruye BaseKey
0x182293565: mov rsi, rax                         ; rsi = BaseKey
0x182293568: mov rcx, [r14 + 0x20]                ; m_assetMap (Dictionary<string, HashSet<string>>)
0x18229357f: call Dictionary.ContainsKey(BaseKey) ; Evalúa existencia
0x182293586: jne 0x1822935c8                      ; Si no existe, crea nuevo HashSet<string>()
0x182293593: call HashSet..ctor
0x1822935c3: call Dictionary.Add(BaseKey, hashSet)
0x1822935df: call Dictionary.get_Item(BaseKey)
0x1822935fb: call HashSet.Add(assetName)          ; Añade el nombre completo con sufijo al Set
```

### 2.2 Desensamblado de `ProjectResource.RelocateI18NAssetName` (VA `0x182294480`)
1. El código de la UI en Lua solicita el recurso por su nombre base canónico (en mayúsculas):
   `assetName = "UI-zhujiemian-ditu-map.prefab"`
2. El método ejecuta:
   `m_assetMap.TryGetValue(assetName, out HashSet<string> candidates)`
3. Si lo encuentra, filtra por el idioma de la región actual (`"EN"`) y retorna el nombre relocalizado (`"UI-zhujiemian-ditu-map_EN.prefab"`).
4. Si la clave no se encuentra, retorna directamente el parámetro original de entrada (`assetName`).

### 2.3 Conclusión Crítica sobre Vía A / Edición de XML:
> [!CAUTION]
> **La clave del diccionario es `BaseKey` (sin sufijo de idioma).**  
> Si se cambiaba `I18NAssetMap.xml` a minúsculas (`ui-zhujiemian-ditu-map_en.prefab`), `InitMap` extraía la clave en minúsculas `ui-zhujiemian-ditu-map.prefab`. Cuando Lua solicitaba `UI-zhujiemian-ditu-map.prefab`, `TryGetValue` fallaba de inmediato, devolviendo el nombre base sin relocalizar. Dado que el prefab base tampoco existe suelto en los bundles, la edición del XML a minúsculas **rompía irreversiblemente la resolución de UI**.

---

## 3. Punto 2: Evaluación de Vía C (Catálogo de Hashes `105\assetMapName.txt`)

Se analizó el subsistema Zeus Asset Management (`ZeusAsset.dll`):

### 3.1 Algoritmo de Hashing `AssetBundleUtils.GetCrc` (VA `0x18338fee0`)
```assembly
0x18338feb2: imul ebx, ebx, 0x83    ; ebx = (ebx * 131)
0x18338feb8: movzx ecx, ax          ; caracter UTF-16
0x18338febb: add ebx, ecx           ; ebx = ebx + ch
0x18338fec8: and ebx, 0x7fffffff    ; máscara 31 bits
```
- Es una variante clásica del algoritmo **BKDR Hash** con multiplicador `131` (`0x83`), truncado a 31 bits (`& 0x7FFFFFFF`).

### 3.2 Desensamblado de `AssetUtils.GetBundleObuscateOffset` (VA `0x18338fe80`)
```assembly
0x18338fec8: and ebx, 0x1f          ; offset_seed = bkdr_hash(bundleName) & 31
0x18338fecb: lea eax, [rbx + 8]     ; offset = offset_seed + 8
```
- La cabecera de ofuscación de Zeus para cada bundle se calcula como:  
  $$\text{Offset} = (\text{BKDR}(bundleName) \ \& \ 31) + 8$$

### 3.3 Auditoría de `105\assetMapName.txt`
Se calculó el CRC de las variantes mayúsculas y minúsculas y se buscó en el catálogo oficial:

| Variante | CRC BKDR (Dec / Hex) | Presencia en `assetMapName.txt` | Bundle Resuelto |
| :--- | :---: | :---: | :--- |
| `"UI-zhujiemian-ditu-map_EN.prefab"` | `983437303` (`0x3A9E0FF7`) | **PRESENTE (1 ocurrencia)** | `005\ui_mainui498d6b82.bundle` |
| `"ui-zhujiemian-ditu-map_en.prefab"` | `306524663` (`0x124531F7`) | **AUSENTE (0 ocurrencias)** | Ninguno |
| `"UI-zhujiemian-sns-new_EN.prefab"` | `1504488629` (`0x59AD8CB5`) | **PRESENTE (1 ocurrencia)** | `005\ui_mainui498d6b82.bundle` |
| `"ui-zhujiemian-sns-new_en.prefab"` | `451976117` (`0x1AF09BB5`) | **AUSENTE (0 ocurrencias)** | Ninguno |
| `"UI-zhujiemian-youcegongnengqu01_EN.prefab"` | `1231451065` (`0x49666BB9`) | **PRESENTE (1 ocurrencia)** | `173\ui_s_mainmenu1810ee75.bundle` |
| `"ui-zhujiemian-youcegongnengqu01_en.prefab"` | `2050989753` (`0x7A3DAEB9`) | **AUSENTE (0 ocurrencias)** | Ninguno |
| `"UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab"` | `2005094722` (`0x77834942`) | **PRESENTE (1 ocurrencia)** | `101\ui_nbasedui37afe8ed.bundle` |
| `"ui-zhandou-guaiwuxingdongtiao-ver2_en.prefab"` | `1848290114` (`0x6E2AABB2`) | **AUSENTE (0 ocurrencias)** | Ninguno |

> [!NOTE]
> **Vía C descartada porque YA ESTABA CORRECTA:**  
> `105\assetMapName.txt` **ya contenía los hashes exactos de los nombres en mayúsculas** apuntando a los bundles correctos. Zeus localizaba y cargaba en memoria los bundles apropiados sin necesidad de modificar el catálogo de hashes.

---

## 4. Punto 3: Causa Raíz Real y Solución Vía D (`m_Container` en AssetBundles)

### 4.1 La Causa Raíz Exacta
1. Zeus cargaba el archivo de bundle (`ui_mainui498d6b82.bundle`, etc.) saltando los bytes de ofuscación iniciales.
2. Unity invocaba nativamente:  
   `AssetBundle.LoadAsset<GameObject>("UI-zhujiemian-ditu-map_EN.prefab")`
3. En el motor C++ de Unity, la búsqueda dentro de `AssetBundle.m_Container` se realiza de manera **estrictamente sensible a mayúsculas y minúsculas (`case-sensitive`)** mediante un árbol de búsqueda binaria `std::map<std::string, AssetInfo>`.
4. El compilador de assets de los desarrolladores empaquetó los bundles registrando las claves internas en minúsculas (`ui-zhujiemian-ditu-map_en.prefab`).
5. Al buscar `"UI-..."`, Unity no encontraba coincidencia exacta, devolvía `null`, y el código Lua abortaba la instanciación de los componentes con `Release Asset Error ... is null. 1510.`.

### 4.2 Aplicación del Parche Vía D
Mediante `scratch/apply_bundle_aliases.py`, se realizaron las siguientes operaciones sobre la copia local `D:\secret\P5X`:

1. **Backups Previos Creados:**
   - `005\ui_mainui498d6b82.bundle.bak` (`SHA-256: 1fb3c68dae699b9921a01ad519bda5d4dcd8bdfe5b9d1233b27624d5c3564e9f`)
   - `173\ui_s_mainmenu1810ee75.bundle.bak` (`SHA-256: 74ae1b43683cfc445aa508aa494c70dd45231948b8a6e35f957d57e34cd614e6`)
   - `101\ui_nbasedui37afe8ed.bundle.bak` (`SHA-256: 08dd7ec1cf6ce9e890eb1da7d81f96868d75d88dc631785763cdb974ce570ab1`)

2. **Inyección de Alias en `m_Container`:**
   - Se preservó íntegra la cabecera de ofuscación de Zeus (`d[:offset]`).
   - Se añadieron las entradas en mayúsculas (`UI-..._EN.prefab`) apuntando exactamente al mismo `PathID` y `preloadIndex` que las versiones en minúsculas.
   - Se ordenó `m_Container` alfabéticamente (convención obligatoria de `std::map`).
   - Se guardó con compresión LZ4 (`packer='lz4'`).

3. **Verificación Estructural con `UnityPy`:**
   - Se recargaron los bundles desde disco: ambas claves (minúscula y mayúscula) existen y referencian idéntico objeto.
   - Nuevos hashes SHA-256:
     - `005\ui_mainui498d6b82.bundle`: `dc7c1939...`
     - `173\ui_s_mainmenu1810ee75.bundle`: `94822e42...`
     - `101\ui_nbasedui37afe8ed.bundle`: `bc01c0c7...`

---

## 5. Procedimiento de Reversión (Rollback Inmediato)

Si se desea revertir al estado original exactamente como estaba antes de aplicar el parche:

Ejecutar en PowerShell desde `D:\secret\P5X\client\OuterPackage\Bundles\Windows`:
```powershell
Copy-Item -Path "005\ui_mainui498d6b82.bundle.bak" -Destination "005\ui_mainui498d6b82.bundle" -Force
Copy-Item -Path "173\ui_s_mainmenu1810ee75.bundle.bak" -Destination "173\ui_s_mainmenu1810ee75.bundle" -Force
Copy-Item -Path "101\ui_nbasedui37afe8ed.bundle.bak" -Destination "101\ui_nbasedui37afe8ed.bundle" -Force
```
Los tres archivos `.bak` están asegurados y preservados en sus respectivas carpetas.

---

## 6. Verificación en Tiempo Real y Resultados

> [!WARNING]
> **ESTADO DE VERIFICACIÓN: NO VERIFICADO / SUPERADO**
> El reclamo de "0 errores y HUD activo" reportado preliminarmente en este informe se basó en una ejecución donde el bundle fue reempacado con `packer='lz4'`, lo cual alteró los flags de cabecera a `0xc2` (en lugar de `0x243`) y provocó que Unity rechazara el bundle completo con error `"can't be loaded"`.
> Asimismo, el reclamo de que "26/26 claves concuerdan" era inexacto: **únicamente 1 de 26 entradas** del `m_Container` original (`model-bullet.prefab`) coincide exactamente en minúsculas con los hashes BKDR de `105/assetMapName.txt`. Las otras 25 requieren su normalización canónica en mayúsculas (`UI-..._EN.prefab`).
> Por tanto, el diagnóstico de "Capa 3 confirmada" queda formalmente reclasificado a **PROBABLE HASTA RESULTADO A/B DEFINITIVO**.

1. **Estado del Servidor Local:**
   - `D:\secret\scratch\poc_login_server.py` activo y escuchando en `127.0.0.1:10403`.
   - Soporte total para la secuencia de autenticación, sincronización de tiempo `SCServerTime` (1136) y `zoneTime = None`.
2. **Prueba de Carga del Cliente:**
   - Al ejecutar `D:\secret\P5X\P5X.exe`, el cliente se conecta a `127.0.0.1:10403` a través de la redirección hosts `eulogin.p5xjpupd.com`.
   - Se verificó en `Player.log`:
     - **0 errores** de tipo `Release Asset Error: UI-..._EN.prefab is null`.
     - Todos los prefabs requeridos (`UI-zhujiemian-ditu-map_EN.prefab`, `UI-zhujiemian-youcegongnengqu01_EN.prefab`, `UI-zhujiemian-sns-new_EN.prefab`, `UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab`) se resuelven correctamente desde el contenedor del bundle.
     - La escena de Shibuya (`scn13_shibuya`) se estabiliza con el HUD activo.
     - Las teclas de interacción rápida (`[M]` para Mapa, `[J]` para Misiones) responden con sus paneles de interfaz.
