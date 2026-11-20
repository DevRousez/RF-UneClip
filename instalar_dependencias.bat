@echo off
title Instalador Automatico de Dependencias - Video Studio Kids
cd /d "%~dp0"

echo =====================================================================
echo    INSTALADOR DE DEPENDENCIAS PARA VIDEO STUDIO KIDS
echo =====================================================================
echo.
echo Este script instalara en tu PC:
echo   1. edge-tts (Generador gratuito de voz en off)
echo   2. FFmpeg y FFprobe (Motor de procesamiento y union de videos)
echo.
echo Presiona cualquier tecla para comenzar...
pause > nul
echo.

echo ---------------------------------------------------------------------
echo [1/2] Instalando libreria 'edge-tts' en Python...
echo ---------------------------------------------------------------------
python -m pip install edge-tts
if %ERRORLEVEL% EQU 0 (
    echo [OK] edge-tts instalado con exito.
) else (
    echo [AVISO] Hubo un problema al instalar edge-tts. Verifica tu conexion a internet.
)
echo.

echo ---------------------------------------------------------------------
echo [2/2] Instalando FFmpeg y FFprobe mediante winget de Windows...
echo ---------------------------------------------------------------------
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
if %ERRORLEVEL% EQU 0 (
    echo [OK] FFmpeg instalado con exito.
) else (
    echo.
    echo [AVISO] Si winget fallo o no esta disponible, puedes instalarlo con Chocolatey:
    echo     choco install ffmpeg
    echo O descargarlo manualmente desde:
    echo     https://www.gyan.dev/ffmpeg/builds/ (ffmpeg-release-essentials.zip)
    echo y extraer la carpeta 'bin' en C:\ffmpeg\bin
)

echo.
echo =====================================================================
echo  PROCESO TERMINADO
echo =====================================================================
echo  Ya puedes cerrar esta ventana y ejecutar 'iniciar_editor.bat'.
echo =====================================================================
echo.
pause
