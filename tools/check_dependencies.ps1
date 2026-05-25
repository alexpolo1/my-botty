param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"

function Write-Check {
    param(
        [string]$Status,
        [string]$Message
    )
    switch ($Status) {
        "PASS" { Write-Host "[PASS] $Message" -ForegroundColor Green }
        "WARN" { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
        "FAIL" { Write-Host "[FAIL] $Message" -ForegroundColor Red }
        default { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
    }
}

function Test-PythonImport {
    param(
        [string]$PythonExe,
        [string]$ModuleName
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    cmd /c "$PythonExe -c ""import $ModuleName""" *> $null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    return ($code -eq 0)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "=== Botty Dependency Check ===" -ForegroundColor Cyan
Write-Host "Repo: $repoRoot"

$pythonExe = $null
foreach ($candidate in @("python", "py -3")) {
    if ($candidate -eq "python") {
        cmd /c "python --version" *> $null
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "python"
            break
        }
    } else {
        cmd /c "py -3 --version" *> $null
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "py -3"
            break
        }
    }
}

if (-not $pythonExe) {
    Write-Check "FAIL" "Python not found. Install Miniforge and run install.bat."
    exit 1
}

cmd /c "$pythonExe --version" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Check "FAIL" "Python not found. Install Miniforge and run install.bat."
    exit 1
}

$pyVersion = cmd /c "$pythonExe -c ""import sys; print(sys.version)"""
Write-Check "PASS" "Python found: $pyVersion"

# Basic repo files
$requiredFiles = @(
    "config\params.ini",
    "config\game.ini",
    "run_botty.bat",
    "src\main.py"
)
foreach ($file in $requiredFiles) {
    if (Test-Path (Join-Path $repoRoot $file)) {
        Write-Check "PASS" "Found $file"
    } else {
        Write-Check "FAIL" "Missing $file"
    }
}

# Core imports needed to launch/run
$coreModules = @(
    "cv2",
    "mss",
    "numpy",
    "keyboard",
    "mouse",
    "transitions",
    "rapidfuzz",
    "discord",
    "psutil",
    "cryptography",
    "parse",
    "dataclasses_json",
    "beautifultable"
)

$failedImports = @()
foreach ($module in $coreModules) {
    if (Test-PythonImport -PythonExe $pythonExe -ModuleName $module) {
        Write-Check "PASS" "Python module '$module' import OK"
    } else {
        Write-Check "FAIL" "Python module '$module' missing/broken"
        $failedImports += $module
    }
}

# OCR dependency (important for live bot)
if (Test-PythonImport -PythonExe $pythonExe -ModuleName "tesserocr") {
    $ocrInfo = cmd /c "$pythonExe -c ""import tesserocr; print(getattr(tesserocr,'tesseract_version',lambda:'unknown')())""" 2>$null
    Write-Check "PASS" "tesserocr import OK ($ocrInfo)"
} else {
    Write-Check "FAIL" "tesserocr missing. Run install.bat in the botty repo."
    $failedImports += "tesserocr"
}

# Read d2r_path from params.ini
$paramsPath = Join-Path $repoRoot "config\params.ini"
$d2rPath = $null
try {
    $raw = Get-Content $paramsPath -ErrorAction Stop
    foreach ($line in $raw) {
        if ($line -match "^\s*d2r_path\s*=\s*(.+)\s*$") {
            $d2rPath = $Matches[1].Trim()
            break
        }
    }
} catch {
    Write-Check "WARN" "Unable to parse config\params.ini for d2r_path"
}

if ($d2rPath) {
    if (Test-Path $d2rPath) {
        Write-Check "PASS" "Configured d2r_path exists: $d2rPath"
    } else {
        Write-Check "WARN" "Configured d2r_path not found: $d2rPath"
    }
}

# Optional: print pip freeze subset
if ($VerboseOutput) {
    Write-Host "`n--- pip show (core) ---" -ForegroundColor Cyan
    foreach ($pkg in @("opencv-python","mss","numpy","discord.py","transitions","rapidfuzz","tesserocr")) {
        cmd /c "$pythonExe -m pip show $pkg" 2>$null | Select-String "Name:|Version:"
    }
}

Write-Host ""
if ($failedImports.Count -eq 0) {
    Write-Check "PASS" "Dependency check passed."
    exit 0
}

Write-Check "FAIL" "Dependency check failed. Missing/broken: $($failedImports -join ', ')"
Write-Host "Suggested fix: run install.bat from repo root, then run this check again." -ForegroundColor Yellow
exit 1
