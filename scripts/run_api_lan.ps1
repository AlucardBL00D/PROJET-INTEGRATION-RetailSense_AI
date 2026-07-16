param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ip = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '169.254.*' -and
        $_.IPAddress -ne '127.0.0.1' -and
        $_.InterfaceAlias -notmatch 'vEthernet|WSL|Hyper-V|VirtualBox|VMware|Loopback|Teredo'
    } |
    Sort-Object SkipAsSource, InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
)

if (-not $ip) {
    Write-Error 'No LAN IPv4 address found. Check your network adapter.'
}

$modelsDir = Join-Path $root 'models'
$env:RETAILSENSE_MODELS_DIR = $modelsDir
$env:RETAILSENSE_CORS_ORIGINS = '*'

Write-Host "LAN IP detected: $ip" -ForegroundColor Green
Write-Host "API URL for phone: http://$ip`:$Port" -ForegroundColor Green
Write-Host 'Starting FastAPI on 0.0.0.0 so phone can reach it...' -ForegroundColor Cyan

uvicorn api.main:app --reload --reload-dir api --host 0.0.0.0 --port $Port
