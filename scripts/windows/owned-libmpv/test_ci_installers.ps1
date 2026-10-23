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
Write-Host "PASS: MSI installed candidate executable and matching DLL at $msiExecutable"

$productCode = [regex]::Match([string]$msiEntry[0].UninstallString, '\{[0-9A-Fa-f-]{36}\}').Value
if (-not $productCode) { $productCode = [regex]::Match([string]$msiEntry[0].PSChildName, '\{[0-9A-Fa-f-]{36}\}').Value }
if (-not $productCode) { throw 'Could not determine MSI product code for uninstall' }
Invoke-Installer 'msiexec.exe' @('/x', $productCode, '/qn', '/norestart', '/l*v', "`"$msiUninstallLog`"") 'MSI uninstall' @(0, 3010)
if (@(Get-InstalledProduct).Count -ne 0) { throw 'MSI uninstall registration remains after uninstall' }
if (Test-Path -LiteralPath $msiExecutable) { throw "MSI uninstall left executable behind: $msiExecutable" }
Write-Host 'PASS: MSI uninstalled and removed its registration and executable'

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
Write-Host "PASS: NSIS installed candidate executable and matching DLL at $nsisExecutable"
Invoke-Installer $uninstaller.FullName @('/S') 'NSIS uninstall'
if (Test-Path -LiteralPath $nsisExecutable) { throw "NSIS uninstall left executable behind: $nsisExecutable" }
Write-Host 'PASS: NSIS uninstalled and removed its executable'
