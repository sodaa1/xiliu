# Archive loose development logs without overwriting previous runs.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$logRoot = Join-Path $projectRoot 'logs'
$moved = 0
$blocked = 0
foreach ($sourceDirectory in @($projectRoot, (Join-Path $projectRoot '.preview'))) {
    if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) { continue }
    $category = if ($sourceDirectory -eq $projectRoot) { 'development' } else { 'preview' }
    $destinationDirectory = Join-Path $logRoot $category
    foreach ($file in Get-ChildItem -LiteralPath $sourceDirectory -Filter '*.log' -File -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        $destination = [IO.Path]::GetFullPath((Join-Path $destinationDirectory $file.Name))
        if (-not $destination.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Log destination is outside the project.'
        }
        if (Test-Path -LiteralPath $destination) {
            $archiveName = '{0}.{1}.log' -f $file.BaseName, [guid]::NewGuid().ToString('N')
            $destination = Join-Path $destinationDirectory $archiveName
        }
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
        try {
            Move-Item -LiteralPath $file.FullName -Destination $destination -ErrorAction Stop
            $moved++
        } catch {
            $blocked++
            Write-Warning "Unable to move $($file.Name); stop its writer and retry."
        }
    }
}
Write-Output "Archived logs: $moved; blocked: $blocked"
if ($blocked) { exit 1 }
