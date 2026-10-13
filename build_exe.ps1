<#
  Builds dist\AIMeetingCompanion\AIMeetingCompanion.exe (windowed: no console, taskbar button or tray icon).
    .\build_exe.ps1                  GPU libraries + Tesseract bundled when found (large folder)
    .\build_exe.ps1 -NoGpu           smaller build; speech recognition runs on the CPU
    .\build_exe.ps1 -Tesseract none  don't bundle Tesseract
    .\build_exe.ps1 -IncludeEnv      also copy .env (contains your API key)
#>
param(
    [switch]$NoGpu,
    [switch]$IncludeEnv,
    [string]$Tesseract = "auto",
    [string]$Icon = ""
)
# PyInstaller writes its normal progress to stderr. With "Stop", PowerShell would treat the first such
# line as a failure whenever output is redirected or captured, so success is judged by the exit code.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$script = Join-Path $PSScriptRoot "scripts\build_exe.py"

$argsList = @($script, "--tesseract-dir", $Tesseract)
if ($NoGpu)      { $argsList += "--no-gpu" }
if ($IncludeEnv) { $argsList += "--include-env" }
if ($Icon)       { $argsList += @("--icon", $Icon) }

& $py @argsList
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Host "Build FAILED (exit code $code)" -ForegroundColor Red }
exit $code
