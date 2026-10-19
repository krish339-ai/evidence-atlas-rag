# Windows PowerShell 5.1 helper for the root batch files. No administrator rights needed.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('start', 'stop', 'restart')][string]$Action,
    [ValidateSet('demo', 'live')][string]$Mode = 'demo',
    [ValidateSet('memory', 'pinecone')][string]$Backend = 'memory'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$RuntimeDir = Join-Path $ProjectRoot 'tmp\local-server'
$StateFile = Join-Path $RuntimeDir 'server.json'
$StdoutFile = Join-Path $RuntimeDir 'stdout.log'
$StderrFile = Join-Path $RuntimeDir 'stderr.log'
$Url = 'http://127.0.0.1:8000'
$ServerArguments = '-m uvicorn papertrail.server:app --app-dir "' + $ProjectRoot + '" --host 127.0.0.1 --port 8000'

function Test-ProjectProcess($Process) {
    return $null -ne $Process -and $Process.Name -match '^python(w)?\.exe$' -and
        $Process.CommandLine -and $Process.CommandLine.TrimEnd().EndsWith($ServerArguments, [StringComparison]::OrdinalIgnoreCase)
}

function Get-Identity($Process) {
    return [pscustomobject]@{
        id = [int]$Process.ProcessId
        created = $Process.CreationDate.ToUniversalTime().ToString('o')
        command = $Process.CommandLine
    }
}

function Read-State {
    if (-not (Test-Path -LiteralPath $StateFile)) { return $null }
    $state = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    if ($state.root -ne $ProjectRoot -or -not $state.processes) {
        throw "Invalid server state: $StateFile. No processes were stopped."
    }
    return $state
}

function Save-State($Processes) {
    $state = @{root = $ProjectRoot; processes = @($Processes | ForEach-Object { Get-Identity $_ })}
    $temporary = Join-Path $RuntimeDir 'server.json.new'
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $StateFile -Force
}

function Get-OwnedProcesses($State) {
    if ($null -eq $State) { return }
    $all = @(Get-CimInstance Win32_Process)
    $owned = @{}
    foreach ($record in $State.processes) {
        $process = $all | Where-Object { $_.ProcessId -eq $record.id } | Select-Object -First 1
        if ((Test-ProjectProcess $process) -and
            $process.CreationDate.ToUniversalTime().ToString('o') -eq $record.created -and
            $process.CommandLine -eq $record.command) {
            $owned[[int]$process.ProcessId] = $process
        }
    }
    # A Windows venv launcher may spawn a second Python process. Track that child
    # too, but only when its parent is owned and its full server arguments match.
    do {
        $added = $false
        foreach ($process in $all) {
            if (-not $owned.ContainsKey([int]$process.ProcessId) -and
                $owned.ContainsKey([int]$process.ParentProcessId) -and (Test-ProjectProcess $process) -and
                $process.CreationDate -ge $owned[[int]$process.ParentProcessId].CreationDate) {
                $owned[[int]$process.ProcessId] = $process
                $added = $true
            }
        }
    } while ($added)
    return $owned.Values
}

function Get-Listeners {
    return @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
}

function Test-LocalConfiguration {
    Push-Location -LiteralPath $ProjectRoot
    try {
        & $Python -m scripts.check_local_config
        if ($LASTEXITCODE -ne 0) {
            throw 'Startup configuration check failed. No server was stopped. Fix the configuration above and retry.'
        }
    } finally { Pop-Location }
}

function Initialize-Startup {
    if ($Backend -eq 'pinecone' -and $Mode -ne 'live') {
        throw 'Pinecone requires live mode. Use restart-live-pinecone.bat.'
    }
    if (-not (Test-Path -LiteralPath $Python)) {
        throw 'Python environment missing. Follow README.md > Fresh setup, then retry.'
    }
    # Overrides belong only to this helper and its children, never the saved .env.
    if ($Mode -eq 'live') {
        Remove-Item Env:PYTHON_DOTENV_DISABLED -ErrorAction SilentlyContinue
    } else {
        $env:PYTHON_DOTENV_DISABLED = '1'
    }
    $env:EVIDENCE_ATLAS_MODE = $Mode
    $env:VECTOR_BACKEND = $Backend
    $env:LANGCHAIN_TRACING_V2 = 'false'
    $env:LANGSMITH_TRACING = 'false'
    if ($Mode -eq 'live') {
        # Local validation only, before stopping a working server. No provider calls.
        Test-LocalConfiguration
    }
}

function Stop-Server {
    $owned = @(Get-OwnedProcesses (Read-State))
    if (-not $owned.Count) {
        if (Test-Path -LiteralPath $StateFile) { Remove-Item -LiteralPath $StateFile }
        Write-Host 'No batch-managed server is running for this project.'
        if (@(Get-Listeners).Count) {
            Write-Host 'Port 8000 is in use by an unmanaged process; it was left running.'
        }
        return
    }
    # Stop children first. Recheck identity immediately before each stop so a
    # stale PID file cannot stop a different process after a PID has been reused.
    foreach ($process in ($owned | Sort-Object CreationDate -Descending)) {
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.ProcessId)"
        if ((Test-ProjectProcess $current) -and $current.CreationDate -eq $process.CreationDate -and
            $current.CommandLine -eq $process.CommandLine) {
            $handle = Get-Process -Id $current.ProcessId -ErrorAction SilentlyContinue
            if ($handle) {
                Stop-Process -InputObject $handle -Force
                if (-not $handle.WaitForExit(10000)) { throw 'The server did not stop within 10 seconds.' }
            }
        }
    }
    Remove-Item -LiteralPath $StateFile -ErrorAction SilentlyContinue
    Write-Host 'Evidence Atlas RAG stopped. Local collections have been cleared; any remote Pinecone vectors remain.'
}

function Start-Server {
    $owned = @(Get-OwnedProcesses (Read-State))
    if ($owned.Count) {
        Write-Host "A batch-managed server is already running. Open $Url"
        Write-Host 'Use restart.bat for demo/memory, restart-live.bat for live/memory, or restart-live-pinecone.bat for live/Pinecone.'
        return
    }
    if (@(Get-Listeners).Count) {
        throw 'Port 8000 is already in use. Stop the app in its original terminal (Ctrl+C), or stop the other service, then try again. No process was stopped.'
    }
    if (-not (Test-Path -LiteralPath $Python)) {
        throw 'Python environment missing. Follow README.md > Fresh setup, then run start.bat again.'
    }
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
    Write-Host "Starting Evidence Atlas RAG in $Mode/$Backend mode..."
    if ($Mode -eq 'live') {
        Write-Host 'Live document indexing and questions use your configured providers and may incur API charges.'
    }
    $launched = Start-Process -FilePath $Python -ArgumentList $ServerArguments -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden -RedirectStandardOutput $StdoutFile -RedirectStandardError $StderrFile -PassThru
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($launched.Id)"
    if (-not (Test-ProjectProcess $process)) { throw "Server exited before startup. See $StderrFile" }
    Save-State @($process)
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline) {
        $owned = @(Get-OwnedProcesses (Read-State))
        if (-not $owned.Count) {
            Remove-Item -LiteralPath $StateFile -ErrorAction SilentlyContinue
            throw "Server exited during startup. Install dependencies using README.md > Fresh setup. Details: $StderrFile"
        }
        Save-State $owned
        $listeners = @(Get-Listeners | Where-Object { $_.OwningProcess -in $owned.ProcessId })
        if ($listeners.Count) {
            $status = $null
            try {
                $status = Invoke-RestMethod -Uri "$Url/api/status" -TimeoutSec 2
            } catch { } # Retry while the server finishes initializing.
            if ($status -and ($status.mode -ne $Mode -or $status.vector_backend -ne $Backend)) {
                Stop-Server
                throw "Server mode/backend does not match requested $Mode/$Backend. The managed server was stopped; no fallback was used."
            }
            if ($status -and $status.mode -eq $Mode -and $status.vector_backend -eq $Backend) {
                if (-not $status.configured) {
                    Stop-Server
                    throw "Configuration is incomplete: $($status.configuration_message)"
                }
                Write-Host "Ready: $Url ($Mode/$Backend)"
                if ($Mode -eq 'live') {
                    Write-Host 'Live mode is configured locally; provider access, index compatibility and billing have not been tested.'
                    Write-Host "Refresh the browser, confirm LIVE MODE and $Backend, and reload your documents to build the semantic index."
                    if ($Backend -eq 'pinecone') {
                        Write-Host 'Restart clears the local collection catalog even though remote vectors persist. Reindexing creates a new namespace.'
                    }
                } else {
                    Write-Host 'Click Explore CMS guidance to load the sample. No API key is needed.'
                }
                Write-Host "Logs: $RuntimeDir"
                Write-Host 'You can close this launcher window. Use stop.bat to stop the server.'
                return
            }
        }
        Start-Sleep -Milliseconds 300
    }
    Stop-Server
    throw "Startup timed out after 60 seconds. The managed server was stopped. See $StderrFile"
}

function Invoke-ServerAction {
    if ($Action -ne 'stop') { Initialize-Startup }
    switch ($Action) {
        'start' { Start-Server }
        'stop' { Stop-Server }
        'restart' { Stop-Server; Start-Server }
    }
}

# Serialize double-clicks and concurrent start/stop calls for this checkout.
$hash = [Security.Cryptography.SHA256]::Create()
$key = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($ProjectRoot.ToLowerInvariant()))).Replace('-', '')
$hash.Dispose()
$mutex = New-Object Threading.Mutex($false, "Local\EvidenceAtlas-$key")
$locked = $false
$result = 0
try {
    try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another start/stop operation is in progress. Wait for it to finish, then retry.' }
    Invoke-ServerAction
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $result = 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
exit $result
