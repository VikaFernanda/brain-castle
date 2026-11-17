<#
Portable build: venv -> requirements -> tests -> PyInstaller (onedir, windowed) -> zip.
Result: dist\BrainCastle\BrainCastle.exe and dist\BrainCastle-portable-<version>.zip
Run from anywhere:  powershell -ExecutionPolicy Bypass -File build.ps1   (add -SkipTests to skip pytest)
#>
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Run-Native([scriptblock]$Cmd) {
    & $Cmd
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $Cmd" }
}

$venv = "app\.venv"
$py = "$venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating venv..."
    Run-Native { py -3.12 -m venv $venv }
}
Write-Host "Installing requirements..."
Run-Native { & $py -m pip install --disable-pip-version-check -q -r app\requirements.txt -r app\requirements-dev.txt }

if (-not $SkipTests) {
    Write-Host "Running tests..."
    Run-Native { & $py -m pytest app\tests -q }
}

$version = (& $py -c "import sys; sys.path.insert(0, 'app'); import brain_castle; print(brain_castle.__version__)").Trim()
if (-not $version) { throw "Could not read the version." }
Write-Host "Building Brain Castle $version..."

Run-Native { & $py app\tools\make_version_info.py build\version_info.txt }
if (Test-Path dist\BrainCastle) { Remove-Item dist\BrainCastle -Recurse -Force }
Run-Native { & $py -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller app\packaging\BrainCastle.spec }

$exe = "dist\BrainCastle\BrainCastle.exe"
if (-not (Test-Path $exe)) { throw "Build failed: $exe not found." }

$zip = "dist\BrainCastle-portable-$version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path dist\BrainCastle -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Done: $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB)"
