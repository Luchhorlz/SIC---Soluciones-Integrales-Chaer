$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$processFile = Join-Path $root "runtime\local-processes.json"
if (-not (Test-Path $processFile)) { Write-Host "No hay procesos SIC registrados."; exit 0 }
$processes = Get-Content $processFile -Raw | ConvertFrom-Json
$webPath = Join-Path $root "apps\web"
$apiExecutable = Join-Path $root "apps\api\.venv\Scripts\python.exe"

function Stop-SicOwnedTree([int]$processId, [string]$component) {
    if (-not $processId) { return }
    $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (-not $rootProcess) { return }
    $owned = if ($component -eq "web") {
        $rootProcess.Name -eq "node.exe" -and $rootProcess.CommandLine -like "*$webPath*" -and $rootProcess.CommandLine -like "*--port 3000*"
    } else {
        $rootProcess.ExecutablePath -eq $apiExecutable -and $rootProcess.CommandLine -like "*uvicorn sic_api.main:app*" -and $rootProcess.CommandLine -like "*--port 8001*"
    }
    if (-not $owned) {
        Write-Warning "Se omitió un PID reutilizado que ya no pertenece a SIC: $processId"
        return
    }

    $tree = @($processId)
    for ($index = 0; $index -lt $tree.Count; $index++) {
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($tree[$index])" -ErrorAction SilentlyContinue
        $tree += @($children | ForEach-Object ProcessId)
    }
    [array]::Reverse($tree)
    foreach ($ownedProcessId in $tree) { Stop-Process -Id $ownedProcessId -ErrorAction SilentlyContinue }
}

Stop-SicOwnedTree $processes.webRoot "web"
Stop-SicOwnedTree $processes.apiRoot "api"
Remove-Item $processFile
Write-Host "Procesos SIC detenidos."
