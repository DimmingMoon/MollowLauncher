@echo off
setlocal
cd /d "%~dp0"
echo ===============================================
echo   MollowLauncher: build program and installer
echo ===============================================
echo.
echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 goto fail
echo.
echo [2/3] Building program (folder dist\MollowLauncher)...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
python tools\make_icon.py
python -m PyInstaller --noconfirm --clean --noconsole --onedir --name MollowLauncher --icon assets\icon.ico --add-data "assets;assets" main.py
if errorlevel 1 goto fail
if not exist "dist\MollowLauncher\MollowLauncher.exe" goto fail
for /f %%v in ('python -c "from launcher.version import VERSION; print(VERSION)"') do set "VER=%%v"
echo.
echo [3/3] Creating installer %VER%...
set "ISCC="
call :find
if defined ISCC goto compile
echo Inno Setup not found, trying to install it with winget...
winget install -e --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
call :find
if defined ISCC goto compile
goto noinno

:compile
"%ISCC%" "/DMyAppVersion=%VER%" installer.iss
if errorlevel 1 goto fail
echo.
echo DONE: installer_output\MollowLauncher_Setup.exe
echo Program folder: dist\MollowLauncher
pause
exit /b 0

:noinno
echo.
echo Could not find or install Inno Setup (it is needed only for the installer).
echo Download it from https://jrsoftware.org/isdl.php and run this file again.
echo The program itself is already built: dist\MollowLauncher\MollowLauncher.exe
pause
exit /b 1

:fail
echo.
echo ERROR. Copy the text above and send it to the developer.
pause
exit /b 1

:find
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0
