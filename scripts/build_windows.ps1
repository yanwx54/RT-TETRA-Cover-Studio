param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$SpecPath = Join-Path $ProjectDir "packaging\rt_tetra_cover_studio.spec"
$OutputExe = Join-Path $ProjectDir "dist\RT-TETRA-Cover-Studio\RT-TETRA-Cover-Studio.exe"

Push-Location $ProjectDir
try {
    & $Python -m pip install -r requirements.txt
    & $Python -m compileall src tests scripts
    & $Python -m unittest discover -s tests
    & $Python -m PyInstaller --clean --noconfirm $SpecPath

    if (-not (Test-Path $OutputExe)) {
        throw "Build finished but executable was not found: $OutputExe"
    }

    Write-Host "Build output:"
    Write-Host $OutputExe
}
finally {
    Pop-Location
}
