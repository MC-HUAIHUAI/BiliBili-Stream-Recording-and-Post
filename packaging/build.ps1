# ============================================================
# 一键打包 exe (PyInstaller, 单文件)
# 用法: 在 E:\stream_record 下执行  .\packaging\build.ps1
# 产物: dist\BiliStreamRecorder.exe
# ============================================================
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "未找到虚拟环境，先运行: python -m venv venv; .\venv\Scripts\pip install -r requirements.txt pyinstaller" -ForegroundColor Yellow
    exit 1
}

Push-Location $Root
try {
    & $VenvPython -m PyInstaller `
        --noconfirm --clean --onefile --windowed `
        --name "BiliStreamRecorder" `
        --icon "assets\icon.ico" `
        --collect-all bilibili_api `
        --collect-all streamlink `
        --collect-all httpx `
        --collect-all certifi `
        app.py

    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }
    Write-Host "`n打包完成: $Root\dist\BiliStreamRecorder.exe" -ForegroundColor Green
}
finally {
    Pop-Location
}
