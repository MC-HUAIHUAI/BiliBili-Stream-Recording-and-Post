; ============================================================
; Inno Setup 脚本 —— 生成 exe 安装包 (setup.exe)
; 依赖: 先运行 packaging\build.ps1 生成 dist\BiliStreamRecorder.exe
; 用法: 用 Inno Setup 打开本脚本编译，或命令行:
;   ISCC.exe /Qp packaging\bili_recorder.iss
; 注意: 本文件需以 UTF-8 (带 BOM) 保存，否则中文会乱码。
; ============================================================

#define MyAppName "B站直播录播+自动投稿"
#define MyAppNameEn "BiliStreamRecorder"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "BiliStreamRecorder"
#define MyAppExeName "BiliStreamRecorder.exe"

[Setup]
AppId={{7E4B3A2D-1F5C-4E8A-9B2D-6C1A4E5B7D90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=BiliStreamRecorder-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
