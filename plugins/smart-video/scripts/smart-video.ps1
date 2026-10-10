[CmdletBinding(PositionalBinding = $false)]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PassThruArgs)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$selectedHome = if ($env:SMARTVIDEO_HOME) { $env:SMARTVIDEO_HOME } else { Join-Path $env:USERPROFILE ".codex\smartvideo-beta" }
$configPath = Join-Path $selectedHome "config.json"
for ($index = 0; $index -lt $PassThruArgs.Count; $index++) {
    if ($PassThruArgs[$index] -eq "--config" -and $index + 1 -lt $PassThruArgs.Count) { $configPath = $PassThruArgs[$index + 1]; break }
}
$configuredNode = $null
if (Test-Path -LiteralPath $configPath) {
    $configuration = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($configuration.PSObject.Properties["tools"] -and $configuration.tools.PSObject.Properties["node"]) { $configuredNode = $configuration.tools.node }
}
# Refresh this child from persistent PATH without restarting Codex.
$env:Path = @($env:Path, [Environment]::GetEnvironmentVariable("Path", "User"), [Environment]::GetEnvironmentVariable("Path", "Machine")) -join ";"
$node = if ($env:SMARTVIDEO_NODE_BINARY) { $env:SMARTVIDEO_NODE_BINARY } elseif ($configuredNode) { $configuredNode } else { $null }
if (-not $node) {
    $candidate = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { $node = $candidate.Path }
}
if (-not $node) {
    foreach ($root in @($env:ProgramFiles, $env:LOCALAPPDATA)) {
        if ($root -and (Test-Path -LiteralPath (Join-Path $root "nodejs\node.exe"))) { $node = Join-Path $root "nodejs\node.exe"; break }
    }
}
if (-not $node -or -not (Test-Path -LiteralPath $node)) {
    @{ schema = "smartvideo_environment_v1"; status = "blocked"; capability = "product-install"; dependencies = @(@{ id = "node"; status = "missing"; install_guidance = @{ official_url = "https://nodejs.org/en/download"; environment_variable = "SMARTVIDEO_NODE_BINARY"; user_choices = @("agent", "manual", "existing_path", "skip") } }) } | ConvertTo-Json -Depth 8
    exit 2
}
& $node (Join-Path $PSScriptRoot "launcher.mjs") @PassThruArgs
exit $LASTEXITCODE
