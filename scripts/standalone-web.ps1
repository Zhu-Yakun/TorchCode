param([ValidateSet('Start', 'Stop')][string]$Action = 'Start')

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.local'
$stateFile = Join-Path $runtimeDir 'standalone-web.json'
$pythonExe = 'D:\Anaconda\python.exe'
$nodeExe = 'D:\nodejs\node.exe'
$nextPackageDir = Join-Path $projectRoot 'web\node_modules\next'
$nextEntry = Join-Path $nextPackageDir 'dist\bin\next'

function Get-ManagedProcess($entry) {
    $processId = 0
    $startTicks = 0L
    if (-not [int]::TryParse([string]$entry.Id, [ref]$processId) -or
        -not [long]::TryParse([string]$entry.StartTicks, [ref]$startTicks)) { return }
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $startTicks -and
        $process.Path -in @($pythonExe, $nodeExe)) { return $process }
}

function Get-ProjectProcesses {
    # Explicit project paths allow recovery even when the state file is missing.
    $candidates = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'node.exe'"
    foreach ($candidate in $candidates) {
        $command = [string]$candidate.CommandLine
        $isBackend = $candidate.ExecutablePath -eq $pythonExe -and
            $command -match '\buvicorn\s+api\.main:app\b' -and
            $command -match ('--app-dir\s+"?' + [regex]::Escape($projectRoot) + '(?:"|\s|$)')
        $isFrontend = $candidate.ExecutablePath -eq $nodeExe -and
            $command -match [regex]::Escape($nextPackageDir + '\')
        if ($isBackend -or $isFrontend) {
            Get-Process -Id $candidate.ProcessId -ErrorAction SilentlyContinue
        }
    }
}

function Get-OwnedProcesses($entries) {
    $byId = @{}
    foreach ($entry in $entries) {
        $process = Get-ManagedProcess $entry
        if ($process) { $byId[$process.Id] = $process }
    }
    foreach ($process in @(Get-ProjectProcesses)) { $byId[$process.Id] = $process }
    @($byId.Values)
}

function Get-Listeners {
    @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in @(8000, 3000) })
}

function Save-State($processes) {
    $entries = @($processes | ForEach-Object {
        # Strings preserve all timestamp digits across JSON implementations.
        @{ Id = $_.Id; StartTicks = [string]$_.StartTime.ToUniversalTime().Ticks }
    })
    $temporaryState = $stateFile + '.tmp'
    ConvertTo-Json -InputObject $entries | Set-Content -LiteralPath $temporaryState -Encoding UTF8
    Move-Item -LiteralPath $temporaryState -Destination $stateFile -Force
}

function Stop-OwnedProcesses($processes) {
    $stopping = @($processes)
    foreach ($process in $stopping) {
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
            $null = $process.Handle
            Stop-Process -InputObject $process -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($process in $stopping) {
        if (-not $process.HasExited -and -not $process.WaitForExit(10000)) { throw "Process $($process.Id) did not stop." }
    }
    # A Next.js child may have been created while the launchers were stopping.
    foreach ($process in @(Get-ProjectProcesses)) {
        $null = $process.Handle
        Stop-Process -InputObject $process -Force -ErrorAction SilentlyContinue
        if (-not $process.HasExited -and -not $process.WaitForExit(10000)) { throw "Process $($process.Id) did not stop." }
        $stopping += $process
    }
    $deadline = (Get-Date).AddSeconds(10)
    while (@(Get-Listeners | Where-Object { $_.OwningProcess -in @($stopping.Id) }).Count -gt 0) {
        if ((Get-Date) -gt $deadline) { throw 'TorchCode ports have not been released yet. Try again shortly.' }
        Start-Sleep -Milliseconds 200
    }
}

function Test-Endpoint([string]$url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch { return $false }
}

# Serialize Start and Stop, including separate double-clicks of the .cmd files.
$hasher = [System.Security.Cryptography.SHA256]::Create()
$projectHash = [BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($projectRoot.ToLowerInvariant()))).Replace('-', '')
$hasher.Dispose()
$mutex = New-Object System.Threading.Mutex($false, ('Local\TorchCode-' + $projectHash))
$locked = $false
try {
    try { $locked = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) {
        Write-Host 'TorchCode startup/shutdown is already in progress. Please wait for it to finish.'
        exit 0
    }

    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    $saved = @()
    if (Test-Path -LiteralPath $stateFile) {
        try {
            # PowerShell 5.1 requires explicit enumeration of the JSON array.
            $saved = @(Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json | ForEach-Object { $_ })
        } catch { Write-Warning 'The old process record is unreadable; checking project processes instead.' }
    }
    $owned = @(Get-OwnedProcesses $saved)

    if ($Action -eq 'Stop') {
        Stop-OwnedProcesses $owned
        if (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile }
        Write-Host 'TorchCode stopped.'
        exit 0
    }

    $listeners = @(Get-Listeners)
    $ownedIds = @($owned.Id)
    $foreign = @($listeners | Where-Object { $_.OwningProcess -notin $ownedIds })
    if ($foreign.Count -gt 0) {
        $conflicts = @($foreign | ForEach-Object {
            $occupant = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
            "port $($_.LocalPort): $($occupant.ProcessName) (PID $($_.OwningProcess))"
        }) -join '; '
        throw "Another service is using a required port: $conflicts. No unrelated process was stopped."
    }
    if (@($listeners | Where-Object LocalPort -eq 8000).Count -gt 0 -and
        @($listeners | Where-Object LocalPort -eq 3000).Count -gt 0 -and
        (Test-Endpoint 'http://127.0.0.1:8000/api/tasks') -and
        (Test-Endpoint 'http://127.0.0.1:3000')) {
        Save-State $owned
        Write-Host 'TorchCode is already running: http://127.0.0.1:3000'
        exit 0
    }

    Stop-OwnedProcesses $owned
    if (@(Get-Listeners).Count -gt 0) { throw 'A required port was occupied during startup. Please try again.' }
    foreach ($file in @($pythonExe, $nodeExe, $nextEntry)) {
        if (-not (Test-Path -LiteralPath $file)) { throw "Required file missing: $file" }
    }

    $managed = @()
    try {
        $backend = Start-Process -FilePath $pythonExe -ArgumentList @('-B', '-m', 'uvicorn', 'api.main:app', '--app-dir', ('"' + $projectRoot + '"'), '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.err.log') -PassThru
        $managed += $backend
        Save-State $managed
        $frontend = Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $nextEntry + '"'), 'dev', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory (Join-Path $projectRoot 'web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.err.log') -PassThru
        $managed += $frontend
        Save-State $managed

        $ready = $false
        $deadline = (Get-Date).AddSeconds(90)
        do {
            $backend.Refresh()
            $frontend.Refresh()
            if ($backend.HasExited -or $frontend.HasExited) { throw 'A service exited during startup.' }
            if ((Test-Endpoint 'http://127.0.0.1:8000/api/tasks') -and (Test-Endpoint 'http://127.0.0.1:3000')) {
                $ready = $true
                break
            }
            Start-Sleep -Milliseconds 500
        } while ((Get-Date) -lt $deadline)
        if (-not $ready) { throw 'Startup timed out.' }

        Save-State @(Get-OwnedProcesses @())
        Write-Host 'TorchCode is ready: http://127.0.0.1:3000'
        Write-Host 'Use stop-web.cmd to stop both services.'
    } catch {
        Stop-OwnedProcesses $managed
        throw "$_ Logs: $runtimeDir"
    }
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
