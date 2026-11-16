# Registro de Bloqueos Técnicos y Diagnóstico Forense (KNOWN_BLOCKERS.md)

**Proyecto:** Preservación Comunitaria y Reconstrucción Fiel de Servidor — *Persona 5: The Phantom X (P5X)*  
**Fecha de Corte:** 16 de noviembre de 2026

---

## 1. Bloqueo 1 (Crítico): Fallo de Instanciación de HUD / UI en Shibuya

### 1.1 Síntoma
El cliente entra a la escena 3D de Shibuya (`sn: 2102`), Wonder puede moverse con colisiones y hablar con NPCs, pero la interfaz gráfica (minimapa, menú inferior derecho de funciones, botón SNS, barra de combate) no aparece en pantalla. Al presionar `[M]` (Mapa) o `[J]` (Misiones), el juego no responde.

### 1.2 Causa Raíz Confirmada
1. En máquinas Windows configuradas con idioma inglés o español, `UnityPlayer.dll` consulta `kernel32!GetUserDefaultLCID()` y reporta `System Language: EN`.
2. `ProjectResource.RelocateI18NAssetName` en `GameAssembly.dll` (VA `0x182294480`) busca si el idioma está en `MultiLanguages` (`EN`) y redirige las solicitudes de prefabs concatenando el sufijo `_EN.prefab`:
   - `UI-zhujiemian-ditu-map_EN.prefab`
   - `UI-zhujiemian-youcegongnengqu01_EN.prefab`
   - `UI-zhujiemian-sns-new_EN.prefab`
   - `UI-zhandou-guaiwuxingdongtiao-ver2_EN.prefab`
3. En la instalación original offline de Windows, estos prefabs no existen con sufijo `_EN` sueltos en los bundles (se descargaban vía CDN oficial) o sus nombres difieren en mayúsculas/minúsculas y Zeus AssetBundleLoader falla al resolverlos arrojando:
   `Release Asset Error: UI-..._EN.prefab is null`
4. Sin embargo, **todos los prefabs con sufijo `_JP` existen íntegros y completos** en los bundles originales (`005\ui_mainui498d6b82.bundle`, etc.).

### 1.3 Estado de Solución
- **Intentos Fallidos:**
  - Editar `I18NAssetMap.xml` a minúsculas: Rompió el diccionario `m_assetMap` que usa claves sin sufijo en mayúsculas.
  - Inyectar alias en `m_Container` de Unity: Zeus AssetBundleLoader intermedia antes de Unity y requiere correspondencia en catálogos internos.
  - Parámetros CLI (`-language`): UnityPlayer no los soporta.
- **Vía de Solución en Curso:**
  - Forzar locale japonés (`ja-JP` / LCID `0x0411`) a nivel de proceso o mediante shim liviano / hook Win32 para que `Application.systemLanguage` retorne `Japanese`, haciendo que el juego cargue de forma natural y limpia los prefabs `_JP` originales sin alterar bundles.
  - Alternativamente, aplicar parche quirúrgico en `GameAssembly.dll` de la copia local de trabajo en `RelocateI18NAssetName`.

---

## 2. Bloqueo 2 (Alto): Ausencia de Motor de Combate PvE en Servidor

### 2.1 Síntoma
No es posible combatir contra sombras ni monstruos en el mundo. Aunque se envíen paquetes iniciales, el juego no puede resolver las acciones de batalla.

### 2.2 Causa Raíz Confirmada
- Se demostró empíricamente y por desensamblado que la hipótesis de `isClientBattle` es falsa: el cliente no calcula daño ni turnos.
- El módulo de cliente `TbTickMod` solo actúa como receptor y reproductor de animaciones de resultados precalculados por el servidor (`SCFightRoundBattleSkill` 1327 y `DRoundSkillResult`).
- El servidor actualmente solo cuenta con stubs en `proto2_codec.py`, sin máquina de turnos ni cálculo de estadísticas.

### 2.3 Plan de Resolución
Implementar el ciclo completo de combate en el servidor:
1. `CSEnterFight` (1302) $\to$ `SCFightRoundTime` (1326).
2. `CSRoundSkillList` (1325) $\to$ Generación de daño y efectos en `SCFightRoundBattleSkill` (1327).
3. `CSFightHumanPlayEnd` (1331) $\to$ `SCFightRoundEnd` (1332) $\to$ `SCFightBattleEnd` (1333).

---

## 3. Bloqueo 3 (Medio): Falta de Persistencia Relacional

### 3.1 Síntoma
El progreso del avatar (coordenadas, objetos, nivel) se pierde al reiniciar el servidor en Python.

### 3.2 Causa Raíz Confirmada
Los datos se almacenan en variables en memoria en `poc_login_server.py`.

### 3.3 Plan de Resolución
Implementar base de datos SQLite (`p5x_server.db`) e integrar consultas transaccionales en los manejadores de movimiento (`CSSceneMoveStop` 1209) e inicialización (`SCInitData` 1102).
