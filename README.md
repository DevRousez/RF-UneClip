# 🎬 Video Studio Kids - Automatizador de Edición (Shorts, TikTok y YouTube Largo)

Programa en Python + FFmpeg con **Interfaz Gráfica Visual (GUI)** y soporte por consola para automatizar la edición de videos animados infantiles tanto en formato vertical **9:16 (Shorts & TikTok)** como en formato horizontal **16:9 (YouTube Normal / Compilados Largos)**:
- 📐 **Múltiples Formatos y Relaciones de Aspecto:** Selector dinámico entre **9:16 Vertical** (720x1280), **16:9 Horizontal** (1280x720 / 1920x1080 Full HD) y **1:1 Cuadrado** (1080x1080).
- 📊 **Línea de tiempo multipista interactiva en tiempo real** (Pista de Video 3D, Pista de Narración y Pista de Texto en pantalla).
- 📱 **Simulador Adaptable (Smartphone 9:16 / Pantalla Panorámica 16:9)** con previsualización en vivo del video y del texto llamativo (con borde y sombra).
- 🎙️ **Narración por voz con `edge-tts` o Audios Propios** con control independiente de volumen para el video original y la voz en off.
- 📁 **Espacios de trabajo independientes por canal** con auto-incremento de numeración (`v18`, `v19`, etc.).
- 🚀 **Botón "Comenzar Edición" con barra de progreso en vivo y logs.**
- 📦 **Modo Compilado** para unir videos terminados en compilaciones largas horizontales (16:9) o verticales.

---

## 🚀 Instalación Rápida de Herramientas (1 Clic)

Para instalar **FFmpeg** y **edge-tts** en tu PC automáticamente:
- Haz doble clic en el archivo [instalar_dependencias.bat](file:///c:/Users/carlo/Documents/desarrollo/video-edit/instalar_dependencias.bat)
- O en PowerShell ejecuta:
  ```powershell
  pip install edge-tts
  winget install Gyan.FFmpeg
  ```

---

## 🖥️ Cómo Abrir la Interfaz Gráfica

Tienes dos formas sencillas en Windows:
1. **Doble Clic:** Haz doble clic en el archivo `iniciar_editor.bat`.
2. **Desde la terminal:**
   ```powershell
   python gui_app.py
   ```
*Se abrirá automáticamente en tu navegador predeterminado (Edge / Chrome) en `http://127.0.0.1:8765`.*

---

## 🚀 Requisitos Previos

El programa requiere **Python 3.10+** y dos herramientas fundamentales:

### 1. Instalar `edge-tts` (Voz en off gratuita sin API key)
Abre PowerShell o tu terminal y ejecuta:
```bash
pip install -r requirements.txt
```
*(O directamente: `pip install edge-tts`)*

### 2. Instalar `FFmpeg` y `FFprobe`
FFmpeg es el motor que une los videos, aplica el texto en pantalla y mezcla el audio.

#### En Windows (PowerShell):
**Opción A (Recomendada con winget):**
```powershell
winget install Gyan.FFmpeg
```
*Reinicia tu terminal PowerShell después de instalar.*

**Opción B (Con Chocolatey):**
```powershell
choco install ffmpeg
```

**Opción C (Manual):**
1. Descarga el paquete `ffmpeg-release-essentials.zip` desde [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/).
2. Descomprímelo (por ejemplo en `C:\ffmpeg`).
3. Agrega `C:\ffmpeg\bin` a la variable de entorno `PATH` de Windows.
4. Comprueba en la consola ejecutando: `ffmpeg -version` y `ffprobe -version`.

#### En Linux (Ubuntu / Debian):
```bash
sudo apt update && sudo apt install ffmpeg
```

---

## 📁 Espacios de Trabajo (Soporte para Múltiples Canales)

Para **no mezclar los videos de tus dos canales**, el programa incluye un gestor de proyectos que organiza todo en carpetas independientes:

```text
canales/
├── CanalPequi/
│   ├── 01_vocales/
│   │   ├── escenas/       <-- Coloca aquí escena-1.mp4 ... escena-4.mp4
│   │   ├── audios/        <-- Audios generados o personalizados
│   │   ├── salida/        <-- Aquí se exporta video-final.mp4
│   │   └── guion.json     <-- Guion y textos de este video
│   └── 02_colores/
│       └── ...
└── CanalSecundario/
    └── 01_dinosaurios/
        └── ...
```

### Comandos de Canales:
* **Crear un nuevo proyecto para un canal:**
  ```powershell
  python video_editor.py --iniciar-proyecto --canal "CanalPequi" --proyecto "01_vocales"
  ```
* **Listar todos tus canales y proyectos:**
  ```powershell
  python video_editor.py --listar-canales
  ```

---

## 📝 Formato del `guion.json`

Cada proyecto tiene su propio archivo `guion.json`:

```json
{
  "titulo": "Pequi aprende las vocales",
  "voz": "es-MX-DaliaNeural",
  "escenas": [
    { 
      "video": "escena-1.mp4", 
      "texto_voz": "¡A! De avión. Pequi aprendió la A.", 
      "texto_pantalla": "A" 
    },
    { 
      "video": "escena-2.mp4", 
      "texto_voz": "¡E! De elefante.", 
      "texto_pantalla": "E" 
    },
    { 
      "video": "escena-3.mp4", 
      "texto_voz": "¡I! De iguana.", 
      "texto_pantalla": "I" 
    },
    { 
      "video": "escena-4.mp4", 
      "texto_voz": "¡O de oso y U de uvas! Ya te sabes las vocales.", 
      "texto_pantalla": "O - U" 
    }
  ]
}
```

---

## ⚡ Guía de Uso

### 1. Procesar un video completo
Toma las escenas, genera la voz, baja el ambiente al 25%, estampa el texto y exporta el video:
```powershell
python video_editor.py --carpeta "canales/CanalPequi/01_vocales"
```

### 2. Omitir el texto en pantalla (Solo video + narración)
Usa la bandera `--sin-texto`:
```powershell
python video_editor.py --carpeta "canales/CanalPequi/01_vocales" --sin-texto
```

### 3. Cambiar la voz desde la línea de comandos
```powershell
python video_editor.py --carpeta "canales/CanalPequi/01_vocales" --voz "es-MX-JorgeNeural"
```
*(Voces recomendadas para contenido infantil: `es-MX-DaliaNeural`, `es-MX-JorgeNeural`, `es-CO-SalomeNeural`, `es-ES-ElviraNeural`)*

### 4. Usar una fuente tipográfica personalizada
Por defecto en Windows se usa **Comic Sans Bold** o **Arial Bold**. Puedes pasar cualquier archivo `.ttf`:
```powershell
python video_editor.py --carpeta "canales/CanalPequi/01_vocales" --fuente "C:/MisFuentes/KidsFont.ttf"
```

### 5. Reutilizar audios existentes o grabados en otro lado
Si ya generaste tus audios en otro lado:
- **Desde la Interfaz Gráfica:** En cada escena verás el botón **"🎙️ Adjuntar Audio MP3"**.
- **Desde el Explorador de Windows:** Cópialos dentro de la carpeta `narracion/` del video (con nombres como `escena-1.mp3`, `escena 1.mp3` o `audio-1.mp3`).
- El programa los detecta automáticamente (verás un indicador verde `✓ Audio propio`) y **no usará TTS ni tocará internet**.

### 6. Desactivar la voz en off (Opcional)
Si quieres exportar un video sin voz en off, conservando el audio ambiente original al 100%:
- **En la Interfaz:** Marca la casilla **`🔇 Desactivar Voz en Off`**.
- **En la Consola:** Agrega el parámetro `--sin-voz`:
  ```powershell
  python video_editor.py --carpeta "canales/kids studio/v18 pequi formas 22 nov 26" --sin-voz
  ```

### 7. Validación de duración (Protección de narración)
Si la narración en una escena dura más que el clip de video:
1. El programa emite una advertencia clara en la consola con la diferencia exacta en segundos.
2. **No corta la voz a la mitad**: extiende automáticamente el video congelando el último fotograma de la escena hasta que termine la narración.

### 7. Modo Compilado (Unir varios videos terminados en un video largo)
Para unir varios videos terminados (por ejemplo todas las vocales en un solo video de 10 minutos):
```powershell
python video_editor.py --compilar "video1.mp4" "video2.mp4" "video3.mp4" --salida "compilacion-vocales.mp4"
```

---

## 📊 Especificaciones del Video Final Exportado

* **Resolución:** `720x1280` (Vertical 9:16).
* **Velocidad de cuadro:** `24 fps`.
* **Códec de Video:** `H.264` (`libx264`, `yuv420p`).
* **Códec de Audio:** `AAC 128 kbps` (`-c:a aac -b:a 128k`).
* **Optimización Web:** Flags `+faststart` activadas (para inicio instantáneo en YouTube Shorts y TikTok).
