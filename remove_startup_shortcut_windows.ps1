$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "RoomSentry Local.lnk"
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath
    Write-Host "Startup shortcut removed." -ForegroundColor Green
} else {
    Write-Host "No RoomSentry startup shortcut found."
}
