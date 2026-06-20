$ErrorActionPreference = "Stop"
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "RoomSentry Tray.lnk"
$target = Join-Path $PSScriptRoot "START_ROOM_SENTRY_TRAY.bat"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "Start RoomSentry tray controller"
$shortcut.Save()
Write-Host "Created startup shortcut: $shortcutPath"
