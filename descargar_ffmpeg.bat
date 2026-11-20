@echo off
title Descargador e Instalador Automatico de FFmpeg Portable
cd /d "%~dp0"

echo =====================================================================
echo       INSTALADOR DIRECTO DE FFMPEG PORTABLE PARA TU PC
echo =====================================================================
echo.
echo Este proceso descargara FFmpeg y FFprobe oficiales y los dejara listos
echo dentro de tu carpeta de trabajo, sin que tengas que configurar el PATH.
echo.
echo Presiona una tecla para iniciar la descarga...
pause > nul
echo.

echo [1/3] Descargando FFmpeg (esto puede tardar 1 o 2 minutos segun tu internet)...
curl -L --progress-bar -o ffmpeg_temp.zip "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] No se pudo descargar desde el servidor principal.
    echo Intentando servidor secundario de GitHub...
    curl -L --progress-bar -o ffmpeg_temp.zip "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
)

if not exist ffmpeg_temp.zip (
    echo.
    echo [ERROR] No se pudo descargar el archivo zip.
    echo Por favor descarga manualmente el archivo desde:
    echo https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    pause
    exit /b 1
)

echo.
echo [2/3] Descomprimiendo archivos...
if not exist ffmpeg mkdir ffmpeg
tar -xf ffmpeg_temp.zip -C ffmpeg --strip-components=1

if not exist ffmpeg\bin\ffmpeg.exe (
    echo Reorganizando estructura de carpetas...
    for /d %%D in (ffmpeg\ffmpeg-*) do (
        if exist "%%D\bin\ffmpeg.exe" (
            move "%%D\bin" "ffmpeg\bin" > nul
        )
    )
)

del /f /q ffmpeg_temp.zip > nul 2>&1

echo.
echo [3/3] Comprobando instalacion...
if exist ffmpeg\bin\ffmpeg.exe (
    echo.
    echo =====================================================================
    echo   EXITO: FFmpeg y FFprobe quedaron instalados correctamente en:
    echo   %CD%\ffmpeg\bin
    echo =====================================================================
    echo.
    echo Ya puedes cerrar esta ventana y ejecutar 'iniciar_editor.bat'.
) else (
    echo [AVISO] Se descargo pero los archivos quedaron en otra subcarpeta.
    echo Busca la carpeta 'bin' dentro de 'ffmpeg' y muevela a 'ffmpeg\bin'.
)

echo.
pause
