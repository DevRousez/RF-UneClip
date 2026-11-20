Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   INSTALADOR DE DEPENDENCIAS - VIDEO STUDIO KIDS" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Instalando edge-tts con pip..." -ForegroundColor Yellow
python -m pip install edge-tts

Write-Host ""
Write-Host "[2/2] Instalando FFmpeg con winget..." -ForegroundColor Yellow
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

Write-Host ""
Write-Host "Verificando instalacion..." -ForegroundColor Yellow
python -c "import edge_tts; print('✓ edge-tts detectado correctamente')"
Get-Command ffmpeg -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "✓ FFmpeg detectado en: $($_.Source)" -ForegroundColor Green }
Get-Command ffprobe -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "✓ FFprobe detectado en: $($_.Source)" -ForegroundColor Green }

Write-Host ""
Write-Host "¡Listo! Ya puedes ejecutar iniciar_editor.bat" -ForegroundColor Green
Read-Host -Prompt "Presiona Enter para salir"
