; Установщик MollowLauncher (Inno Setup 6). Собирается build_installer.bat или GitHub Actions (.github/workflows/release.yml)
#ifndef MyAppVersion
  #define MyAppVersion "2.0.1"
#endif
#define MyAppName "MollowLauncher"
#define MyAppPublisher "Mollow"
#define MyAppExe "MollowLauncher.exe"

[Setup]
AppId={{B7E2C4A1-5D3F-4E8A-9C61-2F0A7D9B3E54}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
DefaultDirName=C:\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
UsePreviousAppDir=yes
WizardImageFile=assets\wizard_big.bmp
WizardSmallImageFile=assets\wizard_small.bmp
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=MollowLauncher_Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; при обновлении закрываем запущенный лаунчер и ставим поверх
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[InstallDelete]
; остатки старой версии (один exe) при обновлении
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\MollowLauncher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Игровые данные (сборки, миры, моды, аккаунты) лежат в %APPDATA%\.MollowLauncher и по умолчанию остаются.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
  begin
    DataDir := ExpandConstant('{userappdata}\.MollowLauncher');
    if DirExists(DataDir) then
      if MsgBox('Удалить также игровые данные (сборки, миры, моды, аккаунты)?' + #13#10 + DataDir + #13#10#13#10 +
                'Это действие необратимо.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
