@echo off
chcp 65001 >nul
title Instalar - App de Carreira PES 2021
cd /d "%~dp0"
echo.
echo  Instalando o App de Carreira...
echo.
py -m pip install --no-index --find-links "%~dp0wheels" numpy pillow etcpak --quiet --disable-pip-version-check
if errorlevel 1 (
  echo  Nao consegui instalar os componentes. Tire um print desta janela e mande para o Claude.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$app = '%~dp0'.TrimEnd('\');" ^
  "$pyw = (Get-Command pyw -ErrorAction SilentlyContinue).Source; if (-not $pyw) { $pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source };" ^
  "if (-not $pyw) { Write-Host ' Nao achei o pyw/pythonw do Python.'; exit 1 };" ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('Programs')) ''))) {" ^
  "  $lnk = $ws.CreateShortcut((Join-Path $dir 'Carreira PES 21.lnk'));" ^
  "  $lnk.TargetPath = $pyw; $lnk.Arguments = '\"' + (Join-Path $app 'app.py') + '\"';" ^
  "  $lnk.WorkingDirectory = $app; $lnk.IconLocation = (Join-Path $app 'web\icone.ico');" ^
  "  $lnk.Description = 'App de Carreira - Patrocinios (PES 2021)'; $lnk.Save() }"
if errorlevel 1 (
  echo  O atalho nao foi criado. Voce ainda pode usar o "Abrir App.bat".
  pause
  exit /b 1
)
echo.
echo  Pronto! Criei o atalho "Carreira PES 21" na Area de Trabalho e no Menu Iniciar.
echo  Abrindo o app...
start "" "%~dp0app.py"
timeout /t 3 >nul
