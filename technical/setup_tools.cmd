@echo off
rem Installs the Python packages and .NET runtime used to rebuild the patch.
rem Everything stays inside technical\tools. Double-click to run.
cd /d "%~dp0tools"
set LOG=%CD%\setup.log
echo Started %DATE% %TIME% > "%LOG%"

echo Installing Python packages...
python\python.exe -m pip install --disable-pip-version-check --no-warn-script-location -r ..\requirements.txt >> "%LOG%" 2>&1
echo pip exit code: %ERRORLEVEL%
echo pip exit code: %ERRORLEVEL% >> "%LOG%"

echo Downloading .NET 8 runtime...
curl.exe -L --fail -o _downloads\dotnet.zip https://aka.ms/dotnet/8.0/dotnet-runtime-win-x64.zip >> "%LOG%" 2>&1
echo curl exit code: %ERRORLEVEL%
echo curl exit code: %ERRORLEVEL% >> "%LOG%"

if not exist dotnet mkdir dotnet
tar.exe -xf _downloads\dotnet.zip -C dotnet >> "%LOG%" 2>&1
echo tar exit code: %ERRORLEVEL%
echo tar exit code: %ERRORLEVEL% >> "%LOG%"

echo Finished %DATE% %TIME% >> "%LOG%"
echo.
echo Done. Results are in %LOG%
pause
