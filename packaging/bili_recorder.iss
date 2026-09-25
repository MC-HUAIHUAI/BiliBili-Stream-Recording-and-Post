; ============================================================
; Inno Setup 脚本 —— 生成 exe 安装包 (setup.exe)
; 依赖: 先运行 packaging\build.ps1 生成 dist\BiliStreamRecorder-<Arch>.exe
; 用法:
;   ISCC.exe /Qp /DArch=x64 packaging\bili_recorder.iss   (64 位安装包)
;   ISCC.exe /Qp /DArch=x86 packaging\bili_recorder.iss   (32 位安装包，x86/x64 通用)
; 注意: 本文件需以 UTF-8 (带 BOM) 保存，否则中文会乱码。
; ============================================================

#define MyAppName "B站直播录播+自动投稿"
#define MyAppNameEn "BiliStreamRecorder"
#define MyAppVersion "1.4.1"
#define MyAppPublisher "BiliStreamRecorder"

#ifndef Arch
  #define Arch "x64"
#endif

#if Arch == "x86"
  #define MyAppExeSrc "BiliStreamRecorder-x86.exe"
  #define ArchSuffix "-x86"
#else
  #define MyAppExeSrc "BiliStreamRecorder-x64.exe"
  #define ArchSuffix "-x64"
#endif

#define MyAppInstalledExe "BiliStreamRecorder.exe"

[Setup]
AppId={{7E4B3A2D-1F5C-4E8A-9B2D-6C1A4E5B7D90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=BiliStreamRecorder-Setup-{#MyAppVersion}{#ArchSuffix}
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
#if Arch == "x64"
ArchitecturesAllowed=x64
#endif

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeSrc}"; DestDir: "{app}"; DestName: "{#MyAppInstalledExe}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppInstalledExe}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppInstalledExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppInstalledExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
