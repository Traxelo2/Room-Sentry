$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "RoomSentry Local.lnk"
$target = Join-Path $PSScriptRoot "START_ROOM_SENTRY.bat"
$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,101"
$shortcut.Save()
Write-Host "Startup shortcut created: $shortcutPath" -ForegroundColor Green
