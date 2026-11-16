<#
.SYNOPSIS
    Redirige (o revierte) el host de login de P5X hacia el servidor local.

.DESCRIPTION
    El cliente resuelve `eulogin.p5xjpupd.com` para autenticarse. Durante las pruebas
    offline ese nombre debe apuntar a 127.0.0.1. El script es idempotente, hace un
    backup del archivo hosts la primera vez y exige permisos de administrador.

.PARAMETER Action
    Add (por defecto) | Remove | Status

.PARAMETER Domain
    Dominios a redirigir. Por defecto eulogin.p5xjpupd.com.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\hosts_local.ps1 -Action Add
    powershell -ExecutionPolicy Bypass -File tools\hosts_local.ps1 -Action Status
    powershell -ExecutionPolicy Bypass -File tools\hosts_local.ps1 -Action Remove
#>
[CmdletBinding()]
param(
    [ValidateSet('Add', 'Remove', 'Status')]
    [string]$Action = 'Add',

    [string[]]$Domain = @('eulogin.p5xjpupd.com'),

    [string]$HostsPath = "$env:SystemRoot\System32\drivers\etc\hosts",

    [switch]$NoFlushDns
)

$ErrorActionPreference = 'Stop'
$Redirect = '127.0.0.1'
$Pattern = ($Domain | ForEach-Object { [regex]::Escape($_) }) -join '|'
$ExactPattern = "^\s*\S+\s+(?:$Pattern)\s*$"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Path $HostsPath)) {
    throw "No se encontro el archivo hosts en $HostsPath"
}

$lines = [System.Collections.ArrayList]@(Get-Content -Path $HostsPath -ErrorAction Stop)

switch ($Action) {
    'Status' {
        $found = @($lines | Where-Object { $_ -match $Pattern })
        if ($found.Count -gt 0) {
            Write-Host 'Entradas activas:' -ForegroundColor Cyan
            $found | ForEach-Object { Write-Host "  $_" }
        } else {
            Write-Host "Sin redirecciones activas para: $($Domain -join ', ')" -ForegroundColor Yellow
        }
    }

    'Add' {
        if (-not (Test-Admin)) { throw 'Requiere una consola como Administrador.' }

        $backup = "$HostsPath.p5x-backup"
        if (-not (Test-Path $backup)) {
            Copy-Item $HostsPath $backup -Force
            Write-Host "[i] Backup creado: $backup" -ForegroundColor DarkGray
        }

        $added = @()
        foreach ($name in $Domain) {
            $already = @($lines | Where-Object { $_ -match $ExactPattern -and $_ -match [regex]::Escape($name) })
            if ($already.Count -gt 0) {
                Write-Host "[=] $name ya esta redirigido" -ForegroundColor DarkGray
            } else {
                [void]$lines.Add("$Redirect`t$name")
                $added += $name
            }
        }

        if ($added.Count -gt 0) {
            $text = ($lines -join "`r`n") + "`r`n"
            [IO.File]::WriteAllText($HostsPath, $text, (New-Object System.Text.ASCIIEncoding))
            $added | ForEach-Object { Write-Host "[+] $Redirect -> $_" -ForegroundColor Green }
        }

        if (-not $NoFlushDns) { ipconfig /flushdns | Out-Null }
    }

    'Remove' {
        if (-not (Test-Admin)) { throw 'Requiere una consola como Administrador.' }

        $kept = @($lines | Where-Object { $_ -notmatch $Pattern })
        if ($kept.Count -eq $lines.Count) {
            Write-Host '[*] No habia entradas que quitar' -ForegroundColor Yellow
        } else {
            $text = ($kept -join "`r`n") + "`r`n"
            [IO.File]::WriteAllText($HostsPath, $text, (New-Object System.Text.ASCIIEncoding))
            Write-Host "[+] Redirecciones eliminadas: $($Domain -join ', ')" -ForegroundColor Green
        }

        if (-not $NoFlushDns) { ipconfig /flushdns | Out-Null }
    }
}
