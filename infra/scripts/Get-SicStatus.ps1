$targets = @(
    @{ Name = "Web"; Url = "http://127.0.0.1:3000" },
    @{ Name = "API"; Url = "http://127.0.0.1:8001/health/ready" },
    @{ Name = "BFF"; Url = "http://127.0.0.1:3000/api/health" }
)
foreach ($target in $targets) {
    try {
        $response = Invoke-WebRequest $target.Url -UseBasicParsing -TimeoutSec 3
        [PSCustomObject]@{ Component = $target.Name; Status = "Online"; Http = $response.StatusCode }
    } catch {
        [PSCustomObject]@{ Component = $target.Name; Status = "Offline"; Http = $null }
    }
}
