# ============================================================
# 一键构建全部产物：x86/x64 两个 exe + 4 个安装包
# 用法: .\packaging\build-all.ps1
# 依赖: Inno Setup 6 与 WiX Toolset v3 已安装/解压
# ============================================================
param(
    [string]$InnoISCC = "",
    [string]$WixBin = ""
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$Packaging = $PSScriptRoot

# 版本号统一从 version.py 读取，避免脚本 / 安装包 / 界面三处hardcode 不一致
$VersionLine = Select-String -Path (Join-Path $Root "version.py") -Pattern 'VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $VersionLine) {
    Write-Host "无法从 version.py 读取版本号。" -ForegroundColor Red
    exit 1
}
$Version = $VersionLine.Matches[0].Groups[1].Value
Write-Host "目标版本: $Version" -ForegroundColor Cyan

# 定位 Inno Setup
if (-not $InnoISCC) {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $InnoISCC = $c; break }
    }
}

# 定位 WiX
if (-not $WixBin) {
    if (Test-Path "$Root\.tools\wix314\candle.exe") { $WixBin = "$Root\.tools\wix314" }
}

function Build-Exe([string]$Arch) {
    Write-Host "`n==== 构建 $Arch exe ====" -ForegroundColor Cyan
    & (Join-Path $Packaging "build.ps1") -Arch $Arch
}

function Build-Inno([string]$Arch) {
    if (-not $InnoISCC) { Write-Host "跳过 Inno ($Arch)：未找到 ISCC.exe" -ForegroundColor Yellow; return }
    Write-Host "`n==== 构建 $Arch Inno 安装包 ====" -ForegroundColor Cyan
    & $InnoISCC /Qp "/DArch=$Arch" "/DMyAppVersion=$Version" (Join-Path $Packaging "bili_recorder.iss")
}

function Build-Wix([string]$Arch) {
    if (-not $WixBin) { Write-Host "跳过 WiX ($Arch)：未找到 candle.exe/light.exe" -ForegroundColor Yellow; return }
    $candle = Join-Path $WixBin "candle.exe"
    $light = Join-Path $WixBin "light.exe"
    $obj = Join-Path $Root "dist\obj"
    New-Item -ItemType Directory -Path $obj -Force | Out-Null
    Write-Host "`n==== 构建 $Arch MSI ====" -ForegroundColor Cyan
    # .wxs 里 File Source 写的是相对路径 ..\dist\...，必须以 packaging 为工作目录编译；
    # 否则 light 会跑到仓库上一级找 exe，报 LGHT0103: cannot find the file。
    Push-Location $Packaging
    try {
        & $candle "-dArch=$Arch" "-dMyVersion=$Version" (Join-Path $Packaging "bili_recorder.wxs") -o "$obj\" | Out-Null
        & $light "$obj\bili_recorder.wixobj" -o "$Root\dist\BiliStreamRecorder-Setup-$Version-$Arch.msi" | Out-Null
    }
    finally {
        Pop-Location
    }
    Remove-Item "$obj" -Recurse -Force -ErrorAction SilentlyContinue
}

Build-Exe "x86"
Build-Exe "x64"
Build-Inno "x86"
Build-Inno "x64"
Build-Wix "x86"
Build-Wix "x64"

Write-Host "`n全部构建完成，产物位于: $Root\dist" -ForegroundColor Green
