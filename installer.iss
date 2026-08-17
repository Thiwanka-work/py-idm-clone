[Setup]
AppName=EasyDownloader
AppVersion=1.0
AppPublisher=Thiwanka
AppPublisherURL=https://github.com/Thiwanka-work/py-idm-clone
LicenseFile=PrivacyPolicy.txt
DisableDirPage=no
DefaultDirName={autopf}\EasyDownloader
DefaultGroupName=EasyDownloader
OutputDir=Output
OutputBaseFilename=EasyDownloader_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=app\icon.ico
UninstallDisplayIcon={app}\EasyDownloader.exe
UninstallDisplayName=EasyDownloader

[Files]
Source: "app\dist\EasyDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\EasyDownloader"; Filename: "{app}\EasyDownloader.exe"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\EasyDownloader"; Filename: "{app}\EasyDownloader.exe"; IconFilename: "{app}\icon.ico"

[Run]
Filename: "{app}\EasyDownloader.exe"; Description: "Launch EasyDownloader"; Flags: nowait postinstall skipifsilent
