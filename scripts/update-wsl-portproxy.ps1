[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [int]$ListenPort = 8080,
    [int]$ConnectPort = 8080,
    [string]$ListenAddress = "0.0.0.0",
    [string[]]$RemoteAddress = @("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)

$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ejecuta PowerShell como Administrador para actualizar portproxy y el firewall."
}

$wslAddresses = @(wsl.exe --distribution $Distro hostname -I 2>$null) -join " "
$wslAddress = ($wslAddresses -split "\s+") | Where-Object { $_ -match "^\d{1,3}(\.\d{1,3}){3}$" } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($wslAddress)) {
    throw "No se pudo obtener la IP de $Distro. Comprueba que WSL esté iniciado."
}

Set-Service -Name iphlpsvc -StartupType Automatic
Start-Service -Name iphlpsvc

netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$ListenPort | Out-Null
netsh interface portproxy add v4tov4 listenaddress=$ListenAddress listenport=$ListenPort connectaddress=$wslAddress connectport=$ConnectPort | Out-Null

$ruleName = "Reto4V WSL TCP $ListenPort"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $ListenPort -Profile Domain,Private -RemoteAddress $RemoteAddress | Out-Null
}

Write-Host "Programmy4V LAN: $ListenAddress`:$ListenPort -> WSL $wslAddress`:$ConnectPort"
Write-Host "Comprueba: netsh interface portproxy show v4tov4"
