$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$api = Join-Path $root "apps\api"
$web = Join-Path $root "apps\web"
$runtime = Join-Path $root "runtime"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

# La previsualización local incluye autenticación y catálogo demo sin guardar
# secretos reales. Este iniciador fuerza un entorno de desarrollo, nunca producción.
$env:APP_ENV = "development"
$env:DEMO_MODE = "true"
if (-not $env:API_INTERNAL_URL) { $env:API_INTERNAL_URL = "http://127.0.0.1:8001" }
if (-not $env:APP_URL) { $env:APP_URL = "http://127.0.0.1:3000" }
if (-not $env:AUTH_URL) { $env:AUTH_URL = $env:APP_URL }
if (-not $env:AUTH_SECRET) { $env:AUTH_SECRET = "sic-local-demo-auth-secret-never-use-in-production" }
if (-not $env:INTERNAL_API_JWT_SECRET) { $env:INTERNAL_API_JWT_SECRET = "sic-local-demo-api-secret-never-use-in-production" }
if (-not $env:AUTH_TRUST_HOST) { $env:AUTH_TRUST_HOST = "true" }

if (-not (Test-Path (Join-Path $api ".venv\Scripts\python.exe"))) {
    py -3.11 -m venv (Join-Path $api ".venv")
    & (Join-Path $api ".venv\Scripts\python.exe") -m pip install -r (Join-Path $api "requirements.txt")
}

$apiProcess = Start-Process -FilePath (Join-Path $api ".venv\Scripts\python.exe") -ArgumentList "-m uvicorn sic_api.main:app --app-dir src --host 127.0.0.1 --port 8001" -WorkingDirectory $api -PassThru -WindowStyle Hidden
$nextBin = Join-Path $web "node_modules\next\dist\bin\next"
if (-not (Test-Path $nextBin)) { throw "Faltan las dependencias web. Ejecutá corepack pnpm install dentro de apps\web." }
$webProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList $nextBin, "dev", "--hostname", "127.0.0.1", "--port", "3000" -WorkingDirectory $web -PassThru -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(20)
do {
    $apiListener = Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -First 1
    $webListener = Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($apiListener -and $webListener) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

if (-not $apiListener -or -not $webListener) {
    throw "SIC no pudo abrir los puertos locales 8001 y 3000 dentro del tiempo esperado."
}

@{
    apiRoot = $apiProcess.Id
    webRoot = $webProcess.Id
    api = $apiListener.OwningProcess
    web = $webListener.OwningProcess
} | ConvertTo-Json | Set-Content (Join-Path $runtime "local-processes.json")
Write-Host "SIC disponible en http://127.0.0.1:3000"
