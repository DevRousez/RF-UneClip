#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SERVIDOR DE INTERFAZ GRÁFICA (GUI) - EDITOR DE VIDEOS INFANTILES
=============================================================================
Levanta un servidor web local interactivo estilo estudio de edición (CapCut)
con línea de tiempo multipista en tiempo real, previsualizador 9:16 vertical,
selector de canales (espacios de trabajo independientes) y renderizado con un clic.
=============================================================================
"""

import os
import sys
import json
import shutil
import urllib.parse
import threading
import webbrowser
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, List

# Importar funciones del motor central de video
import video_editor

PUERTO = 8765
RUTA_WEB = Path(__file__).parent / "web"

# Estado global del proceso de renderizado en segundo plano
ESTADO_RENDER = {
    "en_progreso": False,
    "progreso": 0,
    "mensaje": "Listo para editar",
    "logs": [],
    "finalizado": False,
    "exito": True
}


class VideoEditorHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP para la GUI web y la API REST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RUTA_WEB), **kwargs)

    def log_message(self, format, *args):
        # Desactivar logs ruidosos en la consola estándar
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        # 1. API: Listar canales
        if path == "/api/canales":
            self.responder_json(self.obtener_canales())
            return

        # 2. API: Cargar datos de un proyecto
        if path == "/api/proyecto":
            params = urllib.parse.parse_qs(url.query)
            canal = params.get("canal", [""])[0]
            proyecto = params.get("proyecto", [""])[0]
            self.responder_json(self.obtener_datos_proyecto(canal, proyecto))
            return

        # 3. API: Consultar estado de renderizado
        if path == "/api/estado_edicion":
            self.responder_json(ESTADO_RENDER)
            return

        # 4. API: Sugerir siguiente número de video y fecha
        if path == "/api/siguiente_video":
            params = urllib.parse.parse_qs(url.query)
            canal = params.get("canal", [""])[0]
            carpeta_canal = video_editor.obtener_ruta_canal(canal)
            sig_num = video_editor.detectar_siguiente_numero_video(carpeta_canal)
            fecha_sug = video_editor.obtener_fecha_sugerida()
            self.responder_json({
                "numero": sig_num,
                "prefijo": f"v{sig_num}",
                "fecha_sugerida": fecha_sug
            })
            return

        # 5. API: Descarga directa del video final al navegador
        if path == "/api/descargar_video":
            params = urllib.parse.parse_qs(url.query)
            canal = params.get("canal", [""])[0]
            proyecto = params.get("proyecto", [""])[0]
            carpeta_canal = video_editor.obtener_ruta_canal(canal)
            carpeta_p = carpeta_canal / proyecto
            candidatos = [
                carpeta_p / f"{proyecto} - FINAL.mp4",
                carpeta_p / "salida" / "video-final.mp4",
                carpeta_p / "video-final.mp4"
            ]
            for c in candidatos:
                if c.is_file():
                    self.servir_descarga_archivo(c)
                    return
            self.send_error(404, "El video final aún no ha sido generado")
            return

        # 6. Servir archivos multimedia (videos / audios) para vista previa
        if path.startswith("/media/"):
            partes = path[len("/media/"):].split("/")
            if len(partes) >= 3:
                canal, proyecto = partes[0], partes[1]
                nombre_archivo = "/".join(partes[2:])
                carpeta_canal = video_editor.obtener_ruta_canal(canal)
                posibles_rutas = [
                    carpeta_canal / proyecto / nombre_archivo,
                    carpeta_canal / proyecto / "escenas" / nombre_archivo,
                    carpeta_canal / proyecto / "narracion" / nombre_archivo,
                    carpeta_canal / proyecto / "audios" / nombre_archivo,
                    carpeta_canal / proyecto / "salida" / nombre_archivo,
                ]
                for r in posibles_rutas:
                    if r.is_file():
                        self.servir_archivo_local(r)
                        return
            self.send_error(404, "Archivo no encontrado")
            return

        # 5. Archivos estáticos de la interfaz web
        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        longitud = int(self.headers.get("Content-Length", 0))

        # 1. API: Crear canal / proyecto
        if path == "/api/canales/crear":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            canal = cuerpo.get("canal", "").strip()
            nombre_proyecto = cuerpo.get("proyecto", "").strip()
            numero = cuerpo.get("numero")
            nombre_corto = cuerpo.get("nombre_corto", "").strip()
            fecha = cuerpo.get("fecha", "").strip()
            
            if not canal:
                self.responder_json({"ok": False, "error": "El nombre del canal es obligatorio"})
                return
            try:
                carpeta_creada = video_editor.inicializar_proyecto(
                    canal=canal,
                    nombre_proyecto=nombre_proyecto if nombre_proyecto else None,
                    numero_video=int(numero) if numero is not None and str(numero).isdigit() else None,
                    nombre_corto=nombre_corto if nombre_corto else None,
                    fecha_pub=fecha if fecha else None
                )
                self.responder_json({"ok": True, "nombre_proyecto": carpeta_creada.name})
            except Exception as e:
                self.responder_json({"ok": False, "error": str(e)})
            return

        # 2. API: Configurar ruta externa de un canal
        if path == "/api/canales/configurar_ruta":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            canal = cuerpo.get("canal", "").strip()
            nueva_ruta = cuerpo.get("ruta", "").strip()
            if not canal or not nueva_ruta:
                self.responder_json({"ok": False, "error": "Canal y ruta son obligatorios"})
                return
            try:
                ruta_final = video_editor.vincular_ruta_canal(canal, nueva_ruta)
                self.responder_json({"ok": True, "ruta": str(ruta_final.resolve())})
            except Exception as e:
                self.responder_json({"ok": False, "error": str(e)})
            return

        # 3. API: Guardar guion.json
        if path == "/api/proyecto/guardar":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            canal = cuerpo.get("canal")
            proyecto = cuerpo.get("proyecto")
            guion = cuerpo.get("guion")
            carpeta_canal = video_editor.obtener_ruta_canal(canal)
            ruta_guion = carpeta_canal / proyecto / "guion.json"
            try:
                ruta_guion.parent.mkdir(parents=True, exist_ok=True)
                with open(ruta_guion, "w", encoding="utf-8") as f:
                    json.dump(guion, f, indent=2, ensure_ascii=False)
                self.responder_json({"ok": True})
            except Exception as e:
                self.responder_json({"ok": False, "error": str(e)})
            return

        # 3. API: Subir archivo de escena (video)
        if path == "/api/subir_escena":
            self.procesar_subida_archivo(longitud, subcarpeta="escenas")
            return

        # 3b. API: Subir archivo de narración (audio MP3)
        if path == "/api/subir_audio":
            self.procesar_subida_archivo(longitud, subcarpeta="narracion")
            return

        # 4. API: Comenzar edición
        if path == "/api/comenzar_edicion":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            canal = cuerpo.get("canal")
            proyecto = cuerpo.get("proyecto")
            voz = cuerpo.get("voz")
            sin_texto = cuerpo.get("sin_texto", False)
            sin_voz = cuerpo.get("sin_voz", False)
            volumen_video = float(cuerpo.get("volumen_video", 0.25))
            volumen_voz = float(cuerpo.get("volumen_voz", 1.0))

            if ESTADO_RENDER["en_progreso"]:
                self.responder_json({"ok": False, "error": "Ya hay una edición en progreso"})
                return

            # Iniciar edición en segundo plano
            hilo = threading.Thread(
                target=self.ejecutar_edicion_en_segundo_plano,
                args=(canal, proyecto, voz, sin_texto, sin_voz, volumen_video, volumen_voz)
            )
            hilo.daemon = True
            hilo.start()
            self.responder_json({"ok": True})
            return

        # 5. API: Modo Compilado
        if path == "/api/compilar":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            videos = [Path(v) for v in cuerpo.get("videos", [])]
            nombre_salida = cuerpo.get("salida", "compilacion_final.mp4")
            
            hilo = threading.Thread(
                target=self.ejecutar_compilacion_en_segundo_plano,
                args=(videos, Path(nombre_salida))
            )
            hilo.daemon = True
            hilo.start()
            self.responder_json({"ok": True})
            return

        # 6. API: Abrir carpeta en Windows Explorer
        if path == "/api/abrir_carpeta":
            cuerpo = json.loads(self.rfile.read(longitud).decode("utf-8"))
            canal = cuerpo.get("canal")
            proyecto = cuerpo.get("proyecto")
            carpeta_canal = video_editor.obtener_ruta_canal(canal)
            carpeta_proyecto = carpeta_canal / proyecto
            if not carpeta_proyecto.exists():
                carpeta_proyecto = carpeta_canal
            try:
                if sys.platform.startswith("win"):
                    subprocess.Popen(["explorer.exe", str(carpeta_proyecto.resolve())])
                elif sys.platform.startswith("darwin"):
                    subprocess.Popen(["open", str(carpeta_proyecto.resolve())])
                else:
                    subprocess.Popen(["xdg-open", str(carpeta_proyecto.resolve())])
                self.responder_json({"ok": True})
            except Exception as e:
                self.responder_json({"ok": False, "error": str(e)})
            return

        self.send_error(404, "Ruta no encontrada")

    # =========================================================================
    # Métodos auxiliares
    # =========================================================================

    def responder_json(self, datos: Any):
        payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def servir_descarga_archivo(self, ruta_archivo: Path):
        """Sirve el archivo forzando la descarga en el navegador del usuario."""
        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Disposition", f'attachment; filename="{ruta_archivo.name}"')
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)
        except Exception as e:
            self.send_error(500, f"Error al descargar archivo: {e}")

    def servir_archivo_local(self, ruta_archivo: Path):
        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()
            self.send_response(200)
            if ruta_archivo.suffix.lower() == ".mp4":
                self.send_header("Content-Type", "video/mp4")
            elif ruta_archivo.suffix.lower() == ".mp3":
                self.send_header("Content-Type", "audio/mpeg")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)
        except Exception as e:
            self.send_error(500, f"Error al servir archivo: {e}")

    def obtener_canales(self) -> Dict[str, Any]:
        cfg = video_editor.cargar_config()
        canales_dict = cfg.get("canales", {})
        dir_defecto = video_editor.obtener_directorio_canales_defecto()
        
        # Combinar canales de config con canales de la carpeta local
        if dir_defecto.exists():
            for d in dir_defecto.iterdir():
                if d.is_dir() and not d.name.startswith(".") and d.name not in canales_dict:
                    canales_dict[d.name] = str(d.resolve())

        canales = []
        for nombre, ruta_str in canales_dict.items():
            ruta_c = Path(ruta_str) if ruta_str else dir_defecto / nombre
            proyectos = []
            if ruta_c.is_dir():
                proyectos = [p.name for p in sorted(ruta_c.iterdir()) if p.is_dir() and not p.name.startswith(".")]
            canales.append({
                "nombre": nombre,
                "ruta": str(ruta_c.resolve()),
                "proyectos": proyectos
            })
        return {"canales": canales}

    def obtener_datos_proyecto(self, canal: str, proyecto: str) -> Dict[str, Any]:
        carpeta_canal = video_editor.obtener_ruta_canal(canal)
        carpeta = carpeta_canal / proyecto
        ruta_guion = carpeta / "guion.json"

        if not carpeta.exists():
            return {"error": f"La carpeta del proyecto no existe: {carpeta}"}

        guion = {}
        if ruta_guion.exists():
            try:
                with open(ruta_guion, "r", encoding="utf-8") as f:
                    guion = json.load(f)
            except Exception as e:
                return {"error": f"Error leyendo guion.json: {e}"}

        # Chequear presencia de archivos de video
        archivos_existentes = {}
        duraciones_video = {}
        archivos_audio_existentes = {}
        duraciones_audio = {}
        
        for idx, escena in enumerate(guion.get("escenas", []), start=1):
            nombre_v = escena.get("video", "")
            rutas_posibles = [
                carpeta / nombre_v,
                carpeta / "escenas" / nombre_v
            ]
            encontrado = False
            for r in rutas_posibles:
                if r.is_file() and r.stat().st_size > 0:
                    archivos_existentes[nombre_v] = True
                    encontrado = True
                    # Intentar obtener duración con ffprobe si está disponible
                    if shutil.which("ffprobe"):
                        try:
                            info = video_editor.obtener_info_media(r)
                            duraciones_video[nombre_v] = info["duracion"]
                        except Exception:
                            duraciones_video[nombre_v] = 10.0
                    else:
                        duraciones_video[nombre_v] = 10.0
                    break
            if not encontrado:
                archivos_existentes[nombre_v] = False
                duraciones_video[nombre_v] = 10.0
                
            # Buscar audio existente incorporado
            audio_hallado = video_editor.buscar_audio_existente_escena(
                carpeta_trabajo=carpeta,
                idx=idx,
                nombre_video=nombre_v,
                audio_especificado=escena.get("audio")
            )
            if audio_hallado:
                archivos_audio_existentes[idx - 1] = audio_hallado.name
                if shutil.which("ffprobe"):
                    try:
                        info_a = video_editor.obtener_info_media(audio_hallado)
                        duraciones_audio[idx - 1] = info_a["duracion"]
                    except Exception:
                        duraciones_audio[idx - 1] = 0.0
            else:
                archivos_audio_existentes[idx - 1] = None
                duraciones_audio[idx - 1] = 0.0

        return {
            "canal": canal,
            "proyecto": proyecto,
            "ruta_carpeta": str(carpeta.resolve()),
            "guion": guion,
            "archivos_existentes": archivos_existentes,
            "archivos_audio_existentes": archivos_audio_existentes,
            "duraciones_video": duraciones_video,
            "duraciones_audio": duraciones_audio
        }

    def procesar_subida_archivo(self, longitud: int, subcarpeta: str = "escenas"):
        """Maneja la recepción de un archivo (video o audio) desde el navegador."""
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.responder_json({"ok": False, "error": "Formato inválido"})
            return

        cuerpo_bytes = self.rfile.read(longitud)
        boundary = content_type.split("boundary=")[-1].encode("utf-8")
        partes = cuerpo_bytes.split(b"--" + boundary)

        parametros = {}
        archivo_bytes = None

        for parte in partes:
            if b'Content-Disposition: form-data;' in parte:
                lineas = parte.split(b"\r\n\r\n", 1)
                cabecera = lineas[0].decode("utf-8", errors="ignore")
                contenido = lineas[1].rstrip(b"\r\n") if len(lineas) > 1 else b""

                if 'name="canal"' in cabecera:
                    parametros["canal"] = contenido.decode("utf-8").strip()
                elif 'name="proyecto"' in cabecera:
                    parametros["proyecto"] = contenido.decode("utf-8").strip()
                elif 'name="nombre_destino"' in cabecera:
                    parametros["nombre_destino"] = contenido.decode("utf-8").strip()
                elif 'name="archivo"' in cabecera:
                    archivo_bytes = contenido

        canal = parametros.get("canal")
        proyecto = parametros.get("proyecto")
        nombre = parametros.get("nombre_destino")

        if not canal or not proyecto or not nombre or not archivo_bytes:
            self.responder_json({"ok": False, "error": "Datos incompletos en la subida"})
            return

        carpeta_canal = video_editor.obtener_ruta_canal(canal)
        carpeta_destino = carpeta_canal / proyecto / subcarpeta
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        ruta_guardar = carpeta_destino / nombre

        try:
            with open(ruta_guardar, "wb") as f:
                f.write(archivo_bytes)
            self.responder_json({"ok": True, "ruta": str(ruta_guardar), "nombre": nombre})
        except Exception as e:
            self.responder_json({"ok": False, "error": str(e)})

    def ejecutar_edicion_en_segundo_plano(self, canal: str, proyecto: str, voz: str, sin_texto: bool, sin_voz: bool = False, volumen_video: float = 0.25, volumen_voz: float = 1.0):
        """Ejecuta el renderizado y actualiza el estado de progreso en vivo."""
        global ESTADO_RENDER
        ESTADO_RENDER["en_progreso"] = True
        ESTADO_RENDER["progreso"] = 10
        ESTADO_RENDER["mensaje"] = "Verificando herramientas y archivos..."
        ESTADO_RENDER["logs"] = ["🎬 Iniciando proceso de renderizado..."]
        ESTADO_RENDER["finalizado"] = False
        ESTADO_RENDER["exito"] = False

        # Verificar dependencias
        video_editor.auto_detectar_ffmpeg()
        ok_dep, errores = video_editor.verificar_dependencias()
        
        # Si sin_voz=True, solo requerimos FFmpeg, edge-tts no es obligatorio
        if sin_voz and shutil.which("ffmpeg") and shutil.which("ffprobe"):
            ok_dep = True

        if not ok_dep:
            ESTADO_RENDER["en_progreso"] = False
            ESTADO_RENDER["finalizado"] = True
            ESTADO_RENDER["exito"] = False
            ESTADO_RENDER["mensaje"] = "Faltan herramientas (FFmpeg o edge-tts)"
            ESTADO_RENDER["logs"].extend(errores)
            return

        carpeta_canal = video_editor.obtener_ruta_canal(canal)
        carpeta_proyecto = carpeta_canal / proyecto

        try:
            ESTADO_RENDER["progreso"] = 25
            if sin_voz or volumen_voz <= 0:
                ESTADO_RENDER["mensaje"] = "Modo sin voz: procesando video con audio original..."
                ESTADO_RENDER["logs"].append("🔇 Voz en off desactivada.")
            else:
                ESTADO_RENDER["mensaje"] = f"Procesando narración (Voz: {voz}, Vol: {int(volumen_voz*100)}%)..."
                ESTADO_RENDER["logs"].append(f"🎙️ Narración activa al {int(volumen_voz*100)}%.")

            if volumen_video <= 0:
                ESTADO_RENDER["logs"].append("🔇 Audio original de los videos: SILENCIADO (0%).")
            else:
                ESTADO_RENDER["logs"].append(f"🔊 Audio original de los videos: {int(volumen_video*100)}%.")

            # Ejecutar el motor
            video_editor.ejecutar_edicion(
                carpeta=carpeta_proyecto,
                voz_override=voz,
                sin_texto=sin_texto,
                sin_voz=sin_voz,
                volumen_video=volumen_video,
                volumen_voz=volumen_voz
            )

            nombre_final = f"{carpeta_proyecto.name} - FINAL.mp4"
            ruta_video_final = carpeta_proyecto / nombre_final
            if not ruta_video_final.exists():
                ruta_video_final = carpeta_proyecto / "salida" / "video-final.mp4"

            ESTADO_RENDER["progreso"] = 100
            ESTADO_RENDER["mensaje"] = "¡Edición finalizada con éxito!"
            ESTADO_RENDER["ruta_video_final"] = str(ruta_video_final.resolve())
            ESTADO_RENDER["url_descarga"] = f"/api/descargar_video?canal={urllib.parse.quote(canal)}&proyecto={urllib.parse.quote(proyecto)}"
            ESTADO_RENDER["url_stream"] = f"/media/{canal}/{proyecto}/{nombre_final}"
            ESTADO_RENDER["logs"].append(f"🎉 Video exportado en: {ruta_video_final.resolve()}")
            ESTADO_RENDER["logs"].append("📐 Formato: 720x1280 (9:16), 24 fps, H.264 + AAC 128k, +faststart.")
            ESTADO_RENDER["finalizado"] = True
            ESTADO_RENDER["exito"] = True

        except Exception as e:
            ESTADO_RENDER["progreso"] = 100
            ESTADO_RENDER["mensaje"] = f"Error durante la edición: {e}"
            ESTADO_RENDER["logs"].append(f"❌ ERROR: {e}")
            ESTADO_RENDER["finalizado"] = True
            ESTADO_RENDER["exito"] = False

        finally:
            ESTADO_RENDER["en_progreso"] = False

    def ejecutar_compilacion_en_segundo_plano(self, videos: List[Path], salida: Path):
        """Ejecuta la compilación de múltiples videos en segundo plano."""
        global ESTADO_RENDER
        ESTADO_RENDER["en_progreso"] = True
        ESTADO_RENDER["progreso"] = 30
        ESTADO_RENDER["mensaje"] = f"Compilando {len(videos)} videos..."
        ESTADO_RENDER["logs"] = [f"📦 Uniendo {len(videos)} videos en '{salida.name}'..."]
        ESTADO_RENDER["finalizado"] = False

        try:
            video_editor.compilar_videos_terminados(lista_videos=videos, ruta_salida=salida)
            ESTADO_RENDER["progreso"] = 100
            ESTADO_RENDER["mensaje"] = "Compilación completada exitosamente"
            ESTADO_RENDER["logs"].append(f"🎉 Video largo generado: {salida.resolve()}")
            ESTADO_RENDER["finalizado"] = True
            ESTADO_RENDER["exito"] = True
        except Exception as e:
            ESTADO_RENDER["progreso"] = 100
            ESTADO_RENDER["mensaje"] = f"Error al compilar: {e}"
            ESTADO_RENDER["logs"].append(f"❌ ERROR: {e}")
            ESTADO_RENDER["finalizado"] = True
            ESTADO_RENDER["exito"] = False
        finally:
            ESTADO_RENDER["en_progreso"] = False


def iniciar_servidor():
    """Inicia el servidor local y abre la ventana en el navegador."""
    servidor = HTTPServer(("127.0.0.1", PUERTO), VideoEditorHandler)
    url = f"http://127.0.0.1:{PUERTO}"
    print("=" * 70)
    print("🌟 INTERFAZ GRÁFICA DE EDICIÓN DE VIDEOS INICIADA")
    print(f"👉 Abre en tu navegador: {url}")
    print("=" * 70)
    
    # Abrir navegador automáticamente
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        servidor.server_close()


if __name__ == "__main__":
    iniciar_servidor()
