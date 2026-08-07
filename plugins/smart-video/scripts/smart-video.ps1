[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PassThruArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-CommandPath {
    param([Parameter(Mandatory = $true)][string]$Name)

    $command = Get-Command -Name $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($command) { return $command.Path }
    return $null
}

function Get-CommandPaths {
    param([Parameter(Mandatory = $true)][string]$Name)

    return @(Get-Command -Name $Name -CommandType Application -All -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Path } |
        Select-Object -Unique)
}

function Refresh-ProcessPath {
    $values = @(
        $env:Path,
        [Environment]::GetEnvironmentVariable("Path", "Machine"),
        [Environment]::GetEnvironmentVariable("Path", "User")
    )
    $seen = @{}
    $segments = foreach ($value in $values) {
        foreach ($segment in ($value -split ";")) {
            $normalized = $segment.Trim()
            if ($normalized -and -not $seen.ContainsKey($normalized.ToLowerInvariant())) {
                $seen[$normalized.ToLowerInvariant()] = $true
                $normalized
            }
        }
    }
    $env:Path = $segments -join ";"
}

function Use-CommandDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    $directory = Split-Path -Parent $Path
    $segments = @($env:Path -split ";")
    if ($segments.Count -eq 0 -or $segments[0] -ne $directory) {
        $env:Path = "$directory;$env:Path"
    }
}

function Get-GitCygpathPath {
    param([Parameter(Mandatory = $true)][string]$BashPath)
    if (-not (Test-Path -LiteralPath $BashPath)) { return $null }
    $gitRoot = Split-Path -Parent (Split-Path -Parent $BashPath)
    $cygpath = Join-Path $gitRoot "usr\bin\cygpath.exe"
    if (Test-Path -LiteralPath $cygpath) { return $cygpath }
    return $null
}

function Find-GitBash {
    $programFilesX86 = Get-Item -Path "Env:ProgramFiles(x86)" -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
    $candidates = @()
    foreach ($root in @($env:ProgramFiles, $env:ProgramW6432, $programFilesX86)) {
        if ($root) { $candidates += Join-Path $root "Git\bin\bash.exe" }
    }

    $candidates += @(Get-CommandPaths "bash.exe")
    foreach ($candidate in @($candidates | Select-Object -Unique)) {
        if (Get-GitCygpathPath $candidate) {
            Use-CommandDirectory $candidate
            return $candidate
        }
    }
    return $null
}

function Test-ChromeInstalled {
    if (Get-CommandPath "chrome.exe") { return $true }
    $programFilesX86 = Get-Item -Path "Env:ProgramFiles(x86)" -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
    foreach ($root in @($env:ProgramFiles, $env:ProgramW6432, $programFilesX86, $env:LOCALAPPDATA)) {
        if ($root -and (Test-Path -LiteralPath (Join-Path $root "Google\Chrome\Application\chrome.exe"))) {
            return $true
        }
    }
    return $false
}

function Get-NodePath {
    $fallback = $null
    foreach ($path in @(Get-CommandPaths "node.exe")) {
        try {
            $version = (& $path --version 2>$null | Select-Object -First 1)
            if ($LASTEXITCODE -ne 0 -or -not $version) { continue }
            if (-not $fallback) { $fallback = $path }
            $major = 0
            if ([int]::TryParse(($version.Trim().TrimStart("v") -split "\.")[0], [ref]$major) -and $major -ge 22) {
                Use-CommandDirectory $path
                return $path
            }
        } catch {
            continue
        }
    }
    return $fallback
}

function Get-NodeVersion {
    $node = Get-NodePath
    if (-not $node) { return $null }
    try {
        $version = (& $node --version 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -ne 0 -or -not $version) { return $null }
        return $version.Trim().TrimStart("v")
    } catch {
        return $null
    }
}

function Test-NodeVersion {
    $version = Get-NodeVersion
    if (-not $version) { return $false }
    $major = 0
    if (-not [int]::TryParse(($version -split "\.")[0], [ref]$major)) { return $false }
    return $major -ge 22
}

function Get-PythonPath {
    $fallback = $null
    foreach ($name in @("python.exe", "python3.exe")) {
        foreach ($path in @(Get-CommandPaths $name)) {
            try {
                $version = (& $path -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null | Select-Object -First 1)
                if ($LASTEXITCODE -ne 0 -or -not $version) { continue }
                if (-not $fallback) { $fallback = $path }
                if (([version]$version.Trim()) -ge ([version]"3.10")) {
                    Use-CommandDirectory $path
                    return $path
                }
            } catch {
                continue
            }
        }
    }
    return $fallback
}

function Get-PythonVersion {
    $python = Get-PythonPath
    if (-not $python) { return $null }
    try {
        $version = (& $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -ne 0 -or -not $version) { return $null }
        return $version.Trim()
    } catch {
        return $null
    }
}

function Test-PythonVersion {
    $version = Get-PythonVersion
    if (-not $version) { return $false }
    try {
        return ([version]$version) -ge ([version]"3.10")
    } catch {
        return $false
    }
}

function Test-FFmpegCapabilities {
    foreach ($ffmpeg in @(Get-CommandPaths "ffmpeg.exe")) {
        $directory = Split-Path -Parent $ffmpeg
        $ffprobe = Join-Path $directory "ffprobe.exe"
        if (-not (Test-FFprobePath $ffprobe)) { continue }
        try {
            $encoders = (& $ffmpeg -hide_banner -encoders 2>$null | Out-String)
            if ($LASTEXITCODE -ne 0) { continue }
            $complete = $true
            foreach ($encoder in @("libx264", "aac", "libvpx-vp9")) {
                $pattern = "(?m)^\s*\S+\s+" + [regex]::Escape($encoder) + "(?:\s|$)"
                if ($encoders -notmatch $pattern) {
                    $complete = $false
                    break
                }
            }
            if (-not $complete) { continue }
            $filters = (& $ffmpeg -hide_banner -filters 2>$null | Out-String)
            if ($LASTEXITCODE -ne 0 -or $filters -notmatch "(?m)^\s*\S+\s+subtitles(?:\s|$)") { continue }
            Use-CommandDirectory $ffmpeg
            return $true
        } catch {
            continue
        }
    }
    return $false
}

function Test-FFprobePath {
    param([string]$Path = (Get-CommandPath "ffprobe.exe"))
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $version = (& $Path -version 2>$null | Select-Object -First 1)
        return $LASTEXITCODE -eq 0 -and $version -match "^ffprobe version "
    } catch {
        return $false
    }
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)][string]$PackageId,
        [Parameter(Mandatory = $true)][string]$DisplayName
    )

    $winget = Get-CommandPath "winget.exe"
    if (-not $winget) {
        throw "Smart Video needs $DisplayName, but Windows Package Manager (winget) is unavailable. Install App Installer from Microsoft Store, then run this command again."
    }

    $listed = (& $winget list --id $PackageId --exact 2>$null | Out-String)
    $verb = if ($LASTEXITCODE -eq 0 -and $listed -match [regex]::Escape($PackageId)) { "upgrade" } else { "install" }
    Write-Host "[smart-video] Running winget $verb for $DisplayName..."
    & $winget $verb --id $PackageId --exact --accept-package-agreements `
        --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) {
        throw "winget could not $verb $DisplayName (package: $PackageId, exit code: $LASTEXITCODE). Resolve the Windows installer prompt and run Smart Video again."
    }
    Refresh-ProcessPath
}

function Ensure-WindowsHostTools {
    Refresh-ProcessPath
    $tools = @(
        @{ Name = "Git for Windows"; PackageId = "Git.Git"; Present = { [bool](Find-GitBash) } },
        @{ Name = "Python 3.10+"; PackageId = "Python.Python.3.12"; Present = { Test-PythonVersion } },
        @{ Name = "Node.js 22+"; PackageId = "OpenJS.NodeJS.LTS"; Present = { Test-NodeVersion } },
        @{ Name = "FFmpeg with required codecs"; PackageId = "Gyan.FFmpeg"; Present = { Test-FFmpegCapabilities } },
        @{ Name = "jq"; PackageId = "jqlang.jq"; Present = { [bool](Get-CommandPath "jq.exe") } },
        @{ Name = "Google Chrome"; PackageId = "Google.Chrome"; Present = { Test-ChromeInstalled } }
    )

    foreach ($tool in $tools) {
        if (-not (& $tool.Present)) {
            Install-WingetPackage -PackageId $tool.PackageId -DisplayName $tool.Name
        }
        if (-not (& $tool.Present)) {
            throw "$($tool.Name) was installed but is not available in this PowerShell session. Close and reopen PowerShell, then run Smart Video again."
        }
    }
}

function Get-WindowsHostReport {
    Refresh-ProcessPath
    $pythonPath = Get-PythonPath
    $nodePath = Get-NodePath
    $ffmpegCompatible = Test-FFmpegCapabilities
    $ffmpegPath = Get-CommandPath "ffmpeg.exe"
    $ffprobePath = Get-CommandPath "ffprobe.exe"
    $ffprobeCompatible = Test-FFprobePath $ffprobePath
    $definitions = @(
        @{ Name = "git-bash"; Path = (Find-GitBash); Version = ""; Required = ""; Compatible = [bool](Find-GitBash) },
        @{ Name = "python"; Path = $pythonPath; Version = (Get-PythonVersion); Required = ">=3.10"; Compatible = (Test-PythonVersion) },
        @{ Name = "node"; Path = $nodePath; Version = (Get-NodeVersion); Required = ">=22"; Compatible = (Test-NodeVersion) },
        @{ Name = "ffmpeg"; Path = $ffmpegPath; Version = ""; Required = "encoders=libx264,aac,libvpx-vp9;filter=subtitles"; Compatible = $ffmpegCompatible },
        @{ Name = "ffprobe"; Path = $ffprobePath; Version = ""; Required = "working ffprobe from the FFmpeg distribution"; Compatible = $ffprobeCompatible },
        @{ Name = "jq"; Path = (Get-CommandPath "jq.exe"); Version = ""; Required = ""; Compatible = [bool](Get-CommandPath "jq.exe") },
        @{ Name = "chrome"; Path = ""; Version = ""; Required = ""; Compatible = (Test-ChromeInstalled) }
    )
    $dependencies = foreach ($definition in $definitions) {
        $installed = if ($definition.Name -eq "chrome") { [bool]$definition.Compatible } else { [bool]$definition.Path }
        [pscustomobject]@{
            name = $definition.Name
            installed = $installed
            compatible = [bool]$definition.Compatible
            version = [string]$definition.Version
            path = [string]$definition.Path
            required_version = [string]$definition.Required
        }
    }
    $missing = @($dependencies | Where-Object { -not $_.installed } | ForEach-Object { $_.name })
    $incompatible = @($dependencies | Where-Object { $_.installed -and -not $_.compatible } | ForEach-Object { $_.name })
    $status = if ($missing.Count -eq 0 -and $incompatible.Count -eq 0) { "ready" } else { "dependencies_missing" }
    [pscustomobject]@{
        status = $status
        platform = "Windows"
        dependencies = @($dependencies)
        missing = $missing
        incompatible = $incompatible
        bootstrap_command = "& `"$PSScriptRoot\smart-video.cmd`" bootstrap"
    } | ConvertTo-Json -Compress -Depth 5
}

function Convert-ToGitBashPath {
    param(
        [Parameter(Mandatory = $true)][string]$BashPath,
        [Parameter(Mandatory = $true)][string]$WindowsPath
    )

    $cygpath = Get-GitCygpathPath $BashPath
    if ($cygpath) {
        $converted = (& $cygpath -u -- $WindowsPath | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $converted) { return $converted.Trim() }
    }
    return $WindowsPath.Replace("\", "/")
}

function Convert-RunnerArguments {
    param(
        [Parameter(Mandatory = $true)][string]$BashPath,
        [string[]]$Arguments
    )

    $pathOptions = @("--config", "--planning-file", "--html-file", "--spec-file", "--file")
    $converted = @()
    for ($index = 0; $index -lt $Arguments.Count; $index++) {
        $argument = $Arguments[$index]
        $converted += $argument
        if ($pathOptions -contains $argument -and $index + 1 -lt $Arguments.Count) {
            $index++
            $converted += Convert-ToGitBashPath -BashPath $BashPath -WindowsPath $Arguments[$index]
        }
    }
    return $converted
}

function Get-SmartVideoAction {
    for ($index = 0; $index -lt $PassThruArgs.Count; $index++) {
        if ($PassThruArgs[$index] -eq "--config") {
            $index++
            continue
        }
        if (-not $PassThruArgs[$index].StartsWith("--")) {
            return $PassThruArgs[$index]
        }
    }
    return ""
}

$action = Get-SmartVideoAction
if ($action -in @("bootstrap", "install-deps")) {
    Ensure-WindowsHostTools
}

$bash = Find-GitBash
if (-not $bash) {
    Get-WindowsHostReport
    if ($action -eq "doctor") { exit 0 }
    Write-Error "Smart Video needs Git for Windows. Run: & `"$PSScriptRoot\smart-video.cmd`" bootstrap"
    exit 1
}

$runner = Join-Path $PSScriptRoot "smart-video.sh"
$bashRunner = Convert-ToGitBashPath -BashPath $bash -WindowsPath $runner
$bashArguments = Convert-RunnerArguments -BashPath $bash -Arguments $PassThruArgs
& $bash --noprofile --norc $bashRunner @bashArguments
exit $LASTEXITCODE
