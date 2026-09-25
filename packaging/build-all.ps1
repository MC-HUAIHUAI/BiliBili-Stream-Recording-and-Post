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
    & $InnoISCC /Qp "/DArch=$Arch" (Join-Path $Packaging "bili_recorder.iss")
}

function Build-Wix([string]$Arch) {
    if (-not $WixBin) { Write-Host "跳过 WiX ($Arch)：未找到 candle.exe/light.exe" -ForegroundColor Yellow; return }
    $candle = Join-Path $WixBin "candle.exe"
    $light = Join-Path $WixBin "light.exe"
    $obj = Join-Path $Root "dist\obj"
    New-Item -ItemType Directory -Path $obj -Force | Out-Null
    Write-Host "`n==== 构建 $Arch MSI ====" -ForegroundColor Cyan
    & $candle "-dArch=$Arch" (Join-Path $Packaging "bili_recorder.wxs") -o "$obj\" | Out-Null
    & $light "$obj\bili_recorder.wixobj" -o "$Root\dist\BiliStreamRecorder-Setup-1.4.0-$Arch.msi" | Out-Null
    Remove-Item "$obj" -Recurse -Force -ErrorAction SilentlyContinue
}

Build-Exe "x86"
Build-Exe "x64"
Build-Inno "x86"
Build-Inno "x64"
Build-Wix "x86"
Build-Wix "x64"

Write-Host "`n全部构建完成，产物位于: $Root\dist" -ForegroundColor Green
