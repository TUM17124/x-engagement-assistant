$ErrorActionPreference = 'Stop'
$env:PATH="$env:USERPROFILE\.cargo\bin;$env:PATH"
.venv\Scripts\python.exe -B scripts/build_signed.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
