<#
.SYNOPSIS
    Deja el cliente de P5X en modo offline (sin hotfix, sin CDN) o lo revierte.

.DESCRIPTION
    Vacia las URLs remotas y apaga la actualizacion/verificacion de paquetes para que
    el cliente arranque sin pedir recursos a CloudFront. Modifica SOLO archivos de
    configuracion JSON de la copia indicada, creando un backup `<archivo>.p5x-backup`
    por cada uno. Pensado para una copia de trabajo: revertir antes de jugar en linea.

    Archivos y cambios (ver docs/01-status/STATUS_AND_REMAINING_WORK.md §1):
      HotfixLocalConfig.json      openHotfix=false, serverUrls=[], controlDataUrls=[],
                                  autoPreDownload=false
      ZeusAssetManagerSetting.json bundleLoaderSetting.remoteURL=[]
      PatcherConfig.json          gameResUrl=[], gameUpdateAssetUrl=[]
      InstallConfig.json          updateResFirst=false

    Esto no toca binarios ni bundles. Si ademas reempaquetas assets, hay que ajustar
    los tamanos en SubpackageBundleInfo.txt y RedundantFileCheckSumInfoFB.

.PARAMETER GameRoot
    Ruta de la copia del juego (la que contiene P5XLaunch y client\pc).

.PARAMETER Revert
    Restaura cada archivo desde su `.p5x-backup`.

.PARAMETER DryRun
    Muestra los cambios sin escribir nada.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\offline_config.ps1 -GameRoot "D:\P5X" -DryRun
    powershell -ExecutionPolicy Bypass -File tools\offline_config.ps1 -GameRoot "D:\P5X"
    powershell -ExecutionPolicy Bypass -File tools\offline_config.ps1 -GameRoot "D:\P5X" -Revert
#>
[CmdletBinding(DefaultParameterSetName = 'Apply')]
param(
    [Parameter(Mandatory)]
    [string]$GameRoot,

    [Parameter(ParameterSetName = 'Revert')]
    [switch]$Revert,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $GameRoot)) { throw "No existe GameRoot: $GameRoot" }

$Edits = @(
    @{
        File    = 'HotfixLocalConfig.json'
        Changes = [ordered]@{
            'openHotfix'      = $false
            'serverUrls'      = @()
            'controlDataUrls' = @()
            'autoPreDownload' = $false
        }
    },
    @{
        File    = 'ZeusAssetManagerSetting.json'
        Changes = [ordered]@{
            'bundleLoaderSetting.remoteURL' = @()
        }
    },
    @{
        File    = 'PatcherConfig.json'
        Changes = [ordered]@{
            'gameResUrl'         = @()
            'gameUpdateAssetUrl' = @()
        }
    },
    @{
        File    = 'InstallConfig.json'
        Changes = [ordered]@{
            'updateResFirst' = $false
        }
    }
)

function Find-ConfigFiles([string]$name) {
    return @(Get-ChildItem -Path $GameRoot -Recurse -File -Filter $name -ErrorAction SilentlyContinue)
}

function Get-Node($obj, [string]$path) {
    $node = $obj
    foreach ($part in $path.Split('.')) {
        if ($null -eq $node -or -not ($node.PSObject.Properties.Name -contains $part)) {
            return $null
        }
        $node = $node.$part
    }
    return $node
}

function Set-Node($obj, [string]$path, $value) {
    $parts = $path.Split('.')
    $node = $obj
    for ($i = 0; $i -lt $parts.Length - 1; $i++) {
        $part = $parts[$i]
        if (-not ($node.PSObject.Properties.Name -contains $part)) { return $false }
        $node = $node.$part
    }
    $leaf = $parts[-1]
    if (-not ($node.PSObject.Properties.Name -contains $leaf)) { return $false }
    $node.$leaf = $value
    return $true
}

function Write-Json([string]$path, $obj) {
    $json = $obj | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText($path, $json + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
}

if ($Revert) {
    $restored = 0
    foreach ($backup in Get-ChildItem -Path $GameRoot -Recurse -File -Filter '*.p5x-backup') {
        $target = $backup.FullName -replace '\.p5x-backup$', ''
        if ($DryRun) {
            Write-Host "[dry] restaurar $target"
        } else {
            Copy-Item $backup.FullName $target -Force
            Remove-Item $backup.FullName -Force
            Write-Host "[+] restaurado $target" -ForegroundColor Green
        }
        $restored++
    }
    if ($restored -eq 0) { Write-Host '[*] No hay backups .p5x-backup para restaurar' -ForegroundColor Yellow }
    return
}

foreach ($edit in $Edits) {
    $files = Find-ConfigFiles $edit.File
    if ($files.Count -eq 0) {
        Write-Host "[-] no encontrado: $($edit.File)" -ForegroundColor DarkYellow
        continue
    }

    foreach ($file in $files) {
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $applied = @()
        $missed = @()
        foreach ($key in $edit.Changes.Keys) {
            if (Set-Node $json $key $edit.Changes[$key]) {
                $applied += $key
            } else {
                $missed += $key
            }
        }

        if ($applied.Count -eq 0) {
            Write-Host "[-] $($file.FullName): ninguna clave esperada (¿ya revertido?)" -ForegroundColor DarkYellow
            continue
        }

        Write-Host "[~] $($file.FullName)"
        Write-Host "    cambios: $($applied -join ', ')"
        if ($missed.Count -gt 0) {
            Write-Host "    omitidas (no existen): $($missed -join ', ')" -ForegroundColor DarkYellow
        }

        if (-not $DryRun) {
            $backup = "$($file.FullName).p5x-backup"
            if (-not (Test-Path $backup)) { Copy-Item $file.FullName $backup -Force }
            Write-Json $file.FullName $json
            Write-Host "    backup: $backup" -ForegroundColor DarkGray
        }
    }
}

Write-Host ''
Write-Host 'Listo. Para volver atras: -Revert' -ForegroundColor Cyan
Write-Host 'Recorda: esto es para una copia de trabajo offline, no para jugar en linea.' -ForegroundColor DarkGray
