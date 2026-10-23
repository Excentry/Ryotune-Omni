$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$directory = Join-Path $repositoryRoot ".libmpv\btbn-39601828709"
$archive = Join-Path $directory "cache.tar.gz"
$buildLog = Join-Path $directory "btbn-win64-gpl.log"
$sourcesDirectory = Join-Path $directory "selected-sources"
$log = Get-Content -LiteralPath $buildLog -Raw
$sourceNames = @([regex]::Matches($log, '\.cache/downloads/([a-zA-Z0-9-]+_[a-f0-9]{64}\.tar\.xz)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
if (-not $sourceNames.Count) { throw "No hashed source inputs found in the Windows GPL build log" }
$archiveEntries = @(& tar -tzf $archive)
if ($LASTEXITCODE -ne 0) { throw "Could not list preserved source cache" }
$missing = @($sourceNames | Where-Object { ".cache/downloads/$_" -notin $archiveEntries })
if ($missing.Count) { throw "Build inputs missing from preserved source cache: $($missing -join ', ')" }
New-Item -ItemType Directory -Path $sourcesDirectory -Force | Out-Null
$selectedEntries = $sourceNames | ForEach-Object { ".cache/downloads/$_" }
& tar -xzf $archive -C $sourcesDirectory --strip-components=2 @selectedEntries
if ($LASTEXITCODE -ne 0) { throw "Could not extract selected source archives" }

$inventory = foreach ($name in $sourceNames) {
    $path = Join-Path $sourcesDirectory $name
    $entries = @(& tar -tJf $path)
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect $name" }
    $revisions = foreach ($headPath in @($entries | Where-Object { $_ -match '(?:^|/)\.git/HEAD$' })) {
        $head = (& tar -xOJf $path $headPath) -join "`n"
        if ($LASTEXITCODE -ne 0) { throw "Could not read archived HEAD in $name" }
        $commit = $null
        if ($head -match '^[a-f0-9]{40}$') {
            $commit = $head
        } elseif ($head -match '^ref: (refs/[a-zA-Z0-9_./-]+)$') {
            $reference = $Matches[1]
            $gitDirectory = $headPath.Substring(0, $headPath.Length - 4)
            $referencePath = "$gitDirectory$reference"
            if ($referencePath -in $entries) {
                $commit = ((& tar -xOJf $path $referencePath) -join "`n").Trim()
                if ($LASTEXITCODE -ne 0) { throw "Could not read archived Git ref in $name" }
            } elseif ("${gitDirectory}packed-refs" -in $entries) {
                $packedRefs = @(& tar -xOJf $path "${gitDirectory}packed-refs")
                if ($LASTEXITCODE -ne 0) { throw "Could not read archived packed refs in $name" }
                $line = $packedRefs | Where-Object { $_ -match "^[a-f0-9]{40} $([regex]::Escape($reference))$" } | Select-Object -First 1
                if ($line) { $commit = $line.Substring(0, 40) }
            }
        }
        if ($commit -and $commit -notmatch '^[a-f0-9]{40}$') { throw "Invalid archived Git commit in $name" }
        [pscustomobject]@{ HeadPath = $headPath; Commit = $commit }
    }
    [pscustomobject]@{
        Archive = $name
        Sha256 = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant()
        Bytes = (Get-Item $path).Length
        ArchivedGitRevisions = @($revisions)
        NoticePaths = @($entries | Where-Object { $_ -match '(?i)(?:^|/)(?:COPYING|COPYRIGHT|LICEN[CS]E|NOTICE|AUTHORS)(?:[./_-]|$)' })
        Status = "Source archive referenced by the container build log; final DLL inclusion and nested-source completeness require review"
    }
}
$inventoryPath = Join-Path $directory "selected-source-inventory.json"
$inventory | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $inventoryPath -Encoding utf8
Write-Output "Inventoried $($sourceNames.Count) source archives: $inventoryPath"
Write-Output "Archives with Git HEAD evidence: $(@($inventory | Where-Object { $_.ArchivedGitRevisions.Count -gt 0 }).Count)"
Write-Output "No source code or build scripts were executed."
