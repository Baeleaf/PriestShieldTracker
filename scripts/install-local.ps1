param(
    [string]$AddOnsDirectory = 'C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$versionLine = Get-Content -LiteralPath (Join-Path $projectRoot 'PriestShieldTracker.toc') |
    Where-Object { $_ -match '^## Version: ' } | Select-Object -First 1
$version = $versionLine -replace '^## Version: ', ''
$packagePath = Join-Path $projectRoot "dist\PriestShieldTracker-$version.zip"
if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    throw "Build the release package first: python scripts/package.py --tag v$version"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$targetRoot = [IO.Path]::GetFullPath($AddOnsDirectory).TrimEnd('\') + '\'
$sessionName = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$backupRoot = Join-Path $projectRoot ".local\install-backups\$sessionName"
$stageRoot = Join-Path $projectRoot ".local\install-stage\$sessionName"
$archive = [IO.Compression.ZipFile]::OpenRead($packagePath)
try {
    $files = @()
    foreach ($entry in $archive.Entries) {
        if ($entry.FullName.EndsWith('/')) { continue }
        if ($entry.FullName -notmatch '^(PriestShieldTracker|SoulShield)/' -or
            $entry.FullName -match '(^|[/\\])\.\.([/\\]|$)' -or
            $entry.FullName.Contains(':')) { throw "Unsafe package entry: $($entry.FullName)" }
        $relative = $entry.FullName.Replace('/', '\')
        $destination = [IO.Path]::GetFullPath((Join-Path $targetRoot $relative))
        if (-not $destination.StartsWith($targetRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Package entry leaves the AddOns directory: $relative"
        }
        $staged = Join-Path $stageRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $staged) -Force | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $staged, $true)
        $files += [PSCustomObject]@{ Relative = $relative; Source = $staged; Destination = $destination }
    }
} finally { $archive.Dispose() }
if ($files.Count -lt 3) { throw 'The release package contains too few runtime files.' }
$changed = 0
foreach ($file in $files) {
    if (Test-Path -LiteralPath $file.Destination -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $file.Source).Hash -eq (Get-FileHash -LiteralPath $file.Destination).Hash) { continue }
        $backup = Join-Path $backupRoot $file.Relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $file.Destination -Destination $backup
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $file.Destination) -Force | Out-Null
    Copy-Item -LiteralPath $file.Source -Destination $file.Destination -Force
    $changed++
}
foreach ($file in $files) {
    if ((Get-FileHash -LiteralPath $file.Source).Hash -ne (Get-FileHash -LiteralPath $file.Destination).Hash) {
        throw "Installed file verification failed: $($file.Relative)"
    }
}
Write-Host "PriestShieldTracker $version installed and verified ($($files.Count) files; $changed updated)."
Write-Host 'Character settings and development files were preserved. In WoW, run /reload, then /pst settings.'
if ($changed) { Write-Host "Previous files backed up to $backupRoot" }
