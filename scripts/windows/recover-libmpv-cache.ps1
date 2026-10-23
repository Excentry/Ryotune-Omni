$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Net.Http

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outputDirectory = Join-Path $repositoryRoot ".libmpv\btbn-39601828709"
$archivePath = Join-Path $outputDirectory "download-cache.zip"
$expectedHash = "ea73dfe500a66c3b9f545954f0c9935d3eb8e241c60449dd1ae574e5d43e464d"
$metadataText = & gh api repos/BtbN/FFmpeg-Builds/actions/artifacts/12346534162
if ($LASTEXITCODE -ne 0) { throw "Could not retrieve BtbN cache metadata" }
$metadata = $metadataText | ConvertFrom-Json
if ($metadata.expired -or $metadata.digest -ne "sha256:$expectedHash" -or $metadata.workflow_run.id -ne 39601828709) {
    throw "BtbN cache metadata does not match the selected source recovery input"
}

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$currentHash = if (Test-Path $archivePath) { (Get-FileHash -Algorithm SHA256 $archivePath).Hash.ToLowerInvariant() } else { "" }
if ($currentHash -ne $expectedHash) {
    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $apiClient = [System.Net.Http.HttpClient]::new($handler)
    $downloadClient = [System.Net.Http.HttpClient]::new()
    $downloadClient.Timeout = [TimeSpan]::FromHours(2)
    $response = $null
    $downloadResponse = $null
    $inputStream = $null
    $outputStream = $null
    try {
        $token = & gh auth token
        if ($LASTEXITCODE -ne 0) { throw "GitHub CLI authentication is unavailable" }
        $apiClient.DefaultRequestHeaders.UserAgent.ParseAdd("Ryotunes-Omni-source-recovery")
        $apiClient.DefaultRequestHeaders.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $token.Trim())
        $token = $null
        $response = $apiClient.GetAsync("https://api.github.com/repos/BtbN/FFmpeg-Builds/actions/artifacts/12346534162/zip").GetAwaiter().GetResult()
        if ([int]$response.StatusCode -ne 302) { throw "GitHub artifact download returned HTTP $([int]$response.StatusCode)" }
        $downloadUri = $response.Headers.Location
        if (-not $downloadUri.IsAbsoluteUri -or $downloadUri.Scheme -ne "https") { throw "Invalid artifact download redirect" }
        $downloadResponse = $downloadClient.GetAsync($downloadUri, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        if (-not $downloadResponse.IsSuccessStatusCode) { throw "Artifact storage returned HTTP $([int]$downloadResponse.StatusCode)" }
        $inputStream = $downloadResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $outputStream = [System.IO.File]::Open("$archivePath.download", [System.IO.FileMode]::Create)
        $inputStream.CopyTo($outputStream)
        $outputStream.Dispose()
        $outputStream = $null
    } catch {
        throw "BtbN source cache download failed; partial bytes retained. No download URL or credentials are included in this error."
    } finally {
        if ($outputStream) { $outputStream.Dispose() }
        if ($inputStream) { $inputStream.Dispose() }
        if ($downloadResponse) { $downloadResponse.Dispose() }
        if ($response) { $response.Dispose() }
        $apiClient.Dispose()
        $downloadClient.Dispose()
        $handler.Dispose()
        $token = $null
    }
    $downloadHash = (Get-FileHash -Algorithm SHA256 "$archivePath.download").Hash.ToLowerInvariant()
    if ($downloadHash -ne $expectedHash) { throw "BtbN source cache SHA-256 mismatch: $downloadHash" }
    if ((Get-Item "$archivePath.download").Length -ne $metadata.size_in_bytes) { throw "BtbN source cache size mismatch" }
    Move-Item -LiteralPath "$archivePath.download" -Destination $archivePath -Force
}

Set-Content -LiteralPath (Join-Path $outputDirectory "artifact.json") -Value $metadataText -Encoding utf8
Write-Output "BtbN cache verified: $archivePath"
Write-Output "SHA-256: $expectedHash"
Write-Output "Source correspondence audit remains incomplete; this cache is not a complete source distribution."
