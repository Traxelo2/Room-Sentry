Set-Location $PSScriptRoot
if (!(Test-Path "snapshots")) {
    New-Item -ItemType Directory -Path "snapshots" | Out-Null
}
Invoke-Item "snapshots"
