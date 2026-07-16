param(
    [int]$Port = 8000,
    [string]$DeviceId = ''
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root 'app_flutter'

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

$apiBaseUrl = "http://$ip`:$Port"
Write-Host "Using API_BASE_URL=$apiBaseUrl" -ForegroundColor Green
Write-Host 'Make sure API is already running: scripts/run_api_lan.ps1' -ForegroundColor Yellow

Set-Location $appDir
flutter pub get

if ($DeviceId) {
    flutter run -d $DeviceId --dart-define "API_BASE_URL=$apiBaseUrl"
} else {
    flutter run --dart-define "API_BASE_URL=$apiBaseUrl"
}
