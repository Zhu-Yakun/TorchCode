param([ValidateSet('Start', 'Stop')][string]$Action = 'Start')

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.local'
$stateFile = Join-Path $runtimeDir 'standalone-web.json'
$pythonExe = 'D:\Anaconda\python.exe'
$nodeExe = 'D:\nodejs\node.exe'
$nextEntry = Join-Path $projectRoot 'web\node_modules\next\dist\bin\next'

function Get-ManagedProcess($entry) {
    $process = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$entry.StartTicks) {
        return $process
    }
}

function Stop-ManagedProcesses($entries) {
    foreach ($entry in $entries) {
        $process = Get-ManagedProcess $entry
        if ($process) { Stop-Process -Id $process.Id -Force }
    }
}

function Save-State($entries) {
    ConvertTo-Json -InputObject @($entries) | Set-Content -LiteralPath $stateFile -Encoding UTF8
}

function Get-ProcessEntry($process) {
    return @{ Id = $process.Id; StartTicks = $process.StartTime.ToUniversalTime().Ticks }
}

function Test-Endpoint([string]$url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch { return $false }
}

$saved = @()
if (Test-Path -LiteralPath $stateFile) {
    $saved = @(Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json)
}

if ($Action -eq 'Stop') {
    Stop-ManagedProcesses $saved
    if (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile }
    Write-Host 'TorchCode stopped.'
    exit 0
}

if ($saved.Count -gt 0) {
    $alive = @($saved | Where-Object { Get-ManagedProcess $_ })
    if ($alive.Count -eq $saved.Count -and
        (Test-Endpoint 'http://127.0.0.1:8000/api/tasks') -and
        (Test-Endpoint 'http://127.0.0.1:3000')) {
        Write-Host 'TorchCode is running: http://127.0.0.1:3000'
        exit 0
    }
    Stop-ManagedProcesses $saved
    Start-Sleep -Seconds 1
}

foreach ($port in @(8000, 3000)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Close its service before starting TorchCode."
    }
}
foreach ($file in @($pythonExe, $nodeExe, $nextEntry)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Required file missing: $file" }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$managed = @()
try {
    $backend = Start-Process -FilePath $pythonExe -ArgumentList @('-B', '-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.err.log') -PassThru
    $managed += Get-ProcessEntry $backend
    Save-State $managed
    $frontend = Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $nextEntry + '"'), 'dev', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory (Join-Path $projectRoot 'web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.err.log') -PassThru
    $managed += Get-ProcessEntry $frontend
    Save-State $managed

    $ready = $false
    $deadline = (Get-Date).AddSeconds(90)
    do {
        if ($backend.HasExited -or $frontend.HasExited) { throw 'A service exited during startup.' }
        if ((Test-Endpoint 'http://127.0.0.1:8000/api/tasks') -and (Test-Endpoint 'http://127.0.0.1:3000')) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    if (-not $ready) { throw 'Startup timed out.' }

    # Next.js may serve requests from a child process; track it for clean shutdown.
    foreach ($connection in @(Get-NetTCPConnection -State Listen -LocalPort 3000,8000)) {
        if ($connection.OwningProcess -notin @($managed | ForEach-Object { $_.Id })) {
            $managed += Get-ProcessEntry (Get-Process -Id $connection.OwningProcess)
        }
    }
    Save-State $managed
    Write-Host 'TorchCode is ready: http://127.0.0.1:3000'
    Write-Host 'Use stop-web.cmd to stop both services.'
} catch {
    Stop-ManagedProcesses $managed
    throw "$_ Logs: $runtimeDir"
}
