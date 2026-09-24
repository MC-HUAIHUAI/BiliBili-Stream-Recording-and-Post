# ============================================================
# 一键打包 exe (PyInstaller, 单文件)
# 支持 x86 / x64 双架构：
#   .\packaging\build.ps1            # 默认 x64
#   .\packaging\build.ps1 -Arch x86  # 32 位（x86/x64 通用）
# 产物: dist\BiliStreamRecorder-<Arch>.exe
# ============================================================
param(
    [ValidateSet("x86", "x64")]
    [string]$Arch = "x64"
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = if ($Arch -eq "x86") { "venv32" } else { "venv" }
$VenvPython = Join-Path $Root "$Venv\Scripts\python.exe"
$Name = "BiliStreamRecorder-$Arch"

if (-not (Test-Path $VenvPython)) {
    Write-Host "未找到虚拟环境 $Venv，请先创建并安装依赖（见 README）。" -ForegroundColor Yellow
    exit 1
}

Push-Location $Root
try {
    & $VenvPython -m PyInstaller `
        --noconfirm --clean --onefile --windowed `
        --name $Name `
        --icon "assets\icon.ico" `
        --collect-all bilibili_api `
        --collect-all streamlink `
        --collect-all httpx `
        --collect-all certifi `
        app.py

    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }
    Write-Host "`n打包完成: $Root\dist\$Name.exe" -ForegroundColor Green
}
finally {
    Pop-Location
}
