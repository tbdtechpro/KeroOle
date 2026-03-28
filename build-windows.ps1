#Requires -Version 5.0
<#
.SYNOPSIS
    Builds the KeroOle Windows executable using PyInstaller.
    Run from the repo root in PowerShell:  .\build-windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step { param($msg) Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }

# ── 1. Detect Python ≥ 3.10 ──────────────────────────────────────────────────
Write-Step "Checking for Python..."
$pythonCmd = $null
$minVersion = [version]"3.10"

foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            if ([version]$Matches[1] -ge $minVersion) {
                $pythonCmd = $cmd
                Write-Ok "Found: $ver"
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Warn "Python $minVersion+ not found."
    $install = Read-Host "Install Python 3.13 via winget? [Y/N]"
    if ($install -notin @("Y","y")) {
        Write-Host "Aborting. Install Python manually: https://python.org" -ForegroundColor Red
        exit 1
    }
    Write-Step "Installing Python via winget..."
    winget install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
    # Refresh PATH in this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $pythonCmd = "python"
    Write-Ok "Python installed."
}

# ── 2. Create / reuse .build-venv ─────────────────────────────────────────────
$venvDir    = Join-Path $ScriptDir ".build-venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating build venv at .build-venv..."
    & $pythonCmd -m venv $venvDir
    Write-Ok "Venv created."
} else {
    Write-Step "Reusing existing .build-venv."
}

# ── 3. Install dependencies ────────────────────────────────────────────────────
Write-Step "Installing dependencies into build venv..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet `
    pyinstaller `
    "lxml>=4.9.0" `
    "requests>=2.28.0" `
    browser_cookie3 `
    "pyperclip>=1.8.0" `
    "colorama>=0.4.6" `
    "git+https://github.com/tbdtechpro/bubblepy" `
    "git+https://github.com/tbdtechpro/pygloss"
Write-Ok "Dependencies installed."

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
Write-Step "Building with PyInstaller..."
Set-Location $ScriptDir
& $venvPython -m PyInstaller KeroOle.spec --distpath dist --noconfirm
Write-Ok "Build complete."

# ── 5. Move output to repo root ───────────────────────────────────────────────
Write-Step "Moving output to repo root..."

$exeSrc = Join-Path $ScriptDir "dist\KeroOle\KeroOle.exe"
$exeDst = Join-Path $ScriptDir "KeroOle.exe"
$intSrc = Join-Path $ScriptDir "dist\KeroOle\_internal"
$intDst = Join-Path $ScriptDir "_internal"

if (Test-Path $exeDst) { Remove-Item $exeDst -Force }
if (Test-Path $intDst) { Remove-Item $intDst -Recurse -Force }

Move-Item $exeSrc $exeDst
Move-Item $intSrc $intDst
Write-Ok "Moved KeroOle.exe and _internal\ to repo root."

# ── 6. Clean up ───────────────────────────────────────────────────────────────
Write-Step "Cleaning up..."
Remove-Item (Join-Path $ScriptDir "dist")  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $ScriptDir "build") -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok "Cleaned up dist\ and build\."

# ── 7. Optional PATH addition ─────────────────────────────────────────────────
$addPath = Read-Host "Add KeroOle to your user PATH? [Y/N]"
if ($addPath -in @("Y","y")) {
    $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$ScriptDir*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$currentPath;$ScriptDir", "User")

        # Broadcast WM_SETTINGCHANGE so open terminals pick up the new PATH
        $sig = '[DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);'
        $type = Add-Type -MemberDefinition $sig -Name WinMsg -Namespace Win32 -PassThru
        $result = [UIntPtr]::Zero
        $type::SendMessageTimeout([IntPtr]0xffff, 0x1a, [UIntPtr]::Zero, "Environment", 2, 5000, [ref]$result) | Out-Null

        Write-Ok "Added to PATH. Restart your terminal to use 'KeroOle' from anywhere."
    } else {
        Write-Ok "Already in PATH — no change needed."
    }
}

Write-Host ""
Write-Ok "Done!  Run .\KeroOle.exe to launch KeroOle."
