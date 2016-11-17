@echo off
if not exist "%pydir%" (
  echo Set %%pydir%% to point to the desired python install
  exit /B 1
)
set PATH=%pydir%;%pydir%\scripts;%PATH%

if not exist "%openssldir%" (
  echo Set %%openssldir%% to point to the desired OpenSSL install
  exit /B 1
)
set PATH=%openssldir%\bin;%PATH%

if not exist "%PROGRAMFILES%\NSIS" (
    if not exist "%PROGRAMFILES(x86)%\NSIS" (
        echo Install NSIS 2.46 from http://sourceforge.net/projects/nsis/files/NSIS%202/2.46/
   exit /B 1
    )
)

where python > nul:
if ERRORLEVEL 1 (
  echo python isn't in your path, fix your path or install python 
  exit /B 1
)

where pip > nul:
if ERRORLEVEL 1 (
  echo pip isn't in your path, fix your path or install pip from https://bootstrap.pypa.io/get-pip.py
  exit /B 1
)

pip install pypiwin32
pip install cx_Freeze
pip install cx_Logging --allow-external cx-Logging --allow-unverified cx-Logging
pip install cx_PyGenLib --allow-external cx-PyGenLib --allow-unverified cx-PyGenLib
pip install psutil requests Jinja2 flask werkzeug docutils pyOpenSSL gevent appdirs packaging

echo to build ncpa:
echo python build\build_windows.py
