$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$processFile = Join-Path $root "runtime\local-processes.json"
if (-not (Test-Path $processFile)) { Write-Host "No hay procesos SIC registrados."; exit 0 }
$processes = Get-Content $processFile -Raw | ConvertFrom-Json
foreach ($id in @($processes.api, $processes.web)) {
    $process = Get-Process -Id $id -ErrorAction SilentlyContinue
    if ($process) { Stop-Process -Id $id }
}
Remove-Item $processFile
Write-Host "Procesos SIC detenidos."
