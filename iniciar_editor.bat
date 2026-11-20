@echo off
title Editor de Videos Infantiles 3D - YouTube Shorts & TikTok
cd /d "%~dp0"

echo =====================================================================
echo  Iniciando Interfaz Grafica de Video Studio Kids (9:16 Shorts)
echo =====================================================================
echo.

python gui_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo -----------------------------------------------------------------
    echo Si te falta FFmpeg, puedes instalarlo en 1 clic ejecutando:
    echo     descargar_ffmpeg.bat
    echo -----------------------------------------------------------------
    pause
)
