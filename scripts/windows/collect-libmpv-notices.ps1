$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$directory = Join-Path $repositoryRoot ".libmpv\btbn-39601828709"
$inventory = Get-Content (Join-Path $directory "selected-source-inventory.json") -Raw | ConvertFrom-Json
$noticeRoot = Join-Path $directory "notice-review"
New-Item -ItemType Directory -Path $noticeRoot -Force | Out-Null

$records = foreach ($component in $inventory) {
    $archivePath = Join-Path $directory "selected-sources\$($component.Archive)"
    $hash = (Get-FileHash -Algorithm SHA256 $archivePath).Hash.ToLowerInvariant()
    if ($hash -ne $component.Sha256) { throw "Source archive changed: $($component.Archive)" }
    $componentName = $component.Archive -replace '_[a-f0-9]{64}\.tar\.xz$', ''
    if ($componentName -notmatch '^[a-zA-Z0-9-]+$') { throw "Unsafe component name" }
    $componentDirectory = Join-Path $noticeRoot $componentName
    New-Item -ItemType Directory -Path $componentDirectory -Force | Out-Null
    $selected = @($component.NoticePaths | Where-Object {
        $_ -notmatch '/$' -and (($_ -replace '^\./', '') -notmatch '/' -or $_ -match '^\./(?:licenses|LICENSES|doc|docs)/[^/]+$')
    })
    if ($componentName -eq "50-ffnvcodec") {
        $selected = @("./ffnvcodec/include/ffnvcodec/nvEncodeAPI.h", "./ffnvcodec/include/ffnvcodec/dynlink_cuviddec.h")
    }
    if ($componentName -eq "45-opencl") {
        $selected += @("./loader/LICENSE", "./headers/LICENSE")
    }
    if ($componentName -eq "50-avisynth") {
        $selected += "./distrib/docs/english/source/avisynthdoc/license.rst"
    }
    foreach ($entry in $selected) {
        $sourceEntry = $entry
        if ($componentName -eq "10-glib" -and $entry -eq "./COPYING") {
            $sourceEntry = "./LICENSES/LGPL-2.1-or-later.txt"
        }
        if ($componentName -eq "40-libpsl" -and $entry -eq "./COPYING") {
            $sourceEntry = "./LICENSE"
        }
        $relativePath = $entry -replace '^\./', ''
        if ($relativePath -notmatch '^[a-zA-Z0-9_./ -]+$' -or $relativePath -match '(^|/)\.\.(/|$)|^/') {
            throw "Unsafe notice path in $componentName"
        }
        $destination = Join-Path $componentDirectory $relativePath
        New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
        $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = "tar.exe"
        $startInfo.Arguments = "-xOJf `"$archivePath`" `"$sourceEntry`""
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $process = [System.Diagnostics.Process]::Start($startInfo)
        $stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::Create)
        try {
            $errorTask = $process.StandardError.ReadToEndAsync()
            $process.StandardOutput.BaseStream.CopyTo($stream)
            $process.WaitForExit()
            $null = $errorTask.GetAwaiter().GetResult()
            if ($process.ExitCode -ne 0) { throw "Could not read $entry from $componentName" }
        } finally {
            $stream.Dispose()
            $process.Dispose()
        }
        $bytes = (Get-Item $destination).Length
        [pscustomobject]@{
            Component = $componentName
            SourceArchive = $component.Archive
            SourceSha256 = $hash
            Entry = $entry
            SourceEntry = $sourceEntry
            Bytes = $bytes
            NoticeSha256 = (Get-FileHash -Algorithm SHA256 $destination).Hash.ToLowerInvariant()
            Status = if ($bytes -gt 0) { "Preserved source notice; human license and inclusion review required" } else { "Empty entry or archived link; review required" }
        }
    }
}
$records | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $directory "notice-review-index.json") -Encoding utf8
Write-Output "Preserved $(@($records).Count) notice inputs under $noticeRoot"
Write-Output "This is a top-level notice corpus, not a complete distribution notice package."
