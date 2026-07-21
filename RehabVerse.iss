; RehabVerse Installer Script (Inno Setup)
; ==========================================
; Built to match RehabVerse Installer Requirements Specification v1.0.0.
;
; BEFORE COMPILING:
;   1. Set MyAppSourceDir below to your verified RehabVerse folder's
;      actual path (the one that already works end-to-end).
;   2. Generate your own AppId - open this file in the Inno Setup IDE,
;      Tools > Generate GUID, paste the result in place of the
;      placeholder below. Keep this GUID the same across future
;      versions of RehabVerse (that's what lets Windows treat a new
;      installer as an UPDATE rather than a separate second install).

#define MyAppName "RehabVerse"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ipsita Jain"
#define MyAppDescription "Gamified Rehabilitation Game"
#define MyAppSourceDir  "D:\RehabVerse"

[Setup]
AppId={64604538-ED00-441F-A903-14225178E5C7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}

; --- Per-user install, no admin/UAC (req. #2, #18) --- ;
DefaultDirName={localappdata}\{#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; --- Wizard pages (req. #3) --- ;
; Welcome, Choose Install Folder, Select Tasks, Installing, Finish only.
; Omitting LicenseFile/InfoBeforeFile/InfoAfterFile already skips those
; pages automatically - no separate directive needed for that. This one
; directive additionally removes the "Select Start Menu Folder" page,
; which isn't in the requested page list.
DisableProgramGroupPage=yes
WizardStyle=modern

; --- Icon (req. #8) --- ;
SetupIconFile={#MyAppSourceDir}\assets\RehabVerse.ico
UninstallDisplayIcon={app}\assets\RehabVerse.ico

; --- Output (req. #19) --- ;
OutputDir=Output
OutputBaseFilename=RehabVerseSetup

; --- Compression (req. #11) --- ;
Compression=lzma2
SolidCompression=yes

[Tasks]
; Checked by default (req. #4) - Inno tasks default to checked unless
; explicitly marked "unchecked", so no extra flag is needed here.
Name: "desktopicon"; Description: "Create Desktop Shortcut"

[Files]
; Whole folders, copied as-is, preserving structure exactly (req. #9,
; #14, #15, #16). Excludes match req. #10 precisely: dev-only folders,
; __pycache__ wherever it appears, and stray/compiled Python files.
Source: "{#MyAppSourceDir}\app\*"; DestDir: "{app}\app"; \
    Excludes: "__pycache__\*,*.pyc,*.pyo,tempCodeRunnerFile.py"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#MyAppSourceDir}\games\*"; DestDir: "{app}\games"; \
    Excludes: "__pycache__\*,*.pyc,*.pyo,tempCodeRunnerFile.py"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#MyAppSourceDir}\python\*"; DestDir: "{app}\python"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#MyAppSourceDir}\assets\*"; DestDir: "{app}\assets"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; Individual files (req. #9, #17 - .env copied unmodified, no [Code]
; section touches it before or after copying).
Source: "{#MyAppSourceDir}\.env"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#MyAppSourceDir}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu (req. #5) + desktop shortcut (req. #4), both launching
; pythonw.exe main.py with working directory {app}\app (req. #6, #7,
; #13) - NOT python.exe, NOT a .bat file, per spec. All shortcuts use
; the custom icon (req. #8).
Name: "{userprograms}\{#MyAppName}"; \
    Filename: "{app}\python\pythonw.exe"; \
    Parameters: "main.py"; \
    WorkingDir: "{app}\app"; \
    IconFilename: "{app}\assets\RehabVerse.ico"

Name: "{userprograms}\Uninstall {#MyAppName}"; \
    Filename: "{uninstallexe}"; \
    IconFilename: "{app}\assets\RehabVerse.ico"

Name: "{userdesktop}\{#MyAppName}"; \
    Filename: "{app}\python\pythonw.exe"; \
    Parameters: "main.py"; \
    WorkingDir: "{app}\app"; \
    IconFilename: "{app}\assets\RehabVerse.ico"; \
    Tasks: desktopicon

[Run]
; Checked by default (req. #6) - "postinstall" without "unchecked" is
; checked by default. Same launch command as the shortcuts above, for
; consistency - this is exactly what "Launch RehabVerse" ends up doing
; either way.
Filename: "{app}\python\pythonw.exe"; \
    Parameters: "main.py"; \
    WorkingDir: "{app}\app"; \
    Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent
