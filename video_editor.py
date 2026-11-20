#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AUTOMATIZADOR DE EDICIÓN DE VIDEOS INFANTILES (YouTube Shorts & TikTok)
=============================================================================
Une escenas 3D (720x1280, 24 fps), genera narración por voz TTS con edge-tts,
mezcla audio ambiente atenuado (0.25) con la voz, estampa texto llamativo
con borde/sombra en pantalla y exporta video final listo para publicar.

Soporta espacios de trabajo (canales) separados y modo de compilación para unir
múltiples videos terminados en un video largo.
=============================================================================
"""

import os
import sys
import re
import json
import shutil
import asyncio
import argparse
import datetime
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

MESES_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
}

def obtener_fecha_sugerida(dias_adelanto: int = 3) -> str:
    """Retorna una fecha sugerida en formato '22 nov 26'."""
    ahora = datetime.datetime.now() + datetime.timedelta(days=dias_adelanto)
    dia = ahora.day
    mes = MESES_ES.get(ahora.month, "nov")
    anio_corto = str(ahora.year)[-2:]
    return f"{dia} {mes} {anio_corto}"

def detectar_siguiente_numero_video(carpeta_canal: Path) -> int:
    """
    Escanea las carpetas de un canal buscando nombres que inicien con 'v' o 'V' seguido de dígitos
    (por ejemplo: 'v12', 'v18 pequi formas 22 nov 26', etc.).
    Devuelve el número siguiente más alto (ej. 19 si el último fue 18).
    """
    if not carpeta_canal.is_dir():
        return 1
    
    numeros = []
    patron = re.compile(r"^[vV](\d+)", re.IGNORECASE)
    for elem in carpeta_canal.iterdir():
        if elem.is_dir():
            match = patron.match(elem.name)
            if match:
                try:
                    numeros.append(int(match.group(1)))
                except ValueError:
                    pass
    if numeros:
        return max(numeros) + 1
    return 1

# Constantes de configuración por defecto
VOZ_DEFECTO = "es-MX-DaliaNeural"
FPS_DEFECTO = 24
ANCHO_DEFECTO = 720
ALTO_DEFECTO = 1280
VOLUMEN_AMBIENTE = 0.25
BITRATE_AUDIO = "128k"

FORMATOS_VIDEO = {
    "9:16": {"ancho": 720, "alto": 1280, "nombre": "9:16 Vertical (Shorts & TikTok)"},
    "16:9": {"ancho": 1280, "alto": 720, "nombre": "16:9 Horizontal (YouTube Normal 720p)"},
    "16:9-fhd": {"ancho": 1920, "alto": 1080, "nombre": "16:9 Full HD (YouTube Normal 1080p)"},
    "1:1": {"ancho": 1080, "alto": 1080, "nombre": "1:1 Cuadrado (Instagram)"}
}

def obtener_dimensiones_formato(formato: Optional[str] = "9:16") -> Tuple[int, int]:
    """
    Retorna la resolución (ancho, alto) según el formato deseado:
    - '9:16' (Shorts / TikTok): 720x1280
    - '16:9' (YouTube normal / horizontal): 1280x720
    - '16:9-fhd' (YouTube Full HD): 1920x1080
    - '1:1' (Cuadrado): 1080x1080
    """
    f = (formato or "9:16").lower().strip()
    if "1080" in f or "fhd" in f:
        return (1920, 1080)
    elif "16:9" in f or "horizontal" in f or "youtube" in f:
        return (1280, 720)
    elif "1:1" in f or "cuadrado" in f:
        return (1080, 1080)
    else:
        return (ANCHO_DEFECTO, ALTO_DEFECTO)

RUTA_CONFIG = Path(__file__).parent / "config.json"

def cargar_config() -> Dict[str, Any]:
    """Carga la configuración de rutas de canales desde config.json."""
    if RUTA_CONFIG.exists():
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"canales": {}}

def guardar_config(datos: Dict[str, Any]):
    """Guarda la configuración de rutas de canales en config.json."""
    try:
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def obtener_ruta_canal(nombre_canal: str) -> Path:
    """
    Retorna la ruta de la carpeta donde se almacenan los videos de un canal.
    Si el usuario configuró una ruta en su PC (por ejemplo fuera del proyecto),
    usa esa ruta; de lo contrario usa la carpeta local 'canales/{nombre_canal}'.
    """
    cfg = cargar_config()
    ruta_cfg = cfg.get("canales", {}).get(nombre_canal)
    if ruta_cfg and str(ruta_cfg).strip():
        p = Path(ruta_cfg).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    p = (Path("canales") / nombre_canal).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def vincular_ruta_canal(nombre_canal: str, ruta_carpeta: str) -> Path:
    """Asocia una ruta del disco de la PC a un canal en config.json."""
    cfg = cargar_config()
    if "canales" not in cfg:
        cfg["canales"] = {}
    p = Path(ruta_carpeta).resolve()
    p.mkdir(parents=True, exist_ok=True)
    cfg["canales"][nombre_canal] = str(p)
    guardar_config(cfg)
    return p

# Carpeta base por defecto para workspaces / canales:
def obtener_directorio_canales_defecto() -> Path:
    return Path("canales").resolve()

# Buscar fuentes disponibles según el sistema operativo
def obtener_fuente_por_defecto() -> str:
    """Detecta una fuente gruesa y legible adecuada para videos infantiles."""
    if sys.platform.startswith("win"):
        candidatas = [
            r"C:\Windows\Fonts\comicbd.ttf",   # Comic Sans Bold (muy amigable para niños)
            r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
            r"C:\Windows\Fonts\impact.ttf",    # Impact
            r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
            r"C:\Windows\Fonts\arial.ttf"      # Arial Regular
        ]
        for f in candidatas:
            if os.path.isfile(f):
                return f
        return "arialbd.ttf"
    elif sys.platform.startswith("darwin"): # macOS
        candidatas = [
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Comic Sans MS.ttf"
        ]
        for f in candidatas:
            if os.path.isfile(f):
                return f
        return "Arial"
    else: # Linux
        candidatas = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
        ]
        for f in candidatas:
            if os.path.isfile(f):
                return f
        return "DejaVuSans-Bold"


def auto_detectar_ffmpeg():
    """
    Intenta localizar ffmpeg y ffprobe en rutas locales o comunes de Windows
    y las agrega dinámicamente al PATH del proceso si no estaban cargadas.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return

    # 1. Buscar en subcarpeta local ./ffmpeg de forma recursiva
    local_ffmpeg = Path(__file__).parent / "ffmpeg"
    if local_ffmpeg.is_dir():
        for sub in local_ffmpeg.glob("**/ffmpeg.exe"):
            os.environ["PATH"] = str(sub.parent.resolve()) + os.pathsep + os.environ["PATH"]
            if shutil.which("ffmpeg"):
                return

    rutas_candidatas = [
        Path(__file__).parent / "ffmpeg" / "bin",
        Path(__file__).parent / "bin",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/ProgramData/chocolatey/bin"),
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    ]
    
    for r in rutas_candidatas:
        if r.is_dir():
            exe_ffmpeg = r / "ffmpeg.exe" if sys.platform.startswith("win") else r / "ffmpeg"
            if exe_ffmpeg.is_file():
                os.environ["PATH"] = str(r.resolve()) + os.pathsep + os.environ["PATH"]
                return
        elif "WinGet" in str(r) and r.is_dir():
            try:
                for sub in r.glob("**/ffmpeg.exe"):
                    os.environ["PATH"] = str(sub.parent.resolve()) + os.pathsep + os.environ["PATH"]
                    return
            except Exception:
                pass


# =============================================================================
# 1. VERIFICACIÓN DE DEPENDENCIAS (FFmpeg, FFprobe, edge-tts)
# =============================================================================

def verificar_dependencias() -> Tuple[bool, List[str]]:
    """
    Verifica que ffmpeg, ffprobe y edge-tts estén disponibles.
    Devuelve (exito, lista_de_mensajes_de_error).
    """
    auto_detectar_ffmpeg()
    errores = []
    
    # 1. Verificar FFmpeg en PATH
    if shutil.which("ffmpeg") is None:
        errores.append(
            "❌ [FFmpeg no encontrado en el sistema]\n"
            "   FFmpeg es indispensable para procesar y ensamblar los videos.\n"
            "   💡 Solución rápida en 1 clic:\n"
            "   - Haz doble clic en el archivo: descargar_ffmpeg.bat (en esta misma carpeta).\n"
            "     Se descargará y configurará automáticamente sin tocar el PATH.\n"
            "   - O si prefieres usar terminal (PowerShell):\n"
            "       winget install Gyan.FFmpeg\n"
        )
        
    # 2. Verificar FFprobe en PATH
    if shutil.which("ffprobe") is None:
        errores.append(
            "❌ [FFprobe no encontrado en el PATH del sistema]\n"
            "   FFprobe se incluye junto a FFmpeg y se usa para medir duraciones.\n"
            "   Asegúrate de que la carpeta de FFmpeg contenga tanto ffmpeg.exe como ffprobe.exe.\n"
        )
        
    # 3. Verificar edge-tts
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        errores.append(
            "❌ [Librería Python 'edge-tts' no instalada]\n"
            "   Se requiere para generar la voz en off de forma gratuita y sin API key.\n"
            "   💡 Cómo instalarla:\n"
            "       pip install edge-tts\n"
        )
        
    return len(errores) == 0, errores


# =============================================================================
# 2. METADATOS Y MEDICIÓN CON FFPROBE
# =============================================================================

def obtener_info_media(ruta_archivo: Path) -> Dict[str, Any]:
    """
    Obtiene la duración en segundos y la presencia de audio usando ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "json",
        str(ruta_archivo)
    ]
    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        datos = json.loads(resultado.stdout)
        duracion = float(datos.get("format", {}).get("duration", 0.0))
        streams = datos.get("streams", [])
        tiene_audio = any(s.get("codec_type") == "audio" for s in streams)
        tiene_video = any(s.get("codec_type") == "video" for s in streams)
        return {
            "duracion": duracion,
            "tiene_audio": tiene_audio,
            "tiene_video": tiene_video
        }
    except Exception as e:
        raise RuntimeError(f"Error al analizar el archivo '{ruta_archivo}' con ffprobe: {e}")


# =============================================================================
# 3. LECTURA Y VALIDACIÓN DEL GUION
# =============================================================================

def leer_guion(ruta_guion: Path, carpeta_trabajo: Optional[Path] = None) -> Dict[str, Any]:
    """
    Lee y valida la estructura del archivo guion.json.
    Si el archivo no existe pero se encontraron escenas (escena-*.mp4) en la carpeta,
    crea un guion.json inicial automáticamente para comodidad del usuario.
    """
    if not ruta_guion.is_file():
        # Intentar auto-generar guion si hay escenas en la carpeta
        if carpeta_trabajo and carpeta_trabajo.is_dir():
            posibles_escenas = sorted(list(carpeta_trabajo.glob("escena-*.mp4")) + list((carpeta_trabajo / "escenas").glob("escena-*.mp4")))
            if posibles_escenas:
                print(f"ℹ️  No se encontró guion.json. Creando plantilla automática con {len(posibles_escenas)} escenas encontradas...")
                lista_escenas_auto = []
                for p in posibles_escenas:
                    lista_escenas_auto.append({
                        "video": p.name,
                        "texto_voz": f"Texto de voz para {p.stem}",
                        "texto_pantalla": p.stem.replace("escena-", "").upper()
                    })
                plantilla = {
                    "titulo": carpeta_trabajo.name,
                    "voz": VOZ_DEFECTO,
                    "escenas": lista_escenas_auto
                }
                with open(ruta_guion, "w", encoding="utf-8") as f:
                    json.dump(plantilla, f, indent=2, ensure_ascii=False)
                print(f"✓ Plantilla '{ruta_guion.name}' creada. Puedes editarla para personalizar textos y voz.")
                return plantilla
                
        raise FileNotFoundError(f"No se encontró el archivo de guion: {ruta_guion}")
        
    try:
        with open(ruta_guion, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"El archivo '{ruta_guion}' no tiene un formato JSON válido: {e}")
        
    if "escenas" not in datos or not isinstance(datos["escenas"], list) or len(datos["escenas"]) == 0:
        raise ValueError("El guion.json debe contener una lista 'escenas' con al menos una escena.")
        
    for idx, escena in enumerate(datos["escenas"], start=1):
        if "video" not in escena:
            raise ValueError(f"La escena #{idx} no tiene la clave obligatoria 'video'.")
        if "texto_voz" not in escena:
            escena["texto_voz"] = ""
        if "texto_pantalla" not in escena:
            escena["texto_pantalla"] = ""
            
    return datos


# =============================================================================
# 4. GENERACIÓN DE VOZ (TTS con edge-tts)
# =============================================================================

async def _generar_audio_edge(texto: str, voz: str, ruta_salida: Path):
    """Llama asíncronamente a edge-tts para generar un archivo MP3."""
    import edge_tts
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(str(ruta_salida))


def generar_voz(
    texto: str,
    voz: str,
    ruta_salida: Path,
    reutilizar_existente: bool = True
) -> bool:
    """
    Genera el audio en formato MP3 con edge-tts.
    Si el archivo ya existe y reutilizar_existente=True, lo reutiliza sin volver a generarlo.
    Retorna True si fue generado de nuevo, False si se reutilizó.
    """
    if reutilizar_existente and ruta_salida.is_file() and ruta_salida.stat().st_size > 0:
        return False
        
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_generar_audio_edge(texto, voz, ruta_salida))
    return True


def limpiar_texto_busqueda(texto: str) -> str:
    """Elimina tildes, mayúsculas y caracteres especiales para comparaciones limpias."""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()


def buscar_audio_existente_escena(carpeta_trabajo: Path, idx: int, nombre_video: str, audio_especificado: Optional[str] = None) -> Optional[Path]:
    """
    Busca de forma inteligente si ya existe un archivo de audio para la escena en
    'narracion/', 'audios/' o en la raíz del proyecto.
    Soporta nombres con o sin tildes, con mayúsculas/minúsculas o espacios:
      - 'Narración escena 1.mp3', 'narracion escena 1.mp3'
      - 'escena-1.mp3', 'escena 1.mp3', 'audio 1.mp3'
    """
    carpetas_buscar = [
        carpeta_trabajo / "narracion",
        carpeta_trabajo / "audios",
        carpeta_trabajo
    ]
    
    stem_v = Path(nombre_video).stem
    
    # 1. Nombres exactos probados directamente
    nombres_probar = []
    if audio_especificado:
        nombres_probar.append(audio_especificado)
        nombres_probar.append(Path(audio_especificado).name)
        
    nombres_probar.extend([
        f"Narración escena {idx}.mp3",
        f"Narracion escena {idx}.mp3",
        f"narracion escena {idx}.mp3",
        f"escena-{idx}.mp3",
        f"escena {idx}.mp3",
        f"escena_{idx}.mp3",
        f"audio-{idx}.mp3",
        f"audio {idx}.mp3",
        f"audio_{idx}.mp3",
        f"{stem_v}.mp3",
        f"{idx}.mp3"
    ])
    
    for c_dir in carpetas_buscar:
        if not c_dir.is_dir():
            continue
        for n in nombres_probar:
            f = c_dir / n
            if f.is_file() and f.stat().st_size > 0:
                return f
                
        # 2. Búsqueda insensible a tildes y mayúsculas
        try:
            for archivo in c_dir.iterdir():
                if archivo.is_file() and archivo.suffix.lower() in [".mp3", ".wav", ".m4a", ".aac"]:
                    nombre_norm = limpiar_texto_busqueda(archivo.stem)
                    # Patrones como: 'escena 1', 'narracion escena 1', 'audio 1', 'escena-1', '1'
                    patrones = [
                        f"escena {idx}",
                        f"escena-{idx}",
                        f"escena_{idx}",
                        f"audio {idx}",
                        f"audio-{idx}",
                        f"narracion escena {idx}",
                        f"narracion {idx}",
                        f" {idx}",
                        f"-{idx}"
                    ]
                    if any(p in nombre_norm for p in patrones):
                        return archivo
                    if nombre_norm == str(idx):
                        return archivo
        except Exception:
            pass
            
    return None


def procesar_audios_escenas(
    escenas: List[Dict[str, Any]],
    carpeta_trabajo: Path,
    voz: str,
    carpeta_audios: Optional[Path] = None,
    sin_voz: bool = False
) -> List[Optional[Path]]:
    """
    Para cada escena del guion, genera o busca su archivo MP3 de narración.
    Si sin_voz=True, omite la generación y retorna None para cada escena.
    """
    if sin_voz:
        print("\n🔇 Modo sin voz en off activado: se omitirá la narración y se mantendrá el audio ambiente original.")
        return [None] * len(escenas)

    if carpeta_audios is None:
        if (carpeta_trabajo / "narracion").is_dir():
            carpeta_audios = carpeta_trabajo / "narracion"
        elif (carpeta_trabajo / "audios").is_dir():
            carpeta_audios = carpeta_trabajo / "audios"
        else:
            carpeta_audios = carpeta_trabajo / "narracion"
            
    carpeta_audios.mkdir(parents=True, exist_ok=True)
    
    rutas_audio = []
    print(f"\n🎙️  Procesando narración por voz (Voz: {voz})...")
    
    for idx, escena in enumerate(escenas, start=1):
        nombre_base = Path(escena["video"]).stem
        archivo_defecto = carpeta_audios / f"audio-{idx}-{nombre_base}.mp3"
        audio_especificado = escena.get("audio")
        
        # 1. Buscar si ya existe un audio previo generado en otro lado
        audio_existente = buscar_audio_existente_escena(
            carpeta_trabajo=carpeta_trabajo,
            idx=idx,
            nombre_video=escena["video"],
            audio_especificado=audio_especificado
        )
        
        texto = escena.get("texto_voz", "").strip()
        
        if audio_existente:
            print(f"   ✓ [Escena {idx}] Usando audio incorporado existente: {audio_existente.name} (en {audio_existente.parent.name}/)")
            rutas_audio.append(audio_existente)
        else:
            if not texto:
                print(f"   [Escena {idx}] Sin texto de voz ni audio previo. Se usará silencio.")
                generar_voz("...", voz, archivo_defecto)
            else:
                print(f"   [Escena {idx}] Generando voz TTS con edge-tts: \"{texto}\" -> {archivo_defecto.name}")
                generar_voz(texto, voz, archivo_defecto)
            rutas_audio.append(archivo_defecto)
            
    return rutas_audio


# =============================================================================
# 5. VALIDACIÓN DE DURACIONES (Video vs Narración)
# =============================================================================

def validar_duraciones(
    escenas: List[Dict[str, Any]],
    carpeta_trabajo: Path,
    rutas_audio: List[Optional[Path]]
) -> List[Dict[str, Any]]:
    """
    Compara la duración de cada escena de video contra su audio de narración.
    Si el audio dura más que el video, emite una advertencia clara y calcula
    la extensión necesaria (congelando el último frame) para NO cortar la voz.
    """
    print("\n⏱️  Validando duraciones de escenas...")
    detalles = []
    
    for idx, (escena, ruta_audio) in enumerate(zip(escenas, rutas_audio), start=1):
        ruta_video = carpeta_trabajo / escena["video"]
        if not ruta_video.is_file():
            # Buscar en subcarpeta 'escenas' si existe
            ruta_alt = carpeta_trabajo / "escenas" / escena["video"]
            if ruta_alt.is_file():
                ruta_video = ruta_alt
            else:
                raise FileNotFoundError(
                    f"❌ No se encontró el video de la Escena #{idx}: '{escena['video']}'. "
                    f"Buscado en '{ruta_video}' y '{ruta_alt}'."
                )
                
        info_v = obtener_info_media(ruta_video)
        dur_v = info_v["duracion"]
        
        if ruta_audio is not None and Path(ruta_audio).is_file():
            info_a = obtener_info_media(ruta_audio)
            dur_a = info_a["duracion"]
            extension = 0.0
            
            if dur_a > dur_v:
                extension = dur_a - dur_v
                print(
                    f"   ⚠️  [ALERTA en Escena {idx} - {ruta_video.name}]:\n"
                    f"      La narración ({dur_a:.2f} s) es más larga que la escena ({dur_v:.2f} s).\n"
                    f"      Diferencia: +{extension:.2f} s.\n"
                    f"      -> Para NO cortar la voz, se extenderá el último fotograma de la escena."
                )
            else:
                print(f"   ✓ [Escena {idx}] Video: {dur_v:.2f} s | Voz: {dur_a:.2f} s (Cabe perfectamente)")
        else:
            dur_a = 0.0
            extension = 0.0
            print(f"   ✓ [Escena {idx}] Video: {dur_v:.2f} s (Sin voz en off)")
            
        detalles.append({
            "idx": idx,
            "ruta_video": ruta_video,
            "ruta_audio": ruta_audio,
            "duracion_video": dur_v,
            "duracion_audio": dur_a,
            "extension_necesaria": extension,
            "tiene_audio_original": info_v["tiene_audio"],
            "texto_pantalla": escena.get("texto_pantalla", "")
        })
        
    return detalles
        
    return detalles


# =============================================================================
# 6. FILTROS DE TEXTO Y ESCAPADO PARA FFMPEG
# =============================================================================

def escapar_texto_drawtext(texto: str) -> str:
    """
    Escapa caracteres especiales para el filtro drawtext de FFmpeg.
    """
    # En FFmpeg drawtext: se escapan \, :, ', %, [, ]
    caracteres = [
        ('\\', r'\\'),
        (':', r'\:'),
        ("'", r"\'"),
        ('%', r'\%'),
        ('[', r'\['),
        (']', r'\]'),
    ]
    for orig, reemplazo in caracteres:
        texto = texto.replace(orig, reemplazo)
    return texto


def escapar_ruta_fuente(ruta_fuente: str) -> str:
    r"""
    Normaliza y escapa la ruta del archivo de fuente para FFmpeg en Windows y Linux.
    En Windows, 'C:\Fonts\fuente.ttf' debe convertirse en 'C\:/Fonts/fuente.ttf'.
    """
    p = Path(ruta_fuente).resolve()
    ruta_str = str(p).replace("\\", "/")
    if sys.platform.startswith("win") and len(ruta_str) > 1 and ruta_str[1] == ":":
        # Escapar los dos puntos de la letra de unidad (ej. C\:/...)
        ruta_str = ruta_str[0] + r"\:" + ruta_str[2:]
    return ruta_str


# =============================================================================
# 7. PROCESAMIENTO DE ESCENAS INDIVIDUALES Y ENSAMBLE
# =============================================================================

def procesar_escena(
    detalle: Dict[str, Any],
    ruta_salida_escena: Path,
    ruta_fuente: str,
    sin_texto: bool = False,
    volumen_video: float = 0.25,
    volumen_voz: float = 1.0,
    ancho: int = ANCHO_DEFECTO,
    alto: int = ALTO_DEFECTO
):
    """
    Procesa una única escena:
    1. Si la narración es más larga, extiende el último frame con tpad.
    2. Coloca el texto en pantalla llamativo con borde y sombra.
    3. Mezcla el audio con control total de volumen:
       - Si volumen_video == 0: silencia el audio original del video por completo.
       - Si volumen_voz == 0: silencia la narración.
       - Si ambos > 0: mezcla con 'normalize=0' para que la narración no pierda volumen.
    4. Garantiza resolución exacta (ancho x alto, ej: 720x1280 o 1280x720) a 24 fps.
    """
    ruta_v = detalle["ruta_video"]
    ruta_a = detalle["ruta_audio"]
    ext = detalle["extension_necesaria"]
    tiene_audio_orig = detalle["tiene_audio_original"]
    texto_pantalla = detalle["texto_pantalla"]
    
    # Construcción de la cadena de filtros de video
    video_filters = []
    
    # 1. Ajuste de escala / resolución base y fps (soporta 9:16 vertical, 16:9 horizontal, 1:1)
    video_filters.append(f"scale={ancho}:{alto}:force_original_aspect_ratio=decrease,pad={ancho}:{alto}:(ow-iw)/2:(oh-ih)/2,fps={FPS_DEFECTO}")
    
    # 2. Extensión de video si el audio es más largo
    if ext > 0.0:
        video_filters.append(f"tpad=stop_mode=clone:stop_duration={ext:.3f}")
        
    # 3. Filtro drawtext para texto en pantalla llamativo (proporcional al alto)
    if not sin_texto and texto_pantalla and texto_pantalla.strip():
        txt_escapado = escapar_texto_drawtext(texto_pantalla.strip())
        fuente_escapada = escapar_ruta_fuente(ruta_fuente)
        ratio_fontsize = "h/10" if ancho > alto else ("h/12" if ancho == alto else "h/14")
        filtro_texto = (
            f"drawtext=fontfile='{fuente_escapada}':"
            f"text='{txt_escapado}':"
            f"fontcolor=#FFE500:"
            f"fontsize={ratio_fontsize}:"
            f"bordercolor=black:"
            f"borderw=6:"
            f"shadowcolor=black@0.6:"
            f"shadowx=4:"
            f"shadowy=4:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2"
        )
        video_filters.append(filtro_texto)
        
    v_filter_str = ",".join(video_filters)
    
    # Construcción de la mezcla de audio profesional
    tiene_narracion_valida = (ruta_a is not None and Path(ruta_a).is_file() and volumen_voz > 0.0)
    video_con_sonido = (tiene_audio_orig and volumen_video > 0.0)
    
    # Caso 1: Silenciar el video original por completo (solo se escucha la narración limpia)
    if volumen_video <= 0.0:
        if tiene_narracion_valida:
            inputs = ["-i", str(ruta_v), "-i", str(ruta_a)]
            filter_complex = f"[0:v]{v_filter_str}[outv];[1:a]volume={volumen_voz:.2f},aresample=44100,aformat=channel_layouts=stereo[outa]"
        else:
            inputs = ["-i", str(ruta_v)]
            filter_complex = f"[0:v]{v_filter_str}[outv];anullsrc=channel_layout=stereo:sample_rate=44100[outa]"
            
    # Caso 2: Narración desactivada (solo se escucha el video original al volumen indicado)
    elif not tiene_narracion_valida:
        inputs = ["-i", str(ruta_v)]
        if video_con_sonido:
            filter_complex = f"[0:v]{v_filter_str}[outv];[0:a]volume={volumen_video:.2f},aresample=44100,aformat=channel_layouts=stereo[outa]"
        else:
            filter_complex = f"[0:v]{v_filter_str}[outv];anullsrc=channel_layout=stereo:sample_rate=44100[outa]"
            
    # Caso 3: Mezcla de ambos audios (Narración + Video Original de fondo)
    else:
        inputs = ["-i", str(ruta_v), "-i", str(ruta_a)]
        if video_con_sonido:
            # normalize=0 es crucial para que amix NO reduzca a la mitad el volumen de la voz
            filter_complex = (
                f"[0:v]{v_filter_str}[outv];"
                f"[0:a]volume={volumen_video:.2f},aresample=44100,aformat=channel_layouts=stereo[bg];"
                f"[1:a]volume={volumen_voz:.2f},aresample=44100,aformat=channel_layouts=stereo[voice];"
                f"[bg][voice]amix=inputs=2:duration=longest:normalize=0[outa]"
            )
        else:
            filter_complex = (
                f"[0:v]{v_filter_str}[outv];"
                f"[1:a]volume={volumen_voz:.2f},aresample=44100,aformat=channel_layouts=stereo[outa]"
            )
        
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", BITRATE_AUDIO,
        "-ar", "44100",
        str(ruta_salida_escena)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error procesando escena {detalle['idx']}:\n{res.stderr}")


def ensamblar_video_final(
    rutas_escenas_procesadas: List[Path],
    ruta_video_final: Path
):
    """
    Une todas las escenas procesadas en un único archivo final con las especificaciones
    requeridas (H.264, AAC 128k, +faststart, 720x1280, 24 fps).
    """
    ruta_video_final.parent.mkdir(parents=True, exist_ok=True)
    
    # Preparar el filtro concat para unir n escenas
    inputs = []
    filter_concat_in = ""
    for idx, p in enumerate(rutas_escenas_procesadas):
        inputs.extend(["-i", str(p)])
        filter_concat_in += f"[{idx}:v][{idx}:a]"
        
    n = len(rutas_escenas_procesadas)
    filter_complex = f"{filter_concat_in}concat=n={n}:v=1:a=1[v][a]"
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS_DEFECTO),
        "-c:a", "aac",
        "-b:a", BITRATE_AUDIO,
        "-movflags", "+faststart",
        str(ruta_video_final)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error al ensamblar el video final:\n{res.stderr}")


# =============================================================================
# 8. MODO COMPILACIÓN (Unir N videos terminados en un video largo)
# =============================================================================

def compilar_videos_terminados(
    lista_videos: List[Path],
    ruta_salida: Path,
    formato: str = "16:9"
):
    """
    Une N videos terminados en un único video largo, normalizando resolución
    y relación de aspecto (por defecto 16:9 horizontal 1280x720 para YouTube)
    para que no haya desincronización o bandas inesperadas.
    """
    if not lista_videos:
        raise ValueError("La lista de videos a compilar está vacía.")
        
    for v in lista_videos:
        if not v.is_file():
            raise FileNotFoundError(f"No existe el video a compilar: {v}")
            
    ancho, alto = obtener_dimensiones_formato(formato)
    print(f"\n📦 Compilando {len(lista_videos)} videos en '{ruta_salida.name}' con formato {formato} ({ancho}x{alto})...")
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    
    inputs = []
    filter_concat_in = ""
    for idx, v in enumerate(lista_videos):
        inputs.extend(["-i", str(v)])
        filter_concat_in += f"[{idx}:v][{idx}:a]"
        
    n = len(lista_videos)
    filter_complex = (
        f"{filter_concat_in}concat=n={n}:v=1:a=1[v][a];"
        f"[v]scale={ancho}:{alto}:force_original_aspect_ratio=decrease,pad={ancho}:{alto}:(ow-iw)/2:(oh-ih)/2,fps={FPS_DEFECTO}[vout]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", BITRATE_AUDIO,
        "-movflags", "+faststart",
        str(ruta_salida)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error en la compilación de videos:\n{res.stderr}")
        
    info = obtener_info_media(ruta_salida)
    print(f"🎉 Compilación completada con éxito: {ruta_salida}")
    print(f"⏱️  Duración total del video compilado: {info['duracion']:.2f} s")


# =============================================================================
# 9. GESTOR DE ESPACIOS DE TRABAJO (CANALES) Y NUEVOS PROYECTOS
# =============================================================================

def listar_canales(carpeta_base: Optional[Path] = None):
    """Muestra los canales y proyectos existentes en el espacio de trabajo."""
    cfg = cargar_config()
    canales_dict = cfg.get("canales", {})
    
    # También incluir carpetas dentro de canales/ si existen
    dir_defecto = obtener_directorio_canales_defecto()
    if dir_defecto.exists():
        for d in dir_defecto.iterdir():
            if d.is_dir() and not d.name.startswith(".") and d.name not in canales_dict:
                canales_dict[d.name] = str(d.resolve())
                
    print("\n" + "=" * 65)
    print("📁 ESPACIOS DE TRABAJO (CANALES CONFIGURADOS)")
    print("=" * 65)
    
    if not canales_dict:
        print("Aún no se han configurado canales. Usa --iniciar-proyecto para crear uno.")
        return
        
    for canal_nombre, ruta_str in canales_dict.items():
        ruta_c = Path(ruta_str) if ruta_str else dir_defecto / canal_nombre
        print(f"\n📺 Canal: [{canal_nombre}]")
        print(f"   📂 Ruta en PC: {ruta_c.resolve()}")
        if ruta_c.is_dir():
            proyectos = [p for p in sorted(ruta_c.iterdir()) if p.is_dir() and not p.name.startswith(".")]
            if not proyectos:
                print("   (Sin videos creados todavía)")
            for proj in proyectos:
                escenas = list((proj / "escenas").glob("*.mp4")) + list(proj.glob("escena-*.mp4"))
                guion_existe = "✓ guion.json" if (proj / "guion.json").exists() else "✗ sin guion"
                print(f"   └── 🎬 {proj.name} ({len(escenas)} escenas, {guion_existe})")
        else:
            print("   (La carpeta aún no existe en el disco)")
    print("=" * 65 + "\n")


def inicializar_proyecto(
    canal: str,
    nombre_proyecto: Optional[str] = None,
    carpeta_base: Optional[Path] = None,
    numero_video: Optional[int] = None,
    nombre_corto: Optional[str] = None,
    fecha_pub: Optional[str] = None
) -> Path:
    """
    Crea la estructura de carpetas aislada para un canal y proyecto específico:
    {carpeta_canal} / v{num} {nombre_corto} {fecha} /
      ├── escenas/     (para escena-1.mp4 ... escena-4.mp4)
      ├── narracion/   (para los audios de voz)
      ├── salida/      (copia del video)
      ├── guion.json   (guion de voz y textos)
      └── {nombre_carpeta} - FINAL.mp4 (se generará aquí)
    """
    if carpeta_base is not None:
        carpeta_canal = carpeta_base / canal
    else:
        carpeta_canal = obtener_ruta_canal(canal)
        
    carpeta_canal.mkdir(parents=True, exist_ok=True)
    
    # Si no se pasó nombre_proyecto directo, construir con la convención v{num} {nombre} {fecha}
    if not nombre_proyecto:
        num = numero_video if numero_video is not None else detectar_siguiente_numero_video(carpeta_canal)
        nc = nombre_corto.strip() if nombre_corto else "nuevo video"
        fp = fecha_pub.strip() if fecha_pub else obtener_fecha_sugerida()
        nombre_proyecto = f"v{num} {nc} {fp}"
        
    carpeta_proyecto = carpeta_canal / nombre_proyecto
    carpeta_escenas = carpeta_proyecto / "escenas"
    carpeta_narracion = carpeta_proyecto / "narracion"
    carpeta_salida = carpeta_proyecto / "salida"
    
    carpeta_escenas.mkdir(parents=True, exist_ok=True)
    carpeta_narracion.mkdir(parents=True, exist_ok=True)
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    
    ruta_guion = carpeta_proyecto / "guion.json"
    if not ruta_guion.exists():
        plantilla = {
            "titulo": f"{nombre_proyecto} ({canal})",
            "voz": VOZ_DEFECTO,
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
        with open(ruta_guion, "w", encoding="utf-8") as f:
            json.dump(plantilla, f, indent=2, ensure_ascii=False)
            
    print(f"\n📁 Proyecto creado con éxito:")
    print(f"   Canal: '{canal}'")
    print(f"   Carpeta del video: {carpeta_proyecto.name}")
    print(f"   Ruta completa: {carpeta_proyecto.resolve()}")
    print(f"   Coloca tus escenas en: {carpeta_escenas}")
    print(f"   Los audios de narración se guardarán en: {carpeta_narracion}")
    print(f"   Edita el guion en: {ruta_guion}")
    return carpeta_proyecto


# =============================================================================
# 10. FLUJO PRINCIPAL DE EDICIÓN
# =============================================================================

def ejecutar_edicion(
    carpeta: Path,
    ruta_guion: Optional[Path] = None,
    ruta_salida: Optional[Path] = None,
    voz_override: Optional[str] = None,
    sin_texto: bool = False,
    sin_voz: bool = False,
    volumen_video: float = 0.25,
    volumen_voz: float = 1.0,
    ruta_fuente: Optional[str] = None,
    formato: str = "9:16"
):
    """Ejecuta el pipeline completo de automatización de video."""
    carpeta = Path(carpeta).resolve()
    if not carpeta.is_dir():
        raise NotADirectoryError(f"La carpeta especificada no existe: {carpeta}")
        
    if ruta_guion is None:
        ruta_guion = carpeta / "guion.json"
        
    # 1. Cargar guion (o auto-generar si hay escenas)
    datos_guion = leer_guion(ruta_guion, carpeta_trabajo=carpeta)
    titulo = datos_guion.get("titulo", "Video Infantil")
    voz = voz_override or datos_guion.get("voz", VOZ_DEFECTO)
    formato_final = formato or datos_guion.get("formato", "9:16")
    ancho, alto = obtener_dimensiones_formato(formato_final)
    
    # Filtrar solo las escenas marcadas como activas
    todas_escenas = datos_guion.get("escenas", [])
    escenas = [e for e in todas_escenas if e.get("activa", True) is not False]
    if not escenas:
        raise ValueError("No hay escenas activas marcadas para procesar. Marca la casilla de al menos una escena.")
    
    print("=" * 70)
    print(f"🎬 INICIANDO EDICIÓN AUTOMATIZADA: {titulo}")
    print(f"📂 Carpeta de trabajo: {carpeta}")
    print(f"📐 Formato de video: {formato_final} ({ancho}x{alto})")
    print(f"🎯 Escenas seleccionadas: {len(escenas)} de {len(todas_escenas)}")
    if sin_voz or volumen_voz <= 0:
        print("🗣️  Voz en off: DESACTIVADA (0%)")
    else:
        print(f"🗣️  Voz seleccionada: {voz} (Volumen: {int(volumen_voz*100)}%)")
    print(f"🔊 Audio ambiente video original: {int(volumen_video*100)}% {'(Silenciado)' if volumen_video <= 0 else ''}")
    print(f"📝 Escenas a procesar: {len(escenas)}")
    print("=" * 70)
    
    # 2. Determinar fuente
    if ruta_fuente is None or not os.path.isfile(ruta_fuente):
        ruta_fuente = obtener_fuente_por_defecto()
    print(f"🔤 Fuente de texto en pantalla: {ruta_fuente}")
    
    # 3. Procesar narración / audios
    rutas_audio = procesar_audios_escenas(escenas, carpeta, voz, sin_voz=(sin_voz or volumen_voz <= 0))
    
    # 4. Validar duraciones
    detalles_escenas = validar_duraciones(escenas, carpeta, rutas_audio)
    
    # 5. Procesar cada escena individualmente
    carpeta_temp = carpeta / ".temp_procesamiento"
    carpeta_temp.mkdir(parents=True, exist_ok=True)
    rutas_procesadas = []
    
    try:
        print("\n🎨 Renderizando escenas con texto y audio mezclado...")
        for detalle in detalles_escenas:
            idx = detalle["idx"]
            salida_temp = carpeta_temp / f"escena_procesada_{idx}.mp4"
            txt_mostrar = f"\"{detalle['texto_pantalla']}\"" if detalle['texto_pantalla'] else "(sin texto)"
            print(f"   [Paso {idx}/{len(detalles_escenas)}] Escena #{idx} (Texto: {txt_mostrar})...", end="", flush=True)
            
            procesar_escena(
                detalle=detalle,
                ruta_salida_escena=salida_temp,
                ruta_fuente=ruta_fuente,
                sin_texto=sin_texto,
                volumen_video=volumen_video,
                volumen_voz=0.0 if sin_voz else volumen_voz,
                ancho=ancho,
                alto=alto
            )
            print(" [OK]")
            rutas_procesadas.append(salida_temp)
            
        # 6. Ensamblar video final
        if ruta_salida is None:
            # Se guarda con el nombre formal del video dentro de su carpeta de proyecto
            # Ejemplo: 'v18 pequi formas 22 nov 26 - FINAL.mp4'
            nombre_video_final = f"{carpeta.name} - FINAL.mp4"
            ruta_salida = carpeta / nombre_video_final
        else:
            ruta_salida = Path(ruta_salida).resolve()
            
        print(f"\n🚀 Ensamblando video final en: {ruta_salida.name}...")
        ensamblar_video_final(rutas_procesadas, ruta_salida)
        
        # También crear una copia o enlace en carpeta / 'salida' / 'video-final.mp4' para compatibilidad
        try:
            carpeta_salida = carpeta / "salida"
            carpeta_salida.mkdir(parents=True, exist_ok=True)
            copia_salida = carpeta_salida / "video-final.mp4"
            if copia_salida.resolve() != ruta_salida.resolve():
                shutil.copy2(ruta_salida, copia_salida)
        except Exception:
            pass
        
        # 7. Resumen de resultados
        info_final = obtener_info_media(ruta_salida)
        print("\n" + "=" * 70)
        print("🎉 ¡VIDEO GENERADO EXITOSAMENTE!")
        print(f"📍 Ubicación: {ruta_salida}")
        print(f"⏱️  Duración final: {info_final['duracion']:.2f} segundos")
        print(f"📐 Formato: {ANCHO_DEFECTO}x{ALTO_DEFECTO} (9:16 vertical), {FPS_DEFECTO} fps")
        print(f"🎵 Códec Audio: AAC {BITRATE_AUDIO} (Ambiente al 25% + Voz)")
        print("✨ Listo para subir a YouTube Shorts y TikTok.")
        print("=" * 70)
        
    finally:
        # Limpieza de archivos temporales
        if carpeta_temp.exists():
            shutil.rmtree(carpeta_temp, ignore_errors=True)


# =============================================================================
# 11. INTERFAZ DE LÍNEA DE COMANDOS (CLI)
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Automatizador de edición de videos para niños (YouTube Shorts y TikTok)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  1. Procesar un video normal:
     python video_editor.py --carpeta "canales/pequi/vocales"

  2. Especificar guion y archivo de salida:
     python video_editor.py --carpeta "./mi_video" --guion "./mi_video/guion.json" --salida "./video-final.mp4"

  3. Cambiar la voz y omitir texto en pantalla:
     python video_editor.py --carpeta "./mi_video" --voz "es-MX-JorgeNeural" --sin-texto

  4. Crear un nuevo proyecto organizado por canal (Workspace):
     python video_editor.py --iniciar-proyecto --canal "pequi_aventuras" --proyecto "aprende_colores"

  5. Modo compilado (unir varios videos terminados):
     python video_editor.py --compilar "video1.mp4" "video2.mp4" "video3.mp4" --salida "compilacion-larga.mp4"
        """
    )
    
    parser.add_argument("--carpeta", type=str, help="Ruta a la carpeta del proyecto con las escenas y guion.json")
    parser.add_argument("--guion", type=str, help="Ruta alternativa al archivo guion.json")
    parser.add_argument("--salida", type=str, help="Ruta de exportación para el archivo final (ej. video-final.mp4)")
    parser.add_argument("--voz", type=str, default=None, help=f"Voz TTS de edge-tts (defecto: {VOZ_DEFECTO})")
    parser.add_argument("--sin-texto", action="store_true", help="No agregar texto en pantalla")
    parser.add_argument("--sin-voz", action="store_true", help="Desactivar voz en off (conserva solo el audio ambiente original)")
    parser.add_argument("--volumen-video", type=float, default=0.25, help="Volumen del audio original del video (0.0 = silenciar por completo, 1.0 = normal)")
    parser.add_argument("--volumen-voz", type=float, default=1.0, help="Volumen de la narración de voz (1.0 = normal, 1.5 = alta)")
    parser.add_argument("--fuente", type=str, default=None, help="Ruta a un archivo de fuente .ttf personalizado")
    parser.add_argument("--formato", type=str, default="9:16", choices=["9:16", "16:9", "16:9-fhd", "1:1"], help="Relación de aspecto: '9:16' (Shorts), '16:9' (YouTube 720p), '16:9-fhd' (YouTube 1080p), '1:1' (Cuadrado)")
    
    # Gestión de Canales / Espacios de trabajo
    parser.add_argument("--iniciar-proyecto", action="store_true", help="Crea la estructura de carpetas para un nuevo proyecto de canal")
    parser.add_argument("--listar-canales", action="store_true", help="Lista los canales y proyectos existentes en el espacio de trabajo")
    parser.add_argument("--canal", type=str, default="CanalPequi", help="Nombre del canal o espacio de trabajo (ej. CanalPequi, CanalSecundario)")
    parser.add_argument("--proyecto", type=str, default=None, help="Nombre del proyecto/video dentro del canal")
    parser.add_argument("--numero", type=int, default=None, help="Número correlativo del video (ej. 19 para v19). Si no se indica, se autodetecta.")
    parser.add_argument("--nombre-corto", type=str, default=None, help="Nombre corto del video (ej. 'pequi formas')")
    parser.add_argument("--fecha", type=str, default=None, help="Fecha de publicación (ej. '22 nov 26')")
    parser.add_argument("--directorio-canales", type=str, default=None, help="Ruta personalizada para la carpeta raíz de canales")
    
    # Modo compilado
    parser.add_argument("--compilar", nargs="+", help="Modo compilado: lista de videos terminados para unir en un video largo")
    
    args = parser.parse_args()
    
    # 1. Verificar dependencias antes de empezar (solo si no es listar canales o iniciar proyecto básico)
    dir_canales = Path(args.directorio_canales) if args.directorio_canales else obtener_directorio_canales_defecto()
    
    if args.listar_canales:
        listar_canales(carpeta_base=dir_canales)
        sys.exit(0)
        
    if args.iniciar_proyecto:
        inicializar_proyecto(
            canal=args.canal,
            nombre_proyecto=args.proyecto,
            carpeta_base=dir_canales,
            numero_video=args.numero,
            nombre_corto=args.nombre_corto,
            fecha_pub=args.fecha
        )
        sys.exit(0)

    dependencias_ok, mensajes_error = verificar_dependencias()
    if not dependencias_ok:
        print("\n" + "!" * 75)
        print("⚠️  ATENCIÓN: Se encontraron dependencias faltantes en tu sistema:")
        print("!" * 75)
        for err in mensajes_error:
            print(err)
        print("Por favor instala las herramientas indicadas para que el programa pueda continuar.\n")
        sys.exit(1)
        
    # 3. Acción: Modo Compilación
    if args.compilar:
        salida_comp = Path(args.salida) if args.salida else Path("compilacion_final.mp4")
        videos = [Path(v) for v in args.compilar]
        formato_comp = args.formato if args.formato != "9:16" else "16:9"
        compilar_videos_terminados(lista_videos=videos, ruta_salida=salida_comp, formato=formato_comp)
        sys.exit(0)
        
    # 4. Acción: Edición normal de video
    if not args.carpeta:
        parser.print_help()
        print("\n⚠️  Debes especificar al menos --carpeta con la ubicación de las escenas y guion.json,")
        print("   o usar --iniciar-proyecto para crear una nueva estructura de canal.")
        sys.exit(1)
        
    ejecutar_edicion(
        carpeta=Path(args.carpeta),
        ruta_guion=Path(args.guion) if args.guion else None,
        ruta_salida=Path(args.salida) if args.salida else None,
        voz_override=args.voz,
        sin_texto=args.sin_texto,
        sin_voz=args.sin_voz,
        volumen_video=args.volumen_video,
        volumen_voz=args.volumen_voz,
        ruta_fuente=args.fuente,
        formato=args.formato
    )


if __name__ == "__main__":
    main()
