param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [string]$OutputDir,
    [string]$Suffix = '-rt2',
    [ValidateSet('Low', 'Medium', 'High')][string]$IsoProfile = 'Low',
    [string]$LookProfile,
    [string]$RtRoot,
    [int]$Quality = 92,
    [switch]$ProfileOnly,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

if (-not $RtRoot) {
    $candidates = @(
        (Join-Path $PSScriptRoot '..\..\rt-5.13\RawTherapee_5.13_win64_x86_64_release'),
        (Join-Path $PSScriptRoot '..\rt-5.13\RawTherapee_5.13_win64_x86_64_release')
    )
    $RtRoot = $candidates | Where-Object { Test-Path (Join-Path $_ 'rawtherapee-cli.exe') } | Select-Object -First 1
}
if (-not $RtRoot) { throw 'RawTherapee not found; pass -RtRoot or set RT_ROOT.' }

$exe = Join-Path $RtRoot 'rawtherapee-cli.exe'
$profile = Join-Path $RtRoot "profiles\Auto-Matched Curve - ISO $IsoProfile.pp3"
if (-not (Test-Path $exe)) { throw "RawTherapee CLI not found: $exe" }
if (-not (Test-Path $profile)) { throw "Profile not found: $profile" }
if ($LookProfile -and -not (Test-Path $LookProfile)) {
    $alt = Join-Path (Split-Path $PSScriptRoot -Parent) $LookProfile
    if (Test-Path $alt) { $LookProfile = $alt }
}
if ($LookProfile -and -not (Test-Path $LookProfile)) { throw "Look profile not found: $LookProfile" }
if (-not $OutputDir) { $OutputDir = $InputDir }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# RawTherapee cannot reliably write non-ASCII or long paths (e.g. Chinese folder names).
# Render to a short ASCII staging folder, then copy into place.
$staging = Join-Path $env:TEMP 'rtb'
if (Test-Path $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$exts = @('.rw2', '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.pef', '.srw', '.jpg', '.jpeg', '.tif', '.tiff')
$files = Get-ChildItem -LiteralPath $InputDir -File |
    Where-Object { $exts -contains $_.Extension.ToLower() -and $_.BaseName -notmatch '-rt\d*$' } |
    Sort-Object Name

$ok = 0
$skipped = 0
$failed = 0
try {
    foreach ($file in $files) {
        $dest = Join-Path $OutputDir ($file.BaseName + $Suffix + '.jpg')
        if ((Test-Path -LiteralPath $dest) -and -not $Overwrite) {
            Write-Host "skip  $($file.Name)"
            $skipped++
            continue
        }

        $tmp = Join-Path $staging ($file.BaseName + $Suffix + '.jpg')
        $rtArgs = @('-o', $tmp)
        if (-not $ProfileOnly) { $rtArgs += @('-p', $profile) }
        if ($LookProfile) { $rtArgs += @('-p', $LookProfile) }
        $rtArgs += @("-j$Quality", '-Y', '-c', $file.FullName)

        & $exe @rtArgs 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $tmp)) {
            Copy-Item -LiteralPath $tmp -Destination $dest -Force
            Write-Host "ok    $($file.Name) -> $(Split-Path $dest -Leaf)"
            $ok++
        }
        else {
            Write-Warning "fail  $($file.Name)"
            $failed++
        }
    }
}
finally {
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "done: ok=$ok skipped=$skipped failed=$failed output=$OutputDir"
if ($failed -gt 0) { exit 1 }
