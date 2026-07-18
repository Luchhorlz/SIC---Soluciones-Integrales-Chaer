$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$api = Join-Path $root "apps\api"
$web = Join-Path $root "apps\web"
$runtime = Join-Path $root "runtime"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

if (-not (Test-Path (Join-Path $api ".venv\Scripts\python.exe"))) {
    py -3.11 -m venv (Join-Path $api ".venv")
    & (Join-Path $api ".venv\Scripts\python.exe") -m pip install -r (Join-Path $api "requirements.txt")
}

$apiProcess = Start-Process -FilePath (Join-Path $api ".venv\Scripts\python.exe") -ArgumentList "-m uvicorn sic_api.main:app --app-dir src --host 127.0.0.1 --port 8001" -WorkingDirectory $api -PassThru -WindowStyle Hidden
$webProcess = Start-Process -FilePath (Get-Command corepack.cmd).Source -ArgumentList "pnpm dev --hostname 127.0.0.1 --port 3000" -WorkingDirectory $web -PassThru -WindowStyle Hidden

@{ api = $apiProcess.Id; web = $webProcess.Id } | ConvertTo-Json | Set-Content (Join-Path $runtime "local-processes.json")
Write-Host "SIC disponible en http://127.0.0.1:3000"
