Set-Location $PSScriptRoot
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}
Invoke-Item "logs"
