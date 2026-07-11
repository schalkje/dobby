#!/usr/bin/env pwsh
#
# dobby.ps1 — convenience wrapper around the scenario-skill generator.
#
# A project targets one scenario (ado | github | combined); dobby assembles a
# flat, specialized skill set for it. This wrapper is a thin, discoverable entry
# point over scripts/build-skills.py and scripts/check-skill-sync.py so you don't
# have to remember the python invocations.
#
#   .\dobby.ps1 init [<target>] [<scenario>]   Scaffold a scenario into a project
#                                              (prompts when args are omitted).
#   .\dobby.ps1 dev                            Regenerate dobby's OWN host copies (github scenario).
#   .\dobby.ps1 build [--out <dir>]            Emit all three scenarios to build/<scenario>/.
#   .\dobby.ps1 check                          Verify committed host copies are in sync.
#   .\dobby.ps1 help                           Show this help.
#
# dobby does NOT bundle the OpenSpec workflow skills — install them per-project with
# the OpenSpec CLI. `init` offers to run `openspec init` for you (and always prints
# the manual command). dobby's init is non-destructive: it only manages dobby's own
# skills and leaves openspec-* / your project's skills untouched.
#
# init switches (skip the interactive prompts — useful for scripting):
#   -Config      Write a .dobby/config.json skeleton into the target.
#   -NoConfig    Do not write a config skeleton.
#   -Force       Overwrite an existing .dobby/config.json (with -Config).
#   -OpenSpec    Run `openspec init --tools "claude,github-copilot"` in the target.
#   -NoOpenSpec  Skip it (just print the manual command).
#
# Examples:
#   .\dobby.ps1 init                                   Interactive: prompts for everything.
#   .\dobby.ps1 init ..\my-app github -Config -OpenSpec  Scaffold + config + openspec, no prompts.
#
# Works from any working directory — paths resolve against the script's own location.
# Requires Python 3 (standard library only; no packages).

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = 'help',

    # init only: write / skip the .dobby/config.json skeleton without prompting.
    [switch]$Config,
    [switch]$NoConfig,
    # init only: overwrite an existing .dobby/config.json when writing the skeleton.
    [switch]$Force,
    # init only: run / skip `openspec init` in the target without prompting.
    [switch]$OpenSpec,
    [switch]$NoOpenSpec,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest = @()
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$Scenarios = @('ado', 'github', 'combined')

function Resolve-Python {
    foreach ($name in 'python', 'python3', 'py') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($cmd) {
            $pre = if ($name -eq 'py') { @('-3') } else { @() }
            return [pscustomobject]@{ Exe = $cmd.Source; Pre = $pre }
        }
    }
    throw "Python 3 was not found on PATH. Install Python 3 (stdlib only — no packages needed)."
}

$Py = Resolve-Python
$PyExe = $Py.Exe
$PyPre = $Py.Pre

$BuildSkills = Join-Path $RepoRoot 'scripts/build-skills.py'
$CheckSync = Join-Path $RepoRoot 'scripts/check-skill-sync.py'

function Show-Help {
    Get-Content -Path $PSCommandPath -TotalCount 45 |
        Where-Object { $_ -match '^#' -and $_ -notmatch '^#!' } |
        ForEach-Object { $_ -replace '^#\s?', '' }
}

# Read-Host that degrades to $Default in a non-interactive session instead of throwing.
function Read-Prompt {
    param([string]$Message, [string]$Default = $null)
    try {
        $v = Read-Host $Message
        if ([string]::IsNullOrWhiteSpace($v)) { return $Default }
        return $v.Trim()
    }
    catch { return $Default }
}

function Read-Scenario {
    Write-Host ""
    Write-Host "Which scenario is this project?" -ForegroundColor Cyan
    Write-Host "  [1] ado       Azure DevOps repo + boards + PRs"
    Write-Host "  [2] github    GitHub repo + issues + PRs"
    Write-Host "  [3] combined  GitHub repo/PRs + Azure DevOps boards"
    while ($true) {
        $sel = Read-Prompt "Scenario (1-3 or name)"
        if (-not $sel) {
            throw "No scenario given. Pass it as an argument, e.g. '.\dobby.ps1 init <target> github'."
        }
        if ($Scenarios -contains $sel) { return $sel }
        if ($sel -match '^[1-3]$') { return $Scenarios[[int]$sel - 1] }
        Write-Host "  '$sel' is not a valid choice." -ForegroundColor Yellow
    }
}

function New-ConfigSkeleton {
    param([string]$Scenario)
    switch ($Scenario) {
        'ado' {
            return [ordered]@{
                backend = 'ado'
                ado     = [ordered]@{
                    organization = 'https://dev.azure.com/YOUR-ORG/'
                    project      = 'YOUR-PROJECT'
                    team         = 'YOUR-TEAM'
                }
            }
        }
        'github' {
            return [ordered]@{
                backend = 'github'
                github  = [ordered]@{ owner = 'YOUR-OWNER'; repo = 'YOUR-REPO' }
            }
        }
        'combined' {
            return [ordered]@{
                backend = 'combined'
                ado     = [ordered]@{
                    organization = 'https://dev.azure.com/YOUR-ORG/'
                    project      = 'YOUR-PROJECT'
                    team         = 'YOUR-TEAM'
                }
                github  = [ordered]@{ owner = 'YOUR-OWNER'; repo = 'YOUR-REPO' }
            }
        }
    }
}

function Write-ConfigSkeleton {
    param([string]$TargetRoot, [string]$Scenario, [switch]$Force)
    $dobbyDir = Join-Path $TargetRoot '.dobby'
    $configPath = Join-Path $dobbyDir 'config.json'
    if ((Test-Path $configPath) -and -not $Force) {
        Write-Host "  .dobby/config.json already exists — left untouched." -ForegroundColor Yellow
        return
    }
    if (-not (Test-Path $dobbyDir)) { New-Item -ItemType Directory -Path $dobbyDir -Force | Out-Null }
    $json = (New-ConfigSkeleton -Scenario $Scenario) | ConvertTo-Json -Depth 5
    Set-Content -Path $configPath -Value $json -Encoding utf8
    Write-Host "  Wrote $configPath — fill in the placeholder connection details." -ForegroundColor Green
}

function Invoke-Init {
    param([string[]]$InitArgs)
    $target = if ($InitArgs.Count -ge 1) { $InitArgs[0] } else { $null }
    $scenario = if ($InitArgs.Count -ge 2) { $InitArgs[1] } else { $null }

    if (-not $target) {
        $target = Read-Prompt "Target project directory (Enter for current: $(Get-Location))" (Get-Location).Path
    }
    if (-not (Test-Path $target -PathType Container)) {
        throw "Target project directory does not exist: $target"
    }
    $target = (Resolve-Path $target).Path

    if (-not $scenario) { $scenario = Read-Scenario }
    if ($Scenarios -notcontains $scenario) {
        throw "Unknown scenario '$scenario'. Choose one of: $($Scenarios -join ', ')."
    }

    & $PyExe @PyPre $BuildSkills init $target $scenario
    $code = $LASTEXITCODE
    if ($code -ne 0) { return $code }

    # Decide on the config skeleton: explicit switches win; otherwise ask (skips when non-interactive).
    $writeConfig = $false
    if ($Config) { $writeConfig = $true }
    elseif ($NoConfig) { $writeConfig = $false }
    else {
        $answer = Read-Prompt "Write a .dobby/config.json skeleton for '$scenario' into the target? (y/N)" 'n'
        $writeConfig = $answer -match '^(y|yes)$'
    }

    if ($writeConfig) { Write-ConfigSkeleton -TargetRoot $target -Scenario $scenario -Force:$Force }
    else { Write-Host "  No config skeleton written. The skills collect connection details on first run." }

    Install-OpenSpec -TargetRoot $target
    return 0
}

# dobby does not bundle the OpenSpec workflow skills; install them per-project with the
# OpenSpec CLI. Runs `openspec init` when asked/confirmed, otherwise prints the command.
function Install-OpenSpec {
    param([string]$TargetRoot)

    $manualCmd = 'openspec init --tools "claude,github-copilot"'
    $hint = {
        Write-Host ""
        Write-Host "OpenSpec workflow skills are installed separately (dobby leaves them untouched):" -ForegroundColor Cyan
        Write-Host "  cd `"$TargetRoot`""
        Write-Host "  $manualCmd"
    }

    $run = $false
    if ($OpenSpec) { $run = $true }
    elseif ($NoOpenSpec) { $run = $false }
    else {
        $answer = Read-Prompt "Install the OpenSpec workflow into the target now (openspec init)? (y/N)" 'n'
        $run = $answer -match '^(y|yes)$'
    }

    if (-not $run) { & $hint; return }

    $openspec = Get-Command openspec -ErrorAction SilentlyContinue
    if (-not $openspec) {
        Write-Host "  openspec CLI not found on PATH. Install it (npm i -g @openspec/cli), then run:" -ForegroundColor Yellow
        & $hint
        return
    }

    Push-Location $TargetRoot
    # Quote the list as one token — a bare comma is PowerShell's array operator.
    try { & $openspec.Source init --tools 'claude,github-copilot' }
    finally { Pop-Location }
}

switch ($Command.ToLowerInvariant()) {
    'dev'   { & $PyExe @PyPre $BuildSkills dev; exit $LASTEXITCODE }
    'build' { & $PyExe @PyPre $BuildSkills build @Rest; exit $LASTEXITCODE }
    'check' { & $PyExe @PyPre $CheckSync; exit $LASTEXITCODE }
    'init'  { exit (Invoke-Init -InitArgs $Rest) }
    'help'  { Show-Help; exit 0 }
    '-h'    { Show-Help; exit 0 }
    '--help' { Show-Help; exit 0 }
    default {
        Write-Host "Unknown command '$Command'." -ForegroundColor Red
        Show-Help
        exit 2
    }
}
