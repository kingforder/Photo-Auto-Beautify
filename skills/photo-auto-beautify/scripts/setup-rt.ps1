param(
    [string]$InstallDir,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$url = 'https://github.com/RawTherapee/RawTherapee/releases/download/5.13/RawTherapee_5.13_win64_x86_64_release.zip'
$expected = 'ba29d23f3f12097c925bdab6d80e831a84ed3a88a81ce94606e4dcc796fa87ee'
$innerName = 'RawTherapee_5.13_win64_x86_64_release'

if (-not $InstallDir) {
    $InstallDir = Join-Path $PSScriptRoot '..\..\rt-5.13'
}
$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$target = Join-Path $InstallDir $innerName
$exe = Join-Path $target 'rawtherapee-cli.exe'
if ((Test-Path $exe) -and -not $Force) {
    Write-Host "RawTherapee already installed: $target"
    exit 0
}

$zip = Join-Path $env:TEMP 'RawTherapee_5.13_win64_x86_64_release.zip'
Write-Host "Downloading RawTherapee 5.13 portable..."
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
if ($hash -ne $expected) {
    Remove-Item -LiteralPath $zip -Force
    throw "SHA256 mismatch: got $hash expected $expected"
}

$tmp = Join-Path $env:TEMP ('rt-extract-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
try {
    Expand-Archive -LiteralPath $zip -DestinationPath $tmp -Force
    $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
    if (-not $inner) { throw 'Unexpected RawTherapee archive layout.' }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    Copy-Item $inner.FullName $target -Recurse -Force
    Write-Host "Installed to: $target"
}
finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
}
