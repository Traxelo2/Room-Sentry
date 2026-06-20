$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "RoomSentry Tray.lnk"
if (Test-Path $shortcutPath) {
  Remove-Item $shortcutPath -Force
  Write-Host "Removed startup shortcut: $shortcutPath"
} else {
  Write-Host "No RoomSentry Tray startup shortcut found."
}
