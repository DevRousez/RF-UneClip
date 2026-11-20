// =============================================================================
// FRONTEND INTERACTIVO - EDITOR DE VIDEOS INFANTILES (Shorts & TikTok)
// =============================================================================

let canalActual = "";
let proyectoActual = "";
let datosProyecto = null;
let escenaSeleccionadaIdx = 0;
let indiceEscenaParaSubir = -1;
let indiceAudioParaSubir = -1;
let intervaloPollingRender = null;

// Elementos del DOM
const selectCanal = document.getElementById("selectCanal");
const selectProyecto = document.getElementById("selectProyecto");
const btnNuevoProyecto = document.getElementById("btnNuevoProyecto");
const btnGuardarGuion = document.getElementById("btnGuardarGuion");
const btnAgregarEscena = document.getElementById("btnAgregarEscena");
const btnComenzarEdicion = document.getElementById("btnComenzarEdicion");
const contenedorEscenas = document.getElementById("contenedorEscenas");
const selectFormato = document.getElementById("selectFormato");
const previewMockup = document.getElementById("previewMockup");
const formatoEspecificaciones = document.getElementById("formatoEspecificaciones");
const compiladorFormato = document.getElementById("compiladorFormato");
const selectVoz = document.getElementById("selectVoz");
const selectVolumenVideo = document.getElementById("selectVolumenVideo");
const selectVolumenVoz = document.getElementById("selectVolumenVoz");
const checkSinVoz = document.getElementById("checkSinVoz");
const checkSinTexto = document.getElementById("checkSinTexto");
const videoPreview = document.getElementById("videoPreview");
const screenPlaceholder = document.getElementById("screenPlaceholder");
const screenOverlayText = document.getElementById("screenOverlayText");
const inputArchivoEscena = document.getElementById("inputArchivoEscena");
const inputArchivoAudio = document.getElementById("inputArchivoAudio");
const pistaVideo = document.getElementById("pistaVideo");
const pistaAudio = document.getElementById("pistaAudio");
const pistaTexto = document.getElementById("pistaTexto");
const duracionEstimada = document.getElementById("duracionEstimada");
const toastContainer = document.getElementById("toastContainer");

// =============================================================================
// NOTIFICACIONES FLOTANTES (No bloqueantes)
// =============================================================================

function mostrarNotificacion(mensaje, tipo = "exito") {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${tipo}`;

  let icono = "✓";
  if (tipo === "error") icono = "❌";
  else if (tipo === "info") icono = "ℹ️";

  toast.innerHTML = `<span>${icono}</span> <span>${mensaje}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 2800);
}

// Modales
const modalNuevoProyecto = document.getElementById("modalNuevoProyecto");
const btnConfirmarNuevoProyecto = document.getElementById("btnConfirmarNuevoProyecto");
const btnCancelarNuevoProyecto = document.getElementById("btnCancelarNuevoProyecto");
const nuevoCanalNombre = document.getElementById("nuevoCanalNombre");
const nuevoNumeroVideo = document.getElementById("nuevoNumeroVideo");
const nuevoNombreCorto = document.getElementById("nuevoNombreCorto");
const nuevaFechaPub = document.getElementById("nuevaFechaPub");
const previewNombreCarpeta = document.getElementById("previewNombreCarpeta");

const overlayRender = document.getElementById("overlayRender");
const renderProgressBar = document.getElementById("renderProgressBar");
const renderEstado = document.getElementById("renderEstado");
const renderLogOutput = document.getElementById("renderLogOutput");
const renderRutaSalida = document.getElementById("renderRutaSalida");
const renderAcciones = document.getElementById("renderAcciones");
const btnCerrarRender = document.getElementById("btnCerrarRender");
const btnDescargarVideoFinal = document.getElementById("btnDescargarVideoFinal");
const btnAbrirCarpetaSalida = document.getElementById("btnAbrirCarpetaSalida");

// Modal Compilador
const btnAbrirCompilador = document.getElementById("btnAbrirCompilador");
const modalCompilador = document.getElementById("modalCompilador");
const btnCerrarCompilador = document.getElementById("btnCerrarCompilador");
const btnEjecutarCompilacion = document.getElementById("btnEjecutarCompilacion");


// =============================================================================
// 1. INICIALIZACIÓN Y CARGA DE DATOS
// =============================================================================

async function inicializar() {
  await cargarCanales();
  configurarEventos();
}

async function cargarCanales() {
  try {
    const res = await fetch("/api/canales");
    const data = await res.json();
    
    selectCanal.innerHTML = "";
    if (!data.canales || data.canales.length === 0) {
      selectCanal.innerHTML = "<option value=''>Sin canales</option>";
      selectProyecto.innerHTML = "<option value=''>Sin proyectos</option>";
      return;
    }

    data.canales.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.nombre;
      opt.textContent = c.nombre;
      selectCanal.appendChild(opt);
    });

    canalActual = data.canales[0].nombre;
    actualizarSelectorProyectos(data.canales[0].proyectos);
  } catch (err) {
    console.error("Error al cargar canales:", err);
  }
}

function actualizarSelectorProyectos(proyectos) {
  selectProyecto.innerHTML = "";
  if (!proyectos || proyectos.length === 0) {
    selectProyecto.innerHTML = "<option value=''>Sin proyectos</option>";
    proyectoActual = "";
    limpiarVista();
    return;
  }

  proyectos.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    selectProyecto.appendChild(opt);
  });

  proyectoActual = proyectos[0];
  cargarProyecto(canalActual, proyectoActual);
}

async function cargarProyecto(canal, proyecto) {
  if (!canal || !proyecto) return;
  try {
    const res = await fetch(`/api/proyecto?canal=${encodeURIComponent(canal)}&proyecto=${encodeURIComponent(proyecto)}`);
    const data = await res.json();
    if (data.error) {
      mostrarNotificacion("Error: " + data.error, "error");
      return;
    }
    datosProyecto = data;
    renderizarProyecto();
  } catch (err) {
    console.error("Error al cargar proyecto:", err);
  }
}

function limpiarVista() {
  contenedorEscenas.innerHTML = "<p style='color: var(--text-dim); padding: 20px;'>Crea un proyecto o selecciona uno para comenzar.</p>";
  pistaVideo.innerHTML = "";
  pistaAudio.innerHTML = "";
  pistaTexto.innerHTML = "";
  screenOverlayText.textContent = "";
}


// =============================================================================
// 2. RENDERIZADO DE ESCENAS Y LÍNEA DE TIEMPO
// =============================================================================

function renderizarProyecto() {
  if (!datosProyecto || !datosProyecto.guion) return;

  const guion = datosProyecto.guion;
  const escenas = guion.escenas || [];
  
  // Establecer voz
  if (guion.voz) {
    selectVoz.value = guion.voz;
  }

  // Establecer formato (9:16, 16:9, etc.)
  if (guion.formato && selectFormato) {
    selectFormato.value = guion.formato;
  }
  actualizarVistaFormato();

  // 1. Renderizar lista de escenas
  contenedorEscenas.innerHTML = "";
  escenas.forEach((escena, idx) => {
    const activa = escena.activa !== false;
    const card = document.createElement("div");
    card.className = `scene-card ${idx === escenaSeleccionadaIdx ? "active" : ""} ${activa ? "" : "disabled"}`;
    card.dataset.index = idx;

    const existeVideo = datosProyecto.archivos_existentes && datosProyecto.archivos_existentes[escena.video];
    const audioExistente = datosProyecto.archivos_audio_existentes ? datosProyecto.archivos_audio_existentes[idx] : null;
    const durV = datosProyecto.duraciones_video ? (datosProyecto.duraciones_video[escena.video] || 10) : 10;
    const durA = datosProyecto.duraciones_audio ? (datosProyecto.duraciones_audio[idx] || 0) : 0;
    
    card.innerHTML = `
      <div class="scene-card-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <input type="checkbox" class="check-escena-activa" data-index="${idx}" ${activa ? "checked" : ""} title="Marcar para incluir en la edición / Desmarcar para excluir">
          <span class="scene-badge">Escena ${idx + 1}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <div class="scene-file">
            <span class="file-status ${existeVideo ? 'status-ok' : 'status-missing'}" title="${existeVideo ? 'Video listo' : 'Falta archivo de video'}"></span>
            <span>${escena.video} (~${durV.toFixed(1)}s)</span>
          </div>
          <button class="btn-eliminar-escena" data-index="${idx}" title="Eliminar escena">🗑️</button>
        </div>
      </div>

      <div class="form-group">
        <label>Texto en Pantalla (Palabra clave):</label>
        <input type="text" class="form-control input-texto-pantalla" data-index="${idx}" value="${escena.texto_pantalla || ''}" placeholder="Ej: A, ROJO, CÍRCULO">
      </div>

      <div class="form-group">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <label style="margin: 0;">Voz en Off (Narración):</label>
          <span style="font-size: 11px; color: ${audioExistente ? 'var(--success)' : 'var(--text-dim)'}; font-weight: 600;">
            ${audioExistente ? '✓ Audio propio: ' + audioExistente : '⚡ Se generará con TTS'}
          </span>
        </div>
        <textarea class="form-control input-texto-voz" data-index="${idx}" placeholder="Texto que narrará la voz en off...">${escena.texto_voz || ''}</textarea>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <div class="dropzone btn-adjuntar-escena" data-index="${idx}" title="Cargar video MP4">
          📁 ${existeVideo ? 'Cambiar Video' : 'Adjuntar Video MP4'}
        </div>
        <div class="dropzone btn-adjuntar-audio" data-index="${idx}" title="Cargar audio MP3 propio">
          🎙️ ${audioExistente ? 'Cambiar Audio MP3' : 'Adjuntar Audio MP3'}
        </div>
      </div>
    `;

    // Clic en la tarjeta para previsualizar
    card.addEventListener("click", (e) => {
      if (
        e.target.tagName !== "INPUT" &&
        e.target.tagName !== "TEXTAREA" &&
        !e.target.classList.contains("dropzone") &&
        !e.target.classList.contains("btn-eliminar-escena")
      ) {
        seleccionarEscena(idx);
      }
    });

    contenedorEscenas.appendChild(card);
  });

  // 2. Eventos para checkboxes de activación y botones de eliminación
  document.querySelectorAll(".check-escena-activa").forEach(chk => {
    chk.addEventListener("change", (e) => {
      e.stopPropagation();
      const i = parseInt(e.target.dataset.index);
      escenas[i].activa = e.target.checked;
      const card = e.target.closest(".scene-card");
      if (card) {
        card.classList.toggle("disabled", !e.target.checked);
      }
      actualizarLineaTiempo();
    });
  });

  document.querySelectorAll(".btn-eliminar-escena").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const i = parseInt(btn.dataset.index);
      if (escenas.length <= 1) {
        mostrarNotificacion("El video debe tener al menos una escena", "info");
        return;
      }
      escenas.splice(i, 1);
      if (escenaSeleccionadaIdx >= escenas.length) {
        escenaSeleccionadaIdx = Math.max(0, escenas.length - 1);
      }
      renderizarProyecto();
      mostrarNotificacion(`Escena ${i + 1} eliminada`, "info");
    });
  });

  // 3. Configurar inputs para actualización en tiempo real
  document.querySelectorAll(".input-texto-pantalla").forEach(input => {
    input.addEventListener("input", (e) => {
      const i = parseInt(e.target.dataset.index);
      escenas[i].texto_pantalla = e.target.value;
      if (i === escenaSeleccionadaIdx) {
        screenOverlayText.textContent = checkSinTexto.checked ? "" : e.target.value;
      }
      actualizarLineaTiempo();
    });
  });

  document.querySelectorAll(".input-texto-voz").forEach(textarea => {
    textarea.addEventListener("input", (e) => {
      const i = parseInt(e.target.dataset.index);
      escenas[i].texto_voz = e.target.value;
      actualizarLineaTiempo();
    });
  });

  document.querySelectorAll(".btn-adjuntar-escena").forEach(btn => {
    btn.addEventListener("click", () => {
      indiceEscenaParaSubir = parseInt(btn.dataset.index);
      inputArchivoEscena.click();
    });
  });

  document.querySelectorAll(".btn-adjuntar-audio").forEach(btn => {
    btn.addEventListener("click", () => {
      indiceAudioParaSubir = parseInt(btn.dataset.index);
      inputArchivoAudio.click();
    });
  });

  actualizarVistaFormato();
  seleccionarEscena(escenaSeleccionadaIdx);
}

function actualizarVistaFormato() {
  if (!selectFormato) return;
  const fmt = selectFormato.value;
  if (previewMockup) {
    previewMockup.classList.remove("format-16-9", "format-1-1");
    if (fmt === "16:9" || fmt === "16:9-fhd") {
      previewMockup.classList.add("format-16-9");
    } else if (fmt === "1:1") {
      previewMockup.classList.add("format-1-1");
    }
  }

  if (formatoEspecificaciones) {
    if (fmt === "16:9") {
      formatoEspecificaciones.textContent = "Horizontal 1280x720 (16:9) @ 24fps • YouTube Normal • H.264 + AAC";
    } else if (fmt === "16:9-fhd") {
      formatoEspecificaciones.textContent = "Horizontal 1920x1080 (16:9 FHD) @ 24fps • YouTube Normal • H.264 + AAC";
    } else if (fmt === "1:1") {
      formatoEspecificaciones.textContent = "Cuadrado 1080x1080 (1:1) @ 24fps • Instagram Feed • H.264 + AAC";
    } else {
      formatoEspecificaciones.textContent = "Vertical 720x1280 (9:16) @ 24fps • Shorts & TikTok • H.264 + AAC";
    }
  }
}

if (selectFormato) {
  selectFormato.addEventListener("change", () => {
    if (datosProyecto && datosProyecto.guion) {
      datosProyecto.guion.formato = selectFormato.value;
    }
    actualizarVistaFormato();
    actualizarLineaTiempo();
  });
}

function seleccionarEscena(idx) {
  escenaSeleccionadaIdx = idx;
  document.querySelectorAll(".scene-card").forEach((c, i) => {
    c.classList.toggle("active", i === idx);
  });

  if (!datosProyecto || !datosProyecto.guion || !datosProyecto.guion.escenas[idx]) return;
  const escena = datosProyecto.guion.escenas[idx];

  // Actualizar texto en pantalla
  screenOverlayText.textContent = checkSinTexto.checked ? "" : (escena.texto_pantalla || "");

  // Si el video de la escena existe en la carpeta, cargarlo en el preview
  const existeVideo = datosProyecto.archivos_existentes && datosProyecto.archivos_existentes[escena.video];
  if (existeVideo) {
    const videoUrl = `/media/${encodeURIComponent(canalActual)}/${encodeURIComponent(proyectoActual)}/${encodeURIComponent(escena.video)}`;
    if (videoPreview.getAttribute("data-src") !== videoUrl) {
      videoPreview.setAttribute("data-src", videoUrl);
      videoPreview.src = videoUrl;
      videoPreview.load();
    }
    videoPreview.style.display = "block";
    screenPlaceholder.style.display = "none";
    videoPreview.play().catch(err => {
      console.log("Reproducción automática no permitida o pausada:", err);
    });
  } else {
    videoPreview.pause();
    videoPreview.removeAttribute("src");
    videoPreview.removeAttribute("data-src");
    videoPreview.style.display = "none";
    screenPlaceholder.style.display = "flex";
  }
}

function actualizarLineaTiempo() {
  if (!datosProyecto || !datosProyecto.guion) return;

  const escenas = datosProyecto.guion.escenas || [];
  pistaVideo.innerHTML = "";
  pistaAudio.innerHTML = "";
  pistaTexto.innerHTML = "";

  let duracionTotal = 0;
  let escenasActivasCount = 0;

  escenas.forEach((escena, idx) => {
    // Si la escena fue desmarcada, no se añade a la línea de tiempo
    if (escena.activa === false) {
      return;
    }
    escenasActivasCount++;

    const durV = datosProyecto.duraciones_video ? (datosProyecto.duraciones_video[escena.video] || 10) : 10;
    // Estimación de duración de voz: aprox 14 caracteres por segundo en español hablado
    const longitudTexto = (escena.texto_voz || "").trim().length;
    const durA_estimada = longitudTexto > 0 ? Math.max(1.5, longitudTexto / 13) : 0;
    const durA_real = datosProyecto.duraciones_audio ? (datosProyecto.duraciones_audio[idx] || 0) : 0;
    const durA = durA_real > 0 ? durA_real : durA_estimada;

    const esAlertaAudio = durA > durV;
    const durMaxEscena = Math.max(durV, durA);
    duracionTotal += durMaxEscena;

    // 1. Clip Video
    const clipV = document.createElement("div");
    clipV.className = "timeline-clip clip-video";
    const volVid = parseFloat(selectVolumenVideo.value);
    const estadoAudioVideo = volVid === 0 ? "🔇 Silenciado" : `🔊 ${Math.round(volVid * 100)}%`;
    clipV.innerHTML = `<span>Escena ${idx + 1} (${escena.video}) [${estadoAudioVideo}]</span><span class="clip-badge">${durV.toFixed(1)}s</span>`;
    clipV.addEventListener("click", () => seleccionarEscena(idx));
    pistaVideo.appendChild(clipV);

    // 2. Clip Audio
    const clipA = document.createElement("div");
    const volVoz = parseFloat(selectVolumenVoz.value);
    const narracionDesactivada = (checkSinVoz && checkSinVoz.checked) || (volVoz === 0);

    if (narracionDesactivada) {
      clipA.className = "timeline-clip clip-audio";
      clipA.style.opacity = "0.4";
      clipA.style.background = "#4b5563";
      clipA.innerHTML = `<span>Escena ${idx + 1}: 🔇 Narración desactivada</span><span class="clip-badge">0s</span>`;
    } else {
      clipA.className = `timeline-clip clip-audio ${esAlertaAudio ? 'warning' : ''}`;
      const txtAlerta = esAlertaAudio ? `⚠️ +${(durA - durV).toFixed(1)}s` : '';
      const etiquetaAudio = datosProyecto.archivos_audio_existentes && datosProyecto.archivos_audio_existentes[idx - 1] ? 'Propio' : 'TTS';
      clipA.innerHTML = `<span>Voz #${idx + 1} (${etiquetaAudio} ${Math.round(volVoz * 100)}%) ${txtAlerta}</span><span class="clip-badge">${durA.toFixed(1)}s</span>`;
    }
    clipA.addEventListener("click", () => seleccionarEscena(idx));
    pistaAudio.appendChild(clipA);

    // 3. Clip Texto
    const clipT = document.createElement("div");
    clipT.className = "timeline-clip clip-text";
    const textoMostrar = checkSinTexto.checked ? "(desactivado)" : (escena.texto_pantalla || "(sin texto)");
    const badgeFormato = selectFormato ? selectFormato.value.replace("-fhd", "") : "9:16";
    clipT.innerHTML = `<span>"${textoMostrar}"</span><span class="clip-badge">${badgeFormato}</span>`;
    clipT.addEventListener("click", () => seleccionarEscena(idx));
    pistaTexto.appendChild(clipT);
  });

  if (escenasActivasCount === 0) {
    duracionEstimada.textContent = "⚠️ Ninguna escena activa seleccionada";
    pistaVideo.innerHTML = "<div style='color: var(--text-dim); padding: 8px;'>Marca al menos una escena para incluirla en la edición.</div>";
  } else {
    duracionEstimada.textContent = `Duración estimada (${escenasActivasCount} escenas): ~${duracionTotal.toFixed(1)}s`;
  }
}


// =============================================================================
// 3. ADJUNTAR ARCHIVOS DE VIDEO Y AUDIO (Subida con estado de carga inline)
// =============================================================================

inputArchivoEscena.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || indiceEscenaParaSubir < 0) return;

  const idx = indiceEscenaParaSubir;
  const escena = datosProyecto.guion.escenas[idx];
  const nombreDestino = escena.video;

  // Estado inline de carga en el botón de la tarjeta
  const btnSubir = document.querySelector(`.btn-adjuntar-escena[data-index="${idx}"]`);
  let textoOriginal = "";
  if (btnSubir) {
    textoOriginal = btnSubir.innerHTML;
    btnSubir.innerHTML = "⏳ Subiendo...";
    btnSubir.style.pointerEvents = "none";
    btnSubir.style.opacity = "0.7";
  }

  const formData = new FormData();
  formData.append("canal", canalActual);
  formData.append("proyecto", proyectoActual);
  formData.append("nombre_destino", nombreDestino);
  formData.append("archivo", file);

  try {
    const res = await fetch("/api/subir_escena", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      mostrarNotificacion(`✓ Video Escena ${idx + 1} (${nombreDestino}) cargado correctamente`);
      await cargarProyecto(canalActual, proyectoActual);
    } else {
      mostrarNotificacion("Error al subir video: " + data.error, "error");
      if (btnSubir) {
        btnSubir.innerHTML = textoOriginal;
        btnSubir.style.pointerEvents = "auto";
        btnSubir.style.opacity = "1";
      }
    }
  } catch (err) {
    mostrarNotificacion("Error de conexión al subir video", "error");
    if (btnSubir) {
      btnSubir.innerHTML = textoOriginal;
      btnSubir.style.pointerEvents = "auto";
      btnSubir.style.opacity = "1";
    }
  } finally {
    inputArchivoEscena.value = "";
    indiceEscenaParaSubir = -1;
  }
});

inputArchivoAudio.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || indiceAudioParaSubir < 0) return;

  const idx = indiceAudioParaSubir;
  const ext = file.name.substring(file.name.lastIndexOf(".")) || ".mp3";
  const nombreDestino = `escena-${idx + 1}${ext}`;

  // Estado inline de carga en el botón de la tarjeta
  const btnSubir = document.querySelector(`.btn-adjuntar-audio[data-index="${idx}"]`);
  let textoOriginal = "";
  if (btnSubir) {
    textoOriginal = btnSubir.innerHTML;
    btnSubir.innerHTML = "⏳ Subiendo...";
    btnSubir.style.pointerEvents = "none";
    btnSubir.style.opacity = "0.7";
  }

  const formData = new FormData();
  formData.append("canal", canalActual);
  formData.append("proyecto", proyectoActual);
  formData.append("nombre_destino", nombreDestino);
  formData.append("archivo", file);

  try {
    const res = await fetch("/api/subir_audio", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      mostrarNotificacion(`✓ Audio Escena ${idx + 1} (${data.nombre}) incorporado correctamente`);
      await cargarProyecto(canalActual, proyectoActual);
    } else {
      mostrarNotificacion("Error al subir audio: " + data.error, "error");
      if (btnSubir) {
        btnSubir.innerHTML = textoOriginal;
        btnSubir.style.pointerEvents = "auto";
        btnSubir.style.opacity = "1";
      }
    }
  } catch (err) {
    mostrarNotificacion("Error de red al subir audio", "error");
    if (btnSubir) {
      btnSubir.innerHTML = textoOriginal;
      btnSubir.style.pointerEvents = "auto";
      btnSubir.style.opacity = "1";
    }
  } finally {
    inputArchivoAudio.value = "";
    indiceAudioParaSubir = -1;
  }
});


// =============================================================================
// 4. GUARDAR GUION Y PROCESAR EDICIÓN
// =============================================================================

async function guardarGuion(silencioso = false) {
  if (!datosProyecto || !datosProyecto.guion) return;

  datosProyecto.guion.voz = selectVoz.value;
  if (selectFormato) {
    datosProyecto.guion.formato = selectFormato.value;
  }

  try {
    const res = await fetch("/api/proyecto/guardar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        canal: canalActual,
        proyecto: proyectoActual,
        guion: datosProyecto.guion
      })
    });
    const data = await res.json();
    if (!silencioso) {
      if (data.ok) mostrarNotificacion("✓ Guion guardado correctamente");
      else mostrarNotificacion("Error al guardar: " + data.error, "error");
    }
  } catch (err) {
    if (!silencioso) mostrarNotificacion("Error de red al guardar: " + err, "error");
  }
}

btnGuardarGuion.addEventListener("click", () => guardarGuion(false));

if (btnAgregarEscena) {
  btnAgregarEscena.addEventListener("click", () => {
    if (!datosProyecto || !datosProyecto.guion) return;
    if (!datosProyecto.guion.escenas) datosProyecto.guion.escenas = [];
    const escenas = datosProyecto.guion.escenas;
    const nextNum = escenas.length + 1;
    escenas.push({
      video: `escena-${nextNum}.mp4`,
      texto_pantalla: `ESCENA ${nextNum}`,
      texto_voz: `Texto narrado para la escena ${nextNum}...`,
      activa: true
    });
    renderizarProyecto();
    seleccionarEscena(escenas.length - 1);
    mostrarNotificacion(`✓ Escena ${nextNum} añadida al guion`);
  });
}

selectVolumenVideo.addEventListener("change", () => {
  actualizarLineaTiempo();
});

selectVolumenVoz.addEventListener("change", () => {
  const muteado = (selectVolumenVoz.value === "0");
  selectVoz.disabled = muteado;
  if (checkSinVoz) checkSinVoz.checked = muteado;
  actualizarLineaTiempo();
});

if (checkSinVoz) {
  checkSinVoz.addEventListener("change", () => {
    const desactivada = checkSinVoz.checked;
    selectVoz.disabled = desactivada;
    selectVolumenVoz.disabled = desactivada;
    if (desactivada) {
      selectVolumenVoz.value = "0";
    } else if (selectVolumenVoz.value === "0") {
      selectVolumenVoz.value = "1.5";
    }
    actualizarLineaTiempo();
  });
}

checkSinTexto.addEventListener("change", () => {
  screenOverlayText.textContent = checkSinTexto.checked ? "" : (datosProyecto.guion.escenas[escenaSeleccionadaIdx]?.texto_pantalla || "");
  actualizarLineaTiempo();
});

btnComenzarEdicion.addEventListener("click", async () => {
  if (!canalActual || !proyectoActual) {
    mostrarNotificacion("Selecciona un canal y proyecto primero.", "info");
    return;
  }

  const escenasActivas = (datosProyecto?.guion?.escenas || []).filter(e => e.activa !== false);
  if (escenasActivas.length === 0) {
    mostrarNotificacion("Debes marcar al menos una escena para comenzar la edición.", "info");
    return;
  }

  // Guardar guion actual antes de iniciar
  await guardarGuion(true);

  // Mostrar modal de render
  overlayRender.style.display = "flex";
  renderProgressBar.style.width = "0%";
  renderEstado.textContent = "Iniciando renderizado con FFmpeg...";
  renderLogOutput.textContent = "Preparando pistas de audio, video y fuentes...\n";
  renderAcciones.style.display = "none";

  const volVid = parseFloat(selectVolumenVideo.value);
  const volVoz = parseFloat(selectVolumenVoz.value);
  const sinVoz = (checkSinVoz && checkSinVoz.checked) || (volVoz === 0);
  const formatoSeleccionado = selectFormato ? selectFormato.value : "9:16";

  try {
    const res = await fetch("/api/comenzar_edicion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        canal: canalActual,
        proyecto: proyectoActual,
        voz: selectVoz.value,
        sin_texto: checkSinTexto.checked,
        sin_voz: sinVoz,
        volumen_video: volVid,
        volumen_voz: volVoz,
        formato: formatoSeleccionado
      })
    });
    const data = await res.json();

    if (!data.ok) {
      renderEstado.textContent = "Error al iniciar: " + data.error;
      renderLogOutput.textContent += "\n❌ " + data.error;
      renderAcciones.style.display = "flex";
      return;
    }

    iniciarSondeoProgreso();
  } catch (err) {
    renderEstado.textContent = "Error de conexión: " + err;
    renderAcciones.style.display = "flex";
  }
});

function iniciarSondeoProgreso() {
  if (intervaloPollingRender) clearInterval(intervaloPollingRender);

  intervaloPollingRender = setInterval(async () => {
    try {
      const res = await fetch("/api/estado_edicion");
      const estado = await res.json();

      renderProgressBar.style.width = `${estado.progreso}%`;
      renderEstado.textContent = estado.mensaje;
      renderLogOutput.textContent = estado.logs.join("\n");
      renderLogOutput.scrollTop = renderLogOutput.scrollHeight;

      if (estado.finalizado) {
        clearInterval(intervaloPollingRender);
        renderAcciones.style.display = "flex";
        if (estado.exito) {
          renderTitulo.textContent = "🎉 ¡Edición Completada Exitosamente!";
          if (estado.ruta_video_final) {
            renderRutaSalida.style.display = "block";
            renderRutaSalida.textContent = "📍 Ubicación: " + estado.ruta_video_final;
          }
          // Recargar datos
          cargarProyecto(canalActual, proyectoActual);
        } else {
          renderTitulo.textContent = "❌ Error en la Edición";
        }
      }
    } catch (err) {
      console.error("Error al sondear estado:", err);
    }
  }, 600);
}

btnCerrarRender.addEventListener("click", () => {
  overlayRender.style.display = "none";
});

btnDescargarVideoFinal.addEventListener("click", () => {
  if (!canalActual || !proyectoActual) return;
  window.location.href = `/api/descargar_video?canal=${encodeURIComponent(canalActual)}&proyecto=${encodeURIComponent(proyectoActual)}`;
});

btnAbrirCarpetaSalida.addEventListener("click", async () => {
  await fetch("/api/abrir_carpeta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ canal: canalActual, proyecto: proyectoActual })
  });
});


// =============================================================================
// 5. EVENTOS DE CANALES Y MODAL NUEVO PROYECTO
// =============================================================================

function actualizarPreviewCarpeta() {
  const num = nuevoNumeroVideo.value || "1";
  const nombre = nuevoNombreCorto.value.trim() || "pequi video";
  const fecha = nuevaFechaPub.value.trim() || "22 nov 26";
  previewNombreCarpeta.textContent = `v${num} ${nombre} ${fecha}`;
}

function configurarEventos() {
  selectCanal.addEventListener("change", async (e) => {
    canalActual = e.target.value;
    const res = await fetch("/api/canales");
    const data = await res.json();
    const canalObj = data.canales.find(c => c.nombre === canalActual);
    if (canalObj) {
      actualizarSelectorProyectos(canalObj.proyectos);
    }
  });

  selectProyecto.addEventListener("change", (e) => {
    proyectoActual = e.target.value;
    cargarProyecto(canalActual, proyectoActual);
  });

  // Escuchar cambios en los campos para actualizar la vista previa en vivo del nombre de carpeta
  nuevoNumeroVideo.addEventListener("input", actualizarPreviewCarpeta);
  nuevoNombreCorto.addEventListener("input", actualizarPreviewCarpeta);
  nuevaFechaPub.addEventListener("input", actualizarPreviewCarpeta);

  // Modal Configurar Ubicación de Carpeta
  const btnConfigurarRutaCanal = document.getElementById("btnConfigurarRutaCanal");
  const modalConfigurarRuta = document.getElementById("modalConfigurarRuta");
  const configCanalNombre = document.getElementById("configCanalNombre");
  const configRutaCarpeta = document.getElementById("configRutaCarpeta");
  const btnCancelarConfigRuta = document.getElementById("btnCancelarConfigRuta");
  const btnGuardarConfigRuta = document.getElementById("btnGuardarConfigRuta");

  btnConfigurarRutaCanal.addEventListener("click", async () => {
    configCanalNombre.value = canalActual;
    const res = await fetch("/api/canales");
    const data = await res.json();
    const cObj = data.canales.find(c => c.nombre === canalActual);
    configRutaCarpeta.value = cObj ? cObj.ruta : "";
    modalConfigurarRuta.style.display = "flex";
  });

  btnCancelarConfigRuta.addEventListener("click", () => {
    modalConfigurarRuta.style.display = "none";
  });

  btnGuardarConfigRuta.addEventListener("click", async () => {
    const canal = configCanalNombre.value.trim();
    const ruta = configRutaCarpeta.value.trim();
    if (!canal || !ruta) {
      mostrarNotificacion("Por favor ingresa la ruta de la carpeta.", "info");
      return;
    }

    try {
      const res = await fetch("/api/canales/configurar_ruta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ canal, ruta })
      });
      const data = await res.json();
      if (data.ok) {
        modalConfigurarRuta.style.display = "none";
        mostrarNotificacion("✓ Ubicación vinculada correctamente a: " + data.ruta);
        await cargarCanales();
        selectCanal.value = canal;
        canalActual = canal;
        const resCanales = await fetch("/api/canales");
        const dataCanales = await resCanales.json();
        const cObj = dataCanales.canales.find(c => c.nombre === canal);
        if (cObj) {
          actualizarSelectorProyectos(cObj.proyectos);
        }
      } else {
        mostrarNotificacion("Error: " + data.error, "error");
      }
    } catch (err) {
      mostrarNotificacion("Error de conexión: " + err, "error");
    }
  });

  btnNuevoProyecto.addEventListener("click", async () => {
    nuevoCanalNombre.value = canalActual || "kids studio";
    
    // Consultar el siguiente número correlativo al backend
    try {
      const res = await fetch(`/api/siguiente_video?canal=${encodeURIComponent(nuevoCanalNombre.value)}`);
      const data = await res.json();
      nuevoNumeroVideo.value = data.numero || 1;
      nuevaFechaPub.value = data.fecha_sugerida || "22 nov 26";
      nuevoNombreCorto.value = "pequi ";
      actualizarPreviewCarpeta();
    } catch (err) {
      console.warn("No se pudo obtener siguiente número:", err);
    }
    
    modalNuevoProyecto.style.display = "flex";
  });

  btnCancelarNuevoProyecto.addEventListener("click", () => {
    modalNuevoProyecto.style.display = "none";
  });

  btnConfirmarNuevoProyecto.addEventListener("click", async () => {
    const canal = nuevoCanalNombre.value.trim();
    const numero = nuevoNumeroVideo.value;
    const nombreCorto = nuevoNombreCorto.value.trim();
    const fecha = nuevaFechaPub.value.trim();

    if (!canal || !nombreCorto) {
      mostrarNotificacion("Por favor ingresa el canal y el nombre corto del video.", "info");
      return;
    }

    try {
      const res = await fetch("/api/canales/crear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          canal: canal,
          numero: numero,
          nombre_corto: nombreCorto,
          fecha: fecha
        })
      });
      const data = await res.json();
      if (data.ok) {
        modalNuevoProyecto.style.display = "none";
        mostrarNotificacion(`✓ Video creado: v${numero} ${nombreCorto}`);
        await cargarCanales();
        selectCanal.value = canal;
        canalActual = canal;
        const nombreProyectoCreado = data.nombre_proyecto || `v${numero} ${nombreCorto} ${fecha}`;
        selectProyecto.value = nombreProyectoCreado;
        proyectoActual = nombreProyectoCreado;
        cargarProyecto(canal, nombreProyectoCreado);
      } else {
        mostrarNotificacion("Error: " + data.error, "error");
      }
    } catch (err) {
      mostrarNotificacion("Error de conexión: " + err, "error");
    }
  });

  // Modo compilado
  btnAbrirCompilador.addEventListener("click", () => {
    modalCompilador.style.display = "flex";
  });

  btnCerrarCompilador.addEventListener("click", () => {
    modalCompilador.style.display = "none";
  });

  const btnAutocompletarVideosCompilador = document.getElementById("btnAutocompletarVideosCompilador");
  if (btnAutocompletarVideosCompilador) {
    btnAutocompletarVideosCompilador.addEventListener("click", () => {
      if (!datosProyecto || !datosProyecto.guion) return;
      const textarea = document.getElementById("compiladorListaVideos");
      const rutas = [];
      const escenas = datosProyecto.guion.escenas || [];
      escenas.forEach((escena) => {
        if (escena.activa !== false) {
          rutas.push(`${canalActual}/${proyectoActual}/escenas/${escena.video}`);
        }
      });
      if (rutas.length > 0) {
        textarea.value = rutas.join("\n");
        mostrarNotificacion(`✓ ${rutas.length} escenas añadidas a la lista`);
      } else {
        mostrarNotificacion("No hay escenas activas en el proyecto actual", "info");
      }
    });
  }

  btnEjecutarCompilacion.addEventListener("click", async () => {
    const texto = document.getElementById("compiladorListaVideos").value.trim();
    const salida = document.getElementById("compiladorNombreSalida").value.trim() || "compilacion_larga.mp4";
    const lineas = texto.split("\n").map(l => l.trim()).filter(l => l.length > 0);

    if (lineas.length === 0) {
      mostrarNotificacion("Ingresa al menos una ruta de video.", "info");
      return;
    }

    modalCompilador.style.display = "none";
    overlayRender.style.display = "flex";
    renderProgressBar.style.width = "20%";
    renderEstado.textContent = "Compilando videos seleccionados...";
    renderLogOutput.textContent = `Uniendo ${lineas.length} videos en '${salida}'...\n`;
    renderAcciones.style.display = "none";

    const formatoComp = compiladorFormato ? compiladorFormato.value : "16:9";

    try {
      const res = await fetch("/api/compilar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ videos: lineas, salida: salida, formato: formatoComp })
      });
      const data = await res.json();
      iniciarSondeoProgreso();
    } catch (err) {
      renderEstado.textContent = "Error al iniciar compilación: " + err;
      renderAcciones.style.display = "flex";
    }
  });
}

// Iniciar aplicación
document.addEventListener("DOMContentLoaded", inicializar);
