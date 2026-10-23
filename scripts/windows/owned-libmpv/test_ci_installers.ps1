param(
    [Parameter(Mandatory = $true)]
    [string]$MsiPath,
    [Parameter(Mandatory = $true)]
    [string]$NsisPath,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedDllHash
)

$ErrorActionPreference = 'Stop'
$productName = 'Ryotunes Omni CI Candidate'

function Get-InstalledProduct {
    $roots = @(
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $roots) {
        Get-ItemProperty $root -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -eq $productName }
    }
}

function Get-UninstallEntries {
    $roots = @(
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $roots) {
        Get-ItemProperty $root -ErrorAction SilentlyContinue
    }
}

function Get-NSISRegistration($InstallDir) {
    $installPath = [System.IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
    Get-UninstallEntries | Where-Object {
        $identity = @($_.InstallLocation, $_.DisplayIcon, $_.UninstallString) -join ' '
        $_.DisplayName -like '*Ryotunes Omni*' -and
            $identity.IndexOf($installPath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    }
}

function Get-ShortcutsToExecutable($Executable) {
    $roots = @(
        (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:PUBLIC 'Desktop'),
        (Join-Path $env:USERPROFILE 'Desktop')
    ) | Select-Object -Unique
    $target = [System.IO.Path]::GetFullPath($Executable)
    $shell = New-Object -ComObject WScript.Shell
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -Filter '*.lnk' -File -Recurse -ErrorAction Stop |
            ForEach-Object {
                $shortcut = $shell.CreateShortcut($_.FullName)
                if ($shortcut.TargetPath -and
                    [System.IO.Path]::GetFullPath($shortcut.TargetPath).Equals(
                        $target,
                        [System.StringComparison]::OrdinalIgnoreCase
                    )) {
                    $_.FullName
                }
            }
    }
}

function Assert-InstallDirectoryClean($InstallDir, $Label) {
    if (-not (Test-Path -LiteralPath $InstallDir)) { return }
    $remaining = @(Get-ChildItem -LiteralPath $InstallDir -Force -Recurse -ErrorAction Stop)
    if ($remaining.Count -gt 0) {
        $paths = $remaining | Select-Object -First 10 -ExpandProperty FullName
        throw "$Label uninstall left package-owned paths in $InstallDir`: $($paths -join ', ')"
    }
}

function Assert-ShortcutsRemoved([string[]]$Shortcuts, $Label) {
    $remaining = @($Shortcuts | Where-Object { Test-Path -LiteralPath $_ })
    if ($remaining.Count -gt 0) {
        throw "$Label uninstall left application shortcuts: $($remaining -join ', ')"
    }
}

function Assert-InstalledPayload($Entry, $Label) {
    if (-not $Entry) { throw "$Label uninstall registration is missing after install" }
    $executable = $null
    if ($Entry.DisplayIcon) {
        $icon = [string]$Entry.DisplayIcon -replace ',\s*\d+\s*$', ''
        $executable = $icon.Trim('"')
    }
    if (-not $executable -or -not (Test-Path -LiteralPath $executable)) {
        $location = [string]$Entry.InstallLocation
        if (-not $location) { throw "$Label install location was not registered" }
        $executable = Join-Path $location 'ryotune-omni.exe'
    }
    if (-not (Test-Path -LiteralPath $executable)) {
        throw "$Label application executable missing: $executable"
    }
    $dll = Join-Path (Split-Path -Parent $executable) 'libmpv-2.dll'
    if (-not (Test-Path -LiteralPath $dll)) { throw "$Label candidate DLL missing: $dll" }
    $actualHash = (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $ExpectedDllHash) {
        throw "$Label installed unexpected libmpv DLL hash: $actualHash"
    }
    return $executable
}

function Invoke-Installer($FilePath, [string[]]$Arguments, $Label, [int[]]$AllowedExitCodes = @(0)) {
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru
    if ($process.ExitCode -notin $AllowedExitCodes) {
        throw "$Label exited with code $($process.ExitCode)"
    }
}

if (-not (Test-Path -LiteralPath $MsiPath)) { throw "MSI missing: $MsiPath" }
if (-not (Test-Path -LiteralPath $NsisPath)) { throw "NSIS installer missing: $NsisPath" }

$msiLog = Join-Path $env:RUNNER_TEMP 'candidate-msi-install.log'
$msiUninstallLog = Join-Path $env:RUNNER_TEMP 'candidate-msi-uninstall.log'
Invoke-Installer 'msiexec.exe' @('/i', "`"$MsiPath`"", '/qn', '/norestart', '/l*v', "`"$msiLog`"") 'MSI install' @(0, 3010)
$msiEntry = @(Get-InstalledProduct)
if ($msiEntry.Count -ne 1) { throw "Expected one MSI uninstall registration, found $($msiEntry.Count)" }
$msiExecutable = Assert-InstalledPayload $msiEntry[0] 'MSI'
$msiInstallDir = Split-Path -Parent $msiExecutable
$msiShortcuts = @(Get-ShortcutsToExecutable $msiExecutable)
$msiResources = @(Get-ChildItem -LiteralPath $msiInstallDir -File -Recurse)
$msiLicenses = @($msiResources | Where-Object { $_.FullName -match '[\\/]licenses?[\\/]' })
Write-Host "INFO: MSI identity=$($msiEntry[0].DisplayName); version=$($msiEntry[0].DisplayVersion); installDir=$msiInstallDir; DLL SHA-256=$ExpectedDllHash; payloadFiles=$($msiResources.Count); shortcuts=$($msiShortcuts.Count)"
foreach ($file in $msiLicenses) { Write-Host "MSI LICENSE: $($file.FullName.Substring($msiInstallDir.Length).TrimStart('\'))" }
foreach ($shortcut in $msiShortcuts) { Write-Host "MSI SHORTCUT: $shortcut" }
Write-Host "PASS: MSI installed candidate executable and matching DLL at $msiExecutable"

$productCode = [regex]::Match([string]$msiEntry[0].UninstallString, '\{[0-9A-Fa-f-]{36}\}').Value
if (-not $productCode) { $productCode = [regex]::Match([string]$msiEntry[0].PSChildName, '\{[0-9A-Fa-f-]{36}\}').Value }
if (-not $productCode) { throw 'Could not determine MSI product code for uninstall' }
Invoke-Installer 'msiexec.exe' @('/x', $productCode, '/qn', '/norestart', '/l*v', "`"$msiUninstallLog`"") 'MSI uninstall' @(0, 3010)
if (@(Get-InstalledProduct).Count -ne 0) { throw 'MSI uninstall registration remains after uninstall' }
if (Test-Path -LiteralPath $msiExecutable) { throw "MSI uninstall left executable behind: $msiExecutable" }
if (Test-Path -LiteralPath (Join-Path $msiInstallDir 'libmpv-2.dll')) {
    throw "MSI uninstall left candidate DLL behind: $(Join-Path $msiInstallDir 'libmpv-2.dll')"
}
Assert-InstallDirectoryClean $msiInstallDir 'MSI'
Assert-ShortcutsRemoved $msiShortcuts 'MSI'
Write-Host 'PASS: MSI uninstalled and removed registration, payload, package directory contents, and shortcuts'

$nsisInstallDir = Join-Path $env:RUNNER_TEMP 'ryotune-nsis-install'
Invoke-Installer $NsisPath @('/S', "/D=$nsisInstallDir") 'NSIS install'
$nsisExecutable = Join-Path $nsisInstallDir 'ryotune-omni.exe'
if (-not (Test-Path -LiteralPath $nsisExecutable)) { throw "NSIS application executable missing: $nsisExecutable" }
$nsisDll = Join-Path $nsisInstallDir 'libmpv-2.dll'
if (-not (Test-Path -LiteralPath $nsisDll)) { throw "NSIS candidate DLL missing: $nsisDll" }
$nsisHash = (Get-FileHash -LiteralPath $nsisDll -Algorithm SHA256).Hash.ToLowerInvariant()
if ($nsisHash -ne $ExpectedDllHash) { throw "NSIS installed unexpected libmpv DLL hash: $nsisHash" }
$uninstaller = Get-ChildItem -LiteralPath $nsisInstallDir -File -Filter '*uninstall*.exe' | Select-Object -First 1
if (-not $uninstaller) { $uninstaller = Get-ChildItem -LiteralPath $nsisInstallDir -File -Filter '*unins*.exe' | Select-Object -First 1 }
if (-not $uninstaller) { throw 'NSIS uninstaller executable missing' }
$nsisRegistration = @(Get-NSISRegistration $nsisInstallDir)
if ($nsisRegistration.Count -eq 0) { throw 'NSIS uninstall registration was not found for the isolated install directory' }
$nsisShortcuts = @(Get-ShortcutsToExecutable $nsisExecutable)
$nsisResources = @(Get-ChildItem -LiteralPath $nsisInstallDir -File -Recurse)
$nsisLicenses = @($nsisResources | Where-Object { $_.FullName -match '[\\/]licenses?[\\/]' })
Write-Host "INFO: NSIS identity=$($nsisRegistration[0].DisplayName); version=$($nsisRegistration[0].DisplayVersion); installDir=$nsisInstallDir; DLL SHA-256=$nsisHash; payloadFiles=$($nsisResources.Count); shortcuts=$($nsisShortcuts.Count)"
foreach ($file in $nsisLicenses) { Write-Host "NSIS LICENSE: $($file.FullName.Substring($nsisInstallDir.Length).TrimStart('\'))" }
foreach ($shortcut in $nsisShortcuts) { Write-Host "NSIS SHORTCUT: $shortcut" }
Write-Host "PASS: NSIS installed candidate executable and matching DLL at $nsisExecutable"
Invoke-Installer $uninstaller.FullName @('/S') 'NSIS uninstall'
if (Test-Path -LiteralPath $nsisExecutable) { throw "NSIS uninstall left executable behind: $nsisExecutable" }
if (Test-Path -LiteralPath $nsisDll) { throw "NSIS uninstall left candidate DLL behind: $nsisDll" }
if (@(Get-NSISRegistration $nsisInstallDir).Count -ne 0) { throw 'NSIS uninstall registration remains after uninstall' }
Assert-InstallDirectoryClean $nsisInstallDir 'NSIS'
Assert-ShortcutsRemoved $nsisShortcuts 'NSIS'
Write-Host 'PASS: NSIS uninstalled and removed registration, payload, package directory contents, and shortcuts'
Write-Host 'INFO: Neither package was launched; per-user app-data preservation/removal was not exercised.'
