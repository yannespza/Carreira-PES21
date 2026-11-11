@echo off
chcp 65001 >nul
title App de Carreira - PES 2021
cd /d "%~dp0"
py -c "import numpy, PIL, etcpak" 2>nul
if errorlevel 1 (
  echo Instalando componentes pela primeira vez. Aguarde...
  py -m pip install --no-index --find-links "%~dp0wheels" numpy pillow etcpak --quiet --disable-pip-version-check 2>nul || py -m pip install numpy pillow etcpak --quiet --disable-pip-version-check
)
py app.py
if errorlevel 1 (
  echo.
  echo Algo deu errado. Tire um print desta janela e mande para o Claude.
  pause
)
