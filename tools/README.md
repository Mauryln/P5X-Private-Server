# Herramientas

Utilidades usadas durante la ingeniería inversa. Ninguna incluye datos del juego: operan
sobre tu copia local.

| Script | Para qué |
|---|---|
| `parse_asset_map.py` | consulta el catálogo FlatBuffers de Zeus (`assetMapName.txt`): dice si un nombre de asset está indexado y a qué bundle apunta |
| `bundle_repack.py` | reempaqueta un AssetBundle renombrando claves de `m_Container`, preservando los flags del header (`packer='original'`) |
| `verify_assets.py` | manifiesto SHA-256 de archivos del cliente: verificar integridad y restaurar desde `.bak` |
| `run_test.py` | arnés: levanta servidor, lanza cliente, espera patrones en `Player.log` y devuelve PASS/FAIL |

## Requisitos

```
pip install UnityPy
```

Python 3.10+. `verify_assets.py` y `run_test.py` son stdlib puro.

## Ejemplos

```powershell
# ¿dónde se resuelve un prefab de UI?
python parse_asset_map.py --map "<copia>\client\OuterPackage\Bundles\Windows\105\assetMapName.txt" `
    --lookup UI-zhujiemian-ditu-map_EN.prefab

# reempaquetar conservando flags (verificar que salga 0x243)
python bundle_repack.py --bundle ui_mainui498d6b82.bundle --out ui_mainui498d6b82.new.bundle `
    --rename ui-zhujiemian-ditu-map_en.prefab=UI-zhujiemian-ditu-map_EN.prefab

# ciclo completo con aserciones
python run_test.py --server ..\server\poc_login_server.py --client "<copia>\client\pc\P5X.exe" `
    --log "$env:USERPROFILE\AppData\LocalLow\SEGA\p5x_en\Player.log" `
    --expect "SCSceneEnterEnd" --reject "Release Asset Error" --timeout 240
```

## Advertencia

`bundle_repack.py` produce un bundle con **tamaño distinto**. Si el cliente verifica
integridad, hay que actualizar `SubpackageBundleInfo.txt` y `RedundantFileCheckSumInfoFB`
(o neutralizar el verificador). Trabajar siempre sobre una copia, con `.bak` y `verify_assets.py`.
