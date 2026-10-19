# Execute only parsed helper functions with process/network operations mocked.
# The production entry point is never run and no real server is started/stopped.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'scripts/local-server.ps1'), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw $parseErrors[0] }
foreach ($definition in $ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]}, $false)) {
    Invoke-Expression $definition.Extent.Text
}
$initialize = ${function:Initialize-Startup}
$start = ${function:Start-Server}
$invoke = ${function:Invoke-ServerAction}
$checks = 0
function Assert($Condition, $Message) {
    if (-not $Condition) { throw $Message }
    $script:checks++
}
function Expect-Failure($Operation, $Pattern) {
    try { & $Operation } catch {
        Assert ($_.Exception.Message -like $Pattern) "Unexpected failure: $($_.Exception.Message)"
        return
    }
    throw "Expected failure: $Pattern"
}

# Default wrappers remain demo/memory and live/memory; only new wrapper opts in.
$defaults = @{}
foreach ($parameter in $ast.ParamBlock.Parameters) { $defaults[$parameter.Name.VariablePath.UserPath] = $parameter.DefaultValue.Extent.Text }
Assert ($defaults['Mode'] -eq "'demo'" -and $defaults['Backend'] -eq "'memory'") 'Unsafe launcher defaults'
Assert ((Get-Content (Join-Path $root 'restart-live-pinecone.bat') -Raw) -match '-Action restart -Mode live -Backend pinecone') 'Pinecone wrapper missing explicit selection'
Assert ((Get-Content (Join-Path $root 'restart-live.bat') -Raw) -notmatch '-Backend pinecone') 'Memory wrapper changed'

# Invalid combinations fail before any process inspection or mutation.
$Mode = 'demo'; $Backend = 'pinecone'
Expect-Failure { & $initialize } '*requires live mode*'

$Python=(Get-Command powershell.exe).Source
$script:preflights=0
function Test-LocalConfiguration { $script:preflights++ }
$env:PYTHON_DOTENV_DISABLED='1'; $Mode='live'; $Backend='pinecone'
& $initialize
Assert ($env:EVIDENCE_ATLAS_MODE -eq 'live' -and $env:VECTOR_BACKEND -eq 'pinecone' -and -not $env:PYTHON_DOTENV_DISABLED) 'Live/Pinecone environment selection failed'
Assert ($preflights -eq 1 -and $env:LANGSMITH_TRACING -eq 'false') 'Live preflight/tracing policy failed'
$Backend='memory'; & $initialize
Assert ($env:VECTOR_BACKEND -eq 'memory' -and $preflights -eq 2) 'Live/memory override failed'
$Mode='demo'; & $initialize
Assert ($env:PYTHON_DOTENV_DISABLED -eq '1' -and $env:EVIDENCE_ATLAS_MODE -eq 'demo' -and $preflights -eq 2) 'Demo must skip .env and preflight'

# Failed preflight cannot stop the old server. Stop itself needs no credentials.
$script:calls = @()
function Initialize-Startup { $script:calls += 'validate'; throw 'missing configuration' }
function Stop-Server { $script:calls += 'stop' }
function Start-Server { $script:calls += 'start' }
$Action = 'restart'
Expect-Failure { & $invoke } '*missing configuration*'
Assert (($calls -join ',') -eq 'validate') 'Failed preflight stopped the server'
function Initialize-Startup { $script:calls += 'validate' }
$script:calls = @(); & $invoke
Assert (($calls -join ',') -eq 'validate,stop,start') 'Restart order changed'
$Action = 'stop'; $script:calls = @(); & $invoke
Assert (($calls -join ',') -eq 'stop') 'Stop must work without config'

# Mock all side effects of Start-Server, including the health endpoint.
function Read-State { return $null }
function Get-OwnedProcesses {
    $script:ownedReads++
    if ($script:ownedReads -gt 1) { return [pscustomobject]@{ProcessId=123} }
}
function Get-Listeners { if ($script:ownedReads -gt 1 -or $script:occupied) { return [pscustomobject]@{OwningProcess=123} } }
function Test-Path { return $true }
function New-Item { }
function Start-Process {
    param($FilePath,$ArgumentList,$WorkingDirectory,$WindowStyle,$RedirectStandardOutput,$RedirectStandardError,[switch]$PassThru)
    Assert ($WindowStyle -eq 'Hidden') 'Server must be hidden'
    $script:launchCount++
    return [pscustomobject]@{Id=123}
}
function Get-CimInstance { return [pscustomobject]@{ProcessId=123} }
function Test-ProjectProcess { return $true }
function Save-State { }
function Invoke-RestMethod { return $script:health }
$Python='mock-python'; $RuntimeDir='mock-runtime'; $ProjectRoot=$root
$Url='http://127.0.0.1:8000'; $ServerArguments='mock'; $StdoutFile='mock-out'; $StderrFile='mock-err'
$Mode='live'; $Backend='pinecone'; $script:occupied=$false
$script:health=@{mode='live'; vector_backend='pinecone'; configured=$true}
$script:ownedReads=0; $script:launchCount=0; $script:calls=@()
& $start
Assert ($launchCount -eq 1 -and $calls.Count -eq 0) 'Matching Pinecone health must pass'
$script:health.vector_backend='memory'; $script:ownedReads=0
Expect-Failure { & $start } '*does not match requested live/pinecone*'
Assert (($calls -join ',') -eq 'stop') 'Wrong backend must be stopped, never accepted'
$Backend='memory'; $script:ownedReads=0; $script:calls=@()
& $start
Assert ($calls.Count -eq 0) 'Existing live/memory behavior broke'
$script:health.configured=$false; $script:health.configuration_message='Missing settings'; $script:ownedReads=0
Expect-Failure { & $start } '*Configuration is incomplete*'
Assert (($calls -join ',') -eq 'stop') 'Unconfigured server left running'
$script:occupied=$true; $script:ownedReads=0; $script:calls=@(); $script:launchCount=0
Expect-Failure { & $start } '*Port 8000 is already in use*'
Assert ($calls.Count -eq 0 -and $launchCount -eq 0) 'Unmanaged listener was changed'
Write-Host "Passed $checks launcher assertions; no server or provider was contacted."
