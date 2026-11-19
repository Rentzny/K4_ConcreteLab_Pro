@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   K4 ConcreteLab Pro - START WINDOWS
 echo ==========================================
if not exist ".venv\Scripts\python.exe" (
  echo Membuat lingkungan Python .venv ...
  py -3.13 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  if errorlevel 1 (echo Gagal membuat .venv. Pastikan Python 3.11+ sudah terpasang. & pause & exit /b 1)
)
if not exist ".venv\streamlit_ready.flag" (
  echo Menginstal pustaka aplikasi untuk penggunaan pertama ...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Instalasi gagal. Cek koneksi internet dan versi Python. & pause & exit /b 1)
  echo ready > ".venv\streamlit_ready.flag"
)
echo Membuka aplikasi di browser pada http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 pause
