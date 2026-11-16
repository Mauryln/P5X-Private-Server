# Estado del Proyecto P5X y Tareas Pendientes (Handover)

**Fecha de corte:** 15 de Noviembre de 2026, 17:45  
**Entorno de trabajo:** `D:\secret\P5X` (Copia de preservación local)  
**Binarios principales (`GameAssembly.dll`, `P5X.exe`, `global-metadata.dat`):** Intactos y originales.

---

## 1. Estado Actual al Momento del Cierre

### Servidores y Procesos
- **Servidor PoC TCP:** Detenido (`task-44` cancelado limpiamente; puerto `10403` liberado).
- **Procesos en ejecución:** 0 procesos de P5X o servidores en segundo plano.
- **Redirección de Red:** `C:\Windows\System32\drivers\etc\hosts` mantiene la entrada:
  ```text
  127.0.0.1 eulogin.p5xjpupd.com
  ```

### Lo que Funciona al 100% (Verificado y Confirmado)
1. **Red y Autenticación:**
   - Handshake TCP, encuadre de tramas Zeus (`len(4) + msg_id(2) + seq(2) + protobuf`).
   - Flujo completo de login: `CSLoginAuth` (101) $\rightarrow$ `SCLoginResult` (102) $\rightarrow$ `SCLoginGateResult` (104) $\rightarrow$ `SCCharacterLoginResult` (108).
2. **Sincronización de Tiempo y Escena:**
   - Corrección de `zoneTime` aplicada (omitido en `SCLoginResult`).
   - `SCServerTime` (1136) sincronizado en milisegundos Unix epoch.
   - Carga exitosa de la escena de Shibuya (`scn13_shibuya`), spawn del personaje principal (*Wonder*), cámara, iluminación, colisiones y físicas.
   - Movimiento libre con WASD/gamepad, spawn de NPCs de ambientación, diálogos e interacción con entidades del mundo.
3. **Neutralización del Patcher y Verificador de Integridad:**
   - **Problema resuelto:** El juego anteriormente mostraba *"aviso de recursos faltantes"* y redescargaba los bundles originales de CloudFront, sobreescribiendo cualquier parche local.
   - **Corrección lograda:** 
     - Se actualizaron los tamaños en bytes dentro de las tablas binarias FlatBuffers de integridad:
       - `client\OuterPackage\ZeusSetting\RedundantFileCheckSumInfoFB` (y su copia en `StreamingAssets`)
       - `client\OuterPackage\ZeusSetting\SubpackageBundleInfo.txt` (y su copia en `StreamingAssets`)
     - En el último arranque a las 17:39:14, `OuterPackageFileChecker` arrojó:
       ```text
       [CheckRes] Start Check Res 0
       OuterPackageFileChecker Result: None
       [CheckRes] Finish Check Res
       ```
     - Se desactivaron las URLs remotas y flags en:
       - `HotfixLocalConfig.json` (`"openHotfix": false`, `"serverUrls": []`)
       - `ZeusAssetManagerSetting.json` (`"remoteURL": []`)
       - `InstallConfig.json` (`"updateResFirst": false`)
       - `PatcherConfig.json` (`"gameResUrl": []`, `"gameUpdateAssetUrl": []`)
     - El cliente arranca de inmediato sin pedir descargar recursos ni conectar a CloudFront.

---

## 2. Diagnóstico del Fallo de HUD (Causa Raíz)

A pesar de que los 3 bundles de UI (`005\ui_mainui498d6b82.bundle`, `173\ui_s_mainmenu1810ee75.bundle`, `101\ui_nbasedui37afe8ed.bundle`) fueron parchados exitosamente en su contenedor `m_Container` con los alias mayúsculos (`UI-..._EN.prefab`), el log del juego a las 17:40:23 sigue registrando:

```text
26/11/15 17:40:23.243-493 [Log ]Release Asset Error: UI-zhujiemian-ditu-map_EN.prefab  is null. 35458.
26/11/15 17:40:23.243-493 [Log ]Release Asset Error: UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab  is null. 35458.
26/11/15 17:40:23.244-493 [Log ]Release Asset Error: UI-zhujiemian-sns-new_EN.prefab  is null. 35458.
26/11/15 17:40:23.244-493 [Log ]Release Asset Error: UI-zhujiemian-youcegongnengqu01_EN.prefab  is null. 35458.
```

### ¿Por qué falló el parche de `m_Container`?
1. **Capa intermedia de Zeus AssetManager:** El cliente P5X no llama a `AssetBundle.LoadAsset` de Unity a ciegas. Utiliza el framework propietario **Zeus AssetBundleLoader** de Perfect World.
2. Durante la inicialización de UI:
   ```text
   [zeus asset] AssetBundleLoader load asset failed : UI-zhujiemian-youcegongnengqu01_EN.prefab
   GetAssetRes: UI-zhujiemian-youcegongnengqu01_EN.prefab Res is null.
   ```
   Zeus valida el nombre del recurso contra sus propios catálogos internos (como el archivo binario `105\assetMapName.txt` o tablas hash en memoria). Si la clave de búsqueda de Zeus no coincide exactamente o el manifiesto `I18NAssetMap.xml` redirigió el nombre a `_EN` sin que Zeus tenga la entrada correspondiente, el loader rechaza la carga antes o falla al asociarlo con el bundle.
3. **Assets secundarios null:** En el log también fallan:
   - `zhujiemian-taiyang1.png`, `zhujiemian-taiyang2.png`, `zhujiemian-taiyang3.png` (iconos del sol del reloj).
   - Animaciones base: `wonder_uniform@stand_rest_danhuichen_story.anim`, `wonder_uniform@stand_rest_baoxiong_story.anim`.

---

## 3. Hoja de Ruta: Tareas Pendientes (Backlog Ordenado)

### Prioridad 1: Solución Definitiva de la UI (Carga de Prefabs)

Para que los menús, el minimapa y los accesos rápidos (`[M]`, `[J]`) carguen y respondan en Shibuya, se debe implementar una de las siguientes vías:

1. **Vía A — Forzar Sufijo `_JP` o Locale Japonés (Recomendada):**
   - *Hallazgo:* Todos los prefabs con sufijo `_JP` (`ui-zhujiemian-ditu-map_jp.prefab`, etc.) **existen de forma nativa e íntegra en los bundles originales del juego**.
   - En el archivo `ProjectResource.RelocateI18NAssetName` o en el método de inicialización de idioma:
     - Investigar cómo obligar a que el cliente use el dialecto/recursos `_JP` (o nombre base) para los prefabs de UI.
     - Si se inicia con locale `ja-JP` o se intercepta `Application.systemLanguage` para devolver `Japanese`, el cliente pedirá directamente los prefabs `_JP` existentes y el HUD cargará sin necesidad de alterar bundles.
2. **Vía B — Redirección en `I18NAssetMap.xml`:**
   - Desempaquetar `070\i18n_manifest277deefb.bundle` con UnityPy.
   - En el archivo `I18NAssetMap.xml`, en la sección `<Assets>`, redirigir las 4 entradas de UI para que en lugar de mapear a `_EN`, apunten a la variante existente o no reescriban el nombre.
3. **Vía C — Modificación Quirúrgica en `GameAssembly.dll`:**
   - Dado que el usuario ya autorizó modificar binarios en la copia `D:\secret`, se puede patchear en `GameAssembly.dll` la instrucción que concatena `_EN` al cargar prefabs de UI, o noquear la llamada en `InitLanguage` / `RelocateI18NAssetName` para que devuelva el nombre original sin sufijo o siempre devuelva `_JP`.
4. **Vía D — Depuración de `openGM`:**
   - Una vez que la UI cargue, probar el cliente con `openGM = False` en `poc_login_server.py`. Si la escena y el HUD funcionan con `openGM = False`, revertir definitivamente el parche de `openGM = True`.

---

### Prioridad 2: Implementación de Combate PvE

Actualmente el servidor cuenta con un stub que reconoce los paquetes de batalla pero no gestiona la lógica de turnos.
- **Mensajes a completar en `poc_login_server.py`:**
  - `CSBattleStart` (3001) $\rightarrow$ Responder con `SCBattleStartResult` (3002) incluyendo datos de monstruos y equipo.
  - `CSBattleAction` (3003) $\rightarrow$ Responder con `SCBattleTurnNotice` (3004) y sincronización de daño.
  - `CSBattleFinish` (3005) $\rightarrow$ Responder con `SCBattleResult` (3006) para volver al mapa sin desincronización.

---

### Prioridad 3: Persistencia de Datos con SQLite

Actualmente el estado de Wonder (posición, nivel, inventario) se mantiene en memoria en `poc_login_server.py`.
- **Tareas de persistencia:**
  1. Crear base de datos SQLite local `p5x_server.db`.
  2. Tablas mínimas requeridas:
     - `accounts` (uid, token, username, created_at).
     - `characters` (role_id, name, level, exp, hp, sp, scene_id, pos_x, pos_y, pos_z, rot_y).
     - `inventory` (role_id, item_id, count).
     - `personas` (role_id, persona_id, level, skills).
  3. Guardar las coordenadas al recibir `CSSceneMoveStop` (1209) para que al reconectar el personaje aparezca donde se quedó.

---

## 4. Estado de Archivos y Backups

| Archivo / Componente | Estado Actual | Ubicación Backup |
| :--- | :--- | :--- |
| `005\ui_mainui498d6b82.bundle` | Parchado con alias mayúsculas | `ui_mainui498d6b82.bundle.bak` |
| `173\ui_s_mainmenu1810ee75.bundle` | Parchado con alias mayúsculas | `ui_s_mainmenu1810ee75.bundle.bak` |
| `101\ui_nbasedui37afe8ed.bundle` | Parchado con alias mayúsculas | `ui_nbasedui37afe8ed.bundle.bak` |
| `OuterPackage\ZeusSetting\RedundantFileCheckSumInfoFB` | Tamaños actualizados al byte | `...RedundantFileCheckSumInfoFB.bak` |
| `OuterPackage\ZeusSetting\SubpackageBundleInfo.txt` | Tamaños actualizados al byte | `...SubpackageBundleInfo.txt.bak` |
| `StreamingAssets\ZeusSetting\BuildinSetting\HotfixLocalConfig.json` | `openHotfix: false`, URLs vacías | `...HotfixLocalConfig.json.bak` |
| `StreamingAssets\ZeusSetting\ZeusAssetManagerSetting.json` | `remoteURL: []` | `...ZeusAssetManagerSetting.json.bak` |
| `P5XLaunch\ResFilesM\1000173\PatcherConfig\InstallConfig.json` | `updateResFirst: false` | `...InstallConfig.json.bak` |
| `P5XLaunch\ResFilesM\1000173\PatcherConfig\PatcherConfig.json` | URLs de recursos vacías | `...PatcherConfig.json.bak` |

---

## 5. Prompt de Reanudación para el Siguiente Chat

Copia y pega el siguiente bloque en la nueva conversación para retomar exactamente en este punto:

```markdown
# Reanudación — P5X (HUD / Prefabs de UI y Combate)

## Contexto y Estado
- Copia de trabajo: D:\secret\P5X. Los 5 binarios nativos principales están intactos.
- Login, escena Shibuya, movimiento y NPCs confirmados y funcionando.
- Se neutralizó la verificación de recursos de Zeus (OuterPackageFileChecker Result: None) y se deshabilitó la redescarga remota de CloudFront.
- Servidores cerrados (puerto 10403 libre).

## Problema Pendiente Crítico
- El HUD (minimapa, menú y botonera) sigue fallando con "Release Asset Error: UI-..._EN.prefab is null".
- Zeus AssetBundleLoader no resuelve los alias inyectados en m_Container.
- Sin embargo, todos los prefabs con sufijo _JP existen de forma íntegra en los bundles originales.

## Tareas a Realizar (en este orden)
1. Investigar y aplicar una solución limpia para que el cliente cargue los prefabs de UI:
   - Forzar locale ja-JP / sufijo _JP (en ProjectResource.RelocateI18NAssetName o parámetros de inicio), O BIEN
   - Patchear GameAssembly.dll en la copia local para que pida prefabs _JP o base.
2. Iniciar el servidor PoC (python scratch/poc_login_server.py --port 10403) y verificar en Player.log que los 4 prefabs de UI carguen sin error.
3. Probar respuesta de botones y teclas [M] y [J] en Shibuya.
4. Si la UI funciona, probar openGM = False y avanzar a combate PvE y persistencia SQLite.
```
