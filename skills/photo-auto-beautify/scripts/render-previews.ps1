param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [Parameter(Mandatory = $true)][string]$PreviewDir,
    [int]$MaxEdge = 900,
    [string]$RawmakaseExe
)

$ErrorActionPreference = 'Stop'
if (-not $RawmakaseExe) {
    $RawmakaseExe = Join-Path $env:LOCALAPPDATA 'Programs\RAWmakase\rawmakase.exe'
}
if (-not (Test-Path $RawmakaseExe)) { throw "RAWmakase not found: $RawmakaseExe" }

New-Item -ItemType Directory -Path $PreviewDir -Force | Out-Null
$exts = @('.rw2', '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.pef', '.srw', '.raw')
$files = Get-ChildItem -LiteralPath $InputDir -File |
    Where-Object { $exts -contains $_.Extension.ToLower() -and $_.BaseName -notmatch '-rt\d*$' } |
    Sort-Object Name

$ok = 0
$failed = 0
foreach ($file in $files) {
    $out = Join-Path $PreviewDir ($file.BaseName + '.jpg')
    & $RawmakaseExe render $file.FullName $out --max-edge $MaxEdge --overwrite 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $out)) {
        $ok++
    }
    else {
        Write-Warning "preview failed: $($file.Name)"
        $failed++
    }
}

Write-Host "previews: ok=$ok failed=$failed -> $PreviewDir"
if ($failed -gt 0) { exit 1 }
