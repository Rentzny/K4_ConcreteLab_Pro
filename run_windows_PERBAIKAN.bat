@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title K4 ConcreteLab Pro - Windows

echo ==========================================
echo   K4 ConcreteLab Pro - START WINDOWS
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" goto INSTALL

echo Menyiapkan lingkungan Python untuk aplikasi...

REM Coba uv terlebih dahulu (cocok untuk Python yang dipasang lewat uv)
where uv >nul 2>&1
if errorlevel 1 goto TRY_PARENT
uv venv ".venv" --python 3.13
if exist ".venv\Scripts\python.exe" goto INSTALL

:TRY_PARENT
REM Jika folder aplikasi ada di dalam PJBL, coba Python .venv milik PJBL.
if not exist "..\.venv\Scripts\python.exe" goto TRY_LAUNCHER
"..\.venv\Scripts\python.exe" -m venv ".venv"
if exist ".venv\Scripts\python.exe" goto INSTALL

:TRY_LAUNCHER
py -3.13 -m venv ".venv" >nul 2>&1
if exist ".venv\Scripts\python.exe" goto INSTALL
python -m venv ".venv" >nul 2>&1
if exist ".venv\Scripts\python.exe" goto INSTALL

echo.
echo GAGAL: Python tidak ditemukan oleh launcher.
echo Buka terminal VS Code dan periksa perintah: uv --version
echo Jika sebelumnya ada .venv di folder PJBL, pastikan lokasi folder aplikasi benar.
pause
exit /b 1

:INSTALL
if exist ".venv\streamlit_ready.flag" goto RUN_APP

echo.
echo Menginstal dependensi aplikasi (perlu internet pada penggunaan pertama)...
where uv >nul 2>&1
if errorlevel 1 goto INSTALL_PIP
uv pip install --python ".venv\Scripts\python.exe" -r "requirements.txt"
if errorlevel 1 goto INSTALL_PIP
goto INSTALL_DONE

:INSTALL_PIP
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" -m ensurepip --upgrade
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto ERROR_INSTALL

:INSTALL_DONE
echo ready > ".venv\streamlit_ready.flag"

:RUN_APP
echo.
echo Menjalankan aplikasi pada http://localhost:8501
echo Untuk menghentikan aplikasi, tekan Ctrl+C di jendela ini.
echo.
".venv\Scripts\python.exe" -m streamlit run "app.py"
if errorlevel 1 goto ERROR_RUN
exit /b 0

:ERROR_INSTALL
echo.
echo GAGAL menginstal dependensi. Periksa internet dan pesan error di atas.
pause
exit /b 1

:ERROR_RUN
echo.
echo Aplikasi gagal dijalankan. Periksa pesan error di atas.
pause
exit /b 1
