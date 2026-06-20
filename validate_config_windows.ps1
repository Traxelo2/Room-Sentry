Set-Location -Path $PSScriptRoot
if (Test-Path ".\.venv\Scripts\python.exe") {
  .\.venv\Scripts\python.exe .\validate_config.py
} elseif (Test-Path ".\venv\Scripts\python.exe") {
  .\venv\Scripts\python.exe .\validate_config.py
} else {
  python .\validate_config.py
}
