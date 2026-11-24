; Inno Setup Script for YouTube Downloader Pro
; Download Inno Setup free: https://jrsoftware.org/isinfo.php
; To build installer: Open this .iss file in Inno Setup Compiler -> Build -> Compile

#define AppName      "YouTube Downloader Pro"
#define AppVersion   "2.1.0"
#define AppPublisher "DevSajjadAli"
#define AppURL       "https://github.com/DevSajjadAli/youtube-downloader-gui"
#define AppExeName   "YouTubeDownloaderPro.exe"
#define AppID        "{A8B3C2D1-E4F5-6789-ABCD-EF1234567890}"

[Setup]
AppId={#AppID}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\YouTubeDownloaderPro
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=dist
OutputBaseFilename=YouTubeDownloaderPro-Setup-v{#AppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} - YouTube Video & Playlist Downloader
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";     Description: "{cm:CreateDesktopIcon}";     GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon";   Description: "Create a Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; The main bundled EXE
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Optional: also include assets folder for icons/resources
Source: "assets\icon.ico";      DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\icon.png";      DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist
Source: "assets\logo.png";      DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist
Source: "assets\logo_small.png"; DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Uninstall {#AppName}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Optional: Check if app is already running and prompt to close it
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
