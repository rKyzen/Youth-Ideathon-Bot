; Youth Ideathon Bot - Inno Setup 7 Installer Script
; Builds a lightweight setup EXE that installs dependencies during setup
; instead of shipping 50+ MB self-contained PyInstaller executables.

#define AppName "Youth Ideathon Bot"
#define AppVersion "2.1.0"
#define AppPublisher "Youth Ideathon Team"
#define AppURL "https://youthideathon.in"
#define PythonVersion "3.12.10"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=YouthIdeathon_Setup_v{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico
AppCopyright=Copyright (C) 2026 Youth Ideathon Team
DisableStartupPrompt=yes
DisableDirPage=no
DisableProgramGroupPage=yes
DisableReadyMemo=no
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Application source and data (small)
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "submit_ideas.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "Idea.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "ideas.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "ideas.csv"; DestDir: "{app}"; Flags: ignoreversion
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; Downloaded only when no Python 3.10+ is detected (keeps the setup EXE small)
Source: "https://www.python.org/ftp/python/{#PythonVersion}/python-{#PythonVersion}-amd64.exe"; DestDir: "{tmp}"; DestName: "python-setup.exe"; ExternalSize: 27000000; Flags: external download ignoreversion; Check: NeedsPython

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Install / Repair Dependencies"; Filename: "{app}\install_deps.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; 1. Install Python silently if it was missing
Filename: "{tmp}\python-setup.exe"; Parameters: "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0"; StatusMsg: "Installing Python {#PythonVersion}..."; Flags: waituntilterminated; Check: NeedsPython
; 2. Install Python packages + Playwright Chromium + verify Chrome
Filename: "{app}\install_deps.bat"; StatusMsg: "Installing Python dependencies and Playwright Chromium..."; Flags: waituntilterminated
; 3. Optional launch after setup
Filename: "{app}\run_app.bat"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove runtime artefacts but leave any user-added files in the install folder
Type: filesandordirs; Name: "{app}\screenshots"
Type: filesandordirs; Name: "{app}\chrome_user_data"
Type: filesandordirs; Name: "{app}\ai_window_profile"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\automation.log"
Type: files; Name: "{app}\submission_log.csv"

[Code]
var
  PythonInstalled: Boolean;

function NeedsPython(): Boolean;
begin
  Result := not PythonInstalled;
end;

function CheckPython(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{win}\py.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python314\python.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python313\python.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python312\python.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python311\python.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python310\python.exe')) or
    FileExists('C:\Python314\python.exe') or
    FileExists('C:\Python313\python.exe') or
    FileExists('C:\Python312\python.exe') or
    FileExists('C:\Python311\python.exe') or
    FileExists('C:\Python310\python.exe');
end;

function CheckChrome(): Boolean;
var
  ChromePath: String;
begin
  Result := False;

  ChromePath := ExpandConstant('{pf}\Google\Chrome\Application\chrome.exe');
  if FileExists(ChromePath) then
  begin
    Result := True;
    Exit;
  end;

  ChromePath := ExpandConstant('{pf32}\Google\Chrome\Application\chrome.exe');
  if FileExists(ChromePath) then
  begin
    Result := True;
    Exit;
  end;

  ChromePath := ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe');
  if FileExists(ChromePath) then
  begin
    Result := True;
    Exit;
  end;
end;

function InitializeSetup(): Boolean;
begin
  PythonInstalled := CheckPython();

  if not PythonInstalled then
    MsgBox('Python 3.10+ was not detected.' + #13#10#13#10 +
           'Setup will download and install Python automatically so the app can run.',
           mbInformation, MB_OK);

  if not CheckChrome() then
    MsgBox('Google Chrome was not detected.' + #13#10#13#10 +
           'The app will fall back to Playwright Chromium, which Setup installs automatically.',
           mbInformation, MB_OK);

  Result := True;
end;

procedure CreateBatchFiles();
var
  Launcher: String;
  Deps: String;
begin
  Launcher :=
    '@echo off' + #13#10 +
    'title Youth Ideathon Bot' + #13#10 +
    'cd /d "%~dp0"' + #13#10 +
    'echo Starting Youth Ideathon Bot...' + #13#10 +
    'echo.' + #13#10 +
    'py -3 --version >nul 2>nul' + #13#10 +
    'if not errorlevel 1 (' + #13#10 +
    '    py -3 app.py' + #13#10 +
    '    goto :end' + #13#10 +
    ')' + #13#10 +
    'python --version >nul 2>nul' + #13#10 +
    'if not errorlevel 1 (' + #13#10 +
    '    python app.py' + #13#10 +
    '    goto :end' + #13#10 +
    ')' + #13#10 +
    'python3 --version >nul 2>nul' + #13#10 +
    'if not errorlevel 1 (' + #13#10 +
    '    python3 app.py' + #13#10 +
    '    goto :end' + #13#10 +
    ')' + #13#10 +
    'echo ERROR: Python 3.10+ was not found.' + #13#10 +
    'echo Install it from https://www.python.org/downloads/ and try again.' + #13#10 +
    'pause' + #13#10 +
    ':end' + #13#10;
  SaveStringToFile(ExpandConstant('{app}\run_app.bat'), Launcher, False);

  Deps :=
    '@echo off' + #13#10 +
    'setlocal' + #13#10 +
    'title Youth Ideathon - Dependency Installer' + #13#10 +
    'cd /d "%~dp0"' + #13#10 +
    'echo ============================================================' + #13#10 +
    'echo  Youth Ideathon Bot - Installing Dependencies' + #13#10 +
    'echo ============================================================' + #13#10 +
    'echo.' + #13#10 +
    'set "PYCMD="' + #13#10 +
    'py -3 --version >nul 2>nul' + #13#10 +
    'if not errorlevel 1 set "PYCMD=py -3"' + #13#10 +
    'if not defined PYCMD (' + #13#10 +
    '    python --version >nul 2>nul' + #13#10 +
    '    if not errorlevel 1 set "PYCMD=python"' + #13#10 +
    ')' + #13#10 +
    'if not defined PYCMD (' + #13#10 +
    '    python3 --version >nul 2>nul' + #13#10 +
    '    if not errorlevel 1 set "PYCMD=python3"' + #13#10 +
    ')' + #13#10 +
    'if not defined PYCMD (' + #13#10 +
    '    echo ERROR: Python 3.10+ was not found.' + #13#10 +
    '    echo Install Python from https://www.python.org/downloads/ and run this file again.' + #13#10 +
    '    ping -n 8 127.0.0.1 >nul' + #13#10 +
    '    exit /b 1' + #13#10 +
    ')' + #13#10 +
    'echo Using: %PYCMD%' + #13#10 +
    'echo.' + #13#10 +
    'echo [1/3] Installing Python packages...' + #13#10 +
    '%PYCMD% -m pip --version >nul 2>nul' + #13#10 +
    'if errorlevel 1 %PYCMD% -m ensurepip --upgrade' + #13#10 +
    '%PYCMD% -m pip install --upgrade -r requirements.txt' + #13#10 +
    'if errorlevel 1 echo WARNING: Some Python packages failed to install.' + #13#10 +
    'echo.' + #13#10 +
    'echo [2/3] Installing Playwright Chromium (one-time download)...' + #13#10 +
    '%PYCMD% -m playwright install chromium' + #13#10 +
    'if errorlevel 1 echo WARNING: Playwright Chromium installation failed.' + #13#10 +
    'echo.' + #13#10 +
    'echo [3/3] Checking for Google Chrome...' + #13#10 +
    'if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (' + #13#10 +
    '    echo Chrome found: %ProgramFiles%\Google\Chrome\Application\chrome.exe' + #13#10 +
    ') else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (' + #13#10 +
    '    echo Chrome found: %ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe' + #13#10 +
    ') else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (' + #13#10 +
    '    echo Chrome found: %LocalAppData%\Google\Chrome\Application\chrome.exe' + #13#10 +
    ') else (' + #13#10 +
    '    echo Chrome not found - the app will use Playwright Chromium instead.' + #13#10 +
    ')' + #13#10 +
    'echo.' + #13#10 +
    'echo ============================================================' + #13#10 +
    'echo  Dependency installation finished.' + #13#10 +
    'echo ============================================================' + #13#10 +
    'ping -n 4 127.0.0.1 >nul' + #13#10 +
    'endlocal' + #13#10;
  SaveStringToFile(ExpandConstant('{app}\install_deps.bat'), Deps, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    CreateBatchFiles();
end;
