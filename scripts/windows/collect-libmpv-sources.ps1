$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outputDirectory = Join-Path $repositoryRoot ".libmpv\source-partial"
$sources = @(
    @{
        Name = "mpv-a43ab319fdb7aec31874999e5562c9975328cbda.tar.gz"
        Url = "https://codeload.github.com/mpv-player/mpv/tar.gz/a43ab319fdb7aec31874999e5562c9975328cbda"
        Sha256 = "c7198e76676aaa730164f5535dd4d7c562e616216c793785ca5a63738d611948"
        Component = "mpv"
        ArchiveRoot = "mpv-a43ab319fdb7aec31874999e5562c9975328cbda"
        Notices = @("Copyright", "LICENSE.GPL", "LICENSE.LGPL")
    },
    @{
        Name = "ffmpeg-ca85613d10cd523dd05780f48dc6ecac142bd560.tar.gz"
        Url = "https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/ca85613d10cd523dd05780f48dc6ecac142bd560"
        Sha256 = "589ea7ec9a2d42673b1e18685f5cf936e0cf29bf38e002b54867a0b91399ff2c"
        Component = "ffmpeg"
        ArchiveRoot = "FFmpeg-ca85613d10cd523dd05780f48dc6ecac142bd560"
        Notices = @("LICENSE.md", "COPYING.GPLv2", "COPYING.GPLv3", "COPYING.LGPLv2.1", "COPYING.LGPLv3")
    }
)

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

foreach ($source in $sources) {
    $destination = Join-Path $outputDirectory $source.Name
    $currentHash = if (Test-Path $destination) {
        (Get-FileHash -Algorithm SHA256 $destination).Hash.ToLowerInvariant()
    } else {
        ""
    }

    if ($currentHash -ne $source.Sha256) {
        $downloadPath = "$destination.download"
        Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
        Invoke-WebRequest -Uri $source.Url -OutFile $downloadPath
        $downloadHash = (Get-FileHash -Algorithm SHA256 $downloadPath).Hash.ToLowerInvariant()
        if ($downloadHash -ne $source.Sha256) {
            Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
            throw "Source archive SHA-256 mismatch for $($source.Name): expected $($source.Sha256), got $downloadHash"
        }
        Move-Item -LiteralPath $downloadPath -Destination $destination -Force
        $currentHash = $downloadHash
    }

    Write-Output "$($source.Name) SHA-256: $currentHash"

    $noticeCache = Join-Path $outputDirectory "notices\$($source.Component)"
    $noticeDestination = Join-Path $repositoryRoot "src-tauri\licenses\$($source.Component)"
    New-Item -ItemType Directory -Path $noticeCache -Force | Out-Null
    New-Item -ItemType Directory -Path $noticeDestination -Force | Out-Null
    $archiveEntries = $source.Notices | ForEach-Object { "$($source.ArchiveRoot)/$_" }
    & tar -xzf $destination -C $noticeCache --strip-components=1 @archiveEntries
    if ($LASTEXITCODE -ne 0) {
        throw "Could not extract license notices from $($source.Name)"
    }
    foreach ($notice in $source.Notices) {
        Copy-Item -LiteralPath (Join-Path $noticeCache $notice) -Destination (Join-Path $noticeDestination $notice) -Force
    }
    Write-Output "Verified-source notices prepared: $noticeDestination"
}

$sourceLines = $sources | ForEach-Object {
    "- $($_.Name): $($_.Url) (SHA-256 $($_.Sha256))"
}
$sourceList = $sourceLines -join "`n"
$manifest = @"
# Partial libmpv corresponding-source collection

This directory contains pinned source archives for mpv and FFmpeg used by the selected upstream build. It is **not** the complete corresponding source for the shipped DLL and must not be presented as a complete GPL source package.

$sourceList

Other statically linked dependencies were supplied by the upstream FFmpeg build container or fetched from moving branch/HEAD references. Their exact source revisions and complete license texts are not recorded in the upstream artifact. Resolve those inputs and add their source and notices before release.
"@
Set-Content -LiteralPath (Join-Path $outputDirectory "SOURCE-COLLECTION-PARTIAL.md") -Value $manifest -Encoding utf8
