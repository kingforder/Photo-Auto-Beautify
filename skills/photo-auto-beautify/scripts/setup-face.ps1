param(
    [string]$DepsDir,
    [string]$ModelPath
)

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path $PSScriptRoot -Parent
if (-not $DepsDir) { $DepsDir = Join-Path $skillRoot '..\..\face-deps' }
if (-not $ModelPath) { $ModelPath = Join-Path $skillRoot 'assets\models\face_detection_yunet_2023mar.onnx' }
$DepsDir = [System.IO.Path]::GetFullPath($DepsDir)
$ModelPath = [System.IO.Path]::GetFullPath($ModelPath)
$py = if ($env:PYTHON) { $env:PYTHON } else { 'python' }

New-Item -ItemType Directory -Path $DepsDir -Force | Out-Null
$env:PYTHONPATH = $DepsDir
$hasCv2 = $false
& $py -c "import cv2" 2>$null
if ($LASTEXITCODE -eq 0) { $hasCv2 = $true }
$hasHeif = $false
& $py -c "import pillow_heif" 2>$null
if ($LASTEXITCODE -eq 0) { $hasHeif = $true }

if (-not $hasCv2 -or -not $hasHeif) {
    Write-Host 'Installing opencv-python-headless + pillow-heif into the skill dependency folder...'
    & $py -m pip install --target $DepsDir --upgrade opencv-python-headless pillow-heif
    if ($LASTEXITCODE -ne 0) {
        throw 'pip install failed. Install opencv-python-headless + pillow-heif + numpy + Pillow, or set PYTHON/--DepsDir.'
    }
}

if (-not (Test-Path $ModelPath)) {
    New-Item -ItemType Directory -Path (Split-Path $ModelPath -Parent) -Force | Out-Null
    $url = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
    Write-Host 'Downloading YuNet face model...'
    Invoke-WebRequest -Uri $url -OutFile $ModelPath -UseBasicParsing
}

$hash = (Get-FileHash -LiteralPath $ModelPath -Algorithm SHA256).Hash
if ($hash -ne '8F2383E4DD3CFBB4553EA8718107FC0423210DC964F9F4280604804ED2552FA4') {
    throw "YuNet model SHA256 mismatch: $hash"
}

Write-Host "face deps: $DepsDir"
Write-Host "face model: $ModelPath"
