param(
    [string]$RepoUrl = ""
)

if (!(Test-Path "README.md") -or !(Test-Path "room_sentry.py")) {
    Write-Error "Run this from the RoomSentry repo root."
    exit 1
}

git init
git branch -M main
git add .
git commit -m "Initial open-source RoomSentry release"

if ($RepoUrl -ne "") {
    git remote remove origin 2>$null
    git remote add origin $RepoUrl
    git push -u origin main
} else {
    Write-Host "Local git repo is ready. To push:"
    Write-Host "git remote add origin https://github.com/YOUR_USERNAME/roomsentry.git"
    Write-Host "git push -u origin main"
}
