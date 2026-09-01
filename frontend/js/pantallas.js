// Dashboard, planes y suscripciones, y recepcion.

// --- DASHBOARD ---

// Chart.js llega por CDN. Si el gimnasio esta sin internet no existe, y el
// resto del panel tiene que seguir funcionando igual.
const COLOR_LINEA = "#3b82f6";
const COLOR_REJILLA = "#334155";

let graficoAsistencias = null;
let graficoHorasPico = null;

async function cargarDashboard() {
  try {
    // Los KPIs y las series los cuenta la base. Antes se descargaba el padron
    // entero para contarlo en el navegador, lo que ademas obligaba a mandar
    // los datos de cada socio para poder mostrar un total.
    //
    // Los catalogos siguen haciendo falta para la lista de vencimientos, que
    // necesita el nombre de cada socio.
    const [resumen, porDia, porHora] = await Promise.all([
      apiFetch("/estadisticas/resumen"),
      apiFetch("/estadisticas/asistencias-por-dia?dias=7"),
      apiFetch("/estadisticas/horas-pico?dias=30"),
      cargarCatalogos()
    ]);

    pintarKpis(resumen);
    pintarGraficoAsistencias(porDia);
    pintarHorasPico(porHora);
    pintarProximosVencimientos();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) salir();
  }
}

function pintarKpis(resumen) {
  document.getElementById("kpi-total-miembros").textContent = resumen.total_socios;
  document.getElementById("kpi-activos").textContent = resumen.suscripciones_activas;
  document.getElementById("kpi-vencer").textContent = resumen.suscripciones_por_vencer;
  document.getElementById("kpi-vencidos").textContent = resumen.suscripciones_vencidas;
  document.getElementById("kpi-asistencias-hoy").textContent = resumen.asistencias_hoy;
  document.getElementById("kpi-ingresos").textContent = `$${resumen.ingresos_del_mes}`;
}

const DIAS_CORTOS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

function etiquetaDia(iso) {
  const dia = new Date(`${iso}T00:00:00`);
  return `${DIAS_CORTOS[dia.getDay()]} ${iso.slice(8, 10)}`;
}

/** Ejes comunes: las dos series son cuentas enteras. */
function ejesDeConteo() {
  return {
    x: { grid: { color: COLOR_REJILLA } },
    y: { grid: { color: COLOR_REJILLA }, beginAtZero: true, ticks: { precision: 0 } }
  };
}

function dibujar(idLienzo, anterior, config) {
  const lienzo = document.getElementById(idLienzo);
  if (!lienzo || typeof Chart === "undefined") return null;

  // Chart.js no admite dos instancias sobre el mismo canvas, y volver al
  // dashboard lo recrearia.
  if (anterior) anterior.destroy();
  return new Chart(lienzo, config);
}

function pintarGraficoAsistencias(porDia) {
  graficoAsistencias = dibujar("chartAsistencias", graficoAsistencias, {
    type: "line",
    data: {
      labels: porDia.map(d => etiquetaDia(d.dia)),
      datasets: [{
        label: "Asistencias",
        data: porDia.map(d => d.asistencias),
        borderColor: COLOR_LINEA,
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: ejesDeConteo()
    }
  });
}

/**
 * A que hora viene la gente. Sirve para decidir turnos y horarios de clase.
 *
 * El API devuelve las 24 franjas siempre, incluidas las de cero: un eje al que
 * le faltan las horas vacias exagera los picos. Se destacan las tres horas mas
 * concurridas, que es lo unico que se mira de este grafico.
 */
function pintarHorasPico(porHora) {
  const maximos = [...porHora]
    .sort((a, b) => b.asistencias - a.asistencias)
    .slice(0, 3)
    .filter(f => f.asistencias > 0)
    .map(f => f.hora);

  graficoHorasPico = dibujar("chartHorasPico", graficoHorasPico, {
    type: "bar",
    data: {
      labels: porHora.map(f => `${String(f.hora).padStart(2, "0")}:00`),
      datasets: [{
        label: "Asistencias",
        data: porHora.map(f => f.asistencias),
        backgroundColor: porHora.map(f =>
          maximos.includes(f.hora) ? COLOR_LINEA : "rgba(59, 130, 246, 0.25)"
        ),
        borderRadius: 4
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: ejesDeConteo()
    }
  });
}

/** El objetivo declarado del sistema: avisar de lo que esta por vencer. */
function pintarProximosVencimientos() {
  const caja = document.getElementById("lista-por-vencer");
  const porVencer = catalogo.suscripciones
    .filter(s => s.estatus === "por_vencer")
    .sort((a, b) => a.fecha_fin.localeCompare(b.fecha_fin));

  if (porVencer.length === 0) {
    caja.innerHTML = '<p class="text-muted small mb-0">Ninguna suscripción está por vencer.</p>';
    return;
  }

  caja.innerHTML = porVencer.map(s => `
    <div class="d-flex align-items-center mb-3">
      ${avatar(nombreMiembro(s.miembro_id))}
      <div class="flex-grow-1 overflow-hidden">
        <div class="fw-semibold text-truncate">${esc(nombreMiembro(s.miembro_id))}</div>
        <div class="text-muted small">
          <span class="font-monospace">${idSocio(s.miembro_id)}</span> · vence el ${fecha(s.fecha_fin)}
        </div>
      </div>
      <span class="badge bg-warning bg-opacity-10 text-warning">${diasRestantes(s.fecha_fin)}d</span>
    </div>
  `).join("");
}

function diasRestantes(fechaFin) {
  const fin = new Date(`${fechaFin}T00:00:00`);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return Math.round((fin - hoy) / 86400000);
}

// --- PLANES Y SUSCRIPCIONES ---
async function cargarSuscripciones() {
  const tbody = document.getElementById("tabla-suscripciones");
  cargando(tbody, 6);
  try {
    await cargarCatalogos();
    pintarPlanes();
    prepararFormularioSuscripcion();
    pintarSuscripciones();
  } catch (err) {
    manejarError(err, tbody, 6, "Error al cargar suscripciones");
  }
}

function pintarPlanes() {
  const contenedor = document.getElementById("contenedor-planes");
  const planes = catalogo.planes.filter(p => p.activo);

  if (planes.length === 0) {
    contenedor.innerHTML =
      '<div class="col-12 text-center text-muted py-4">Todavía no hay planes cargados. Usa "Nuevo Plan" para agregar uno.</div>';
    return;
  }

  contenedor.innerHTML = planes.map(p => `
    <div class="col-md-4">
      <div class="kpi-card p-4 text-center h-100 d-flex flex-column justify-content-between">
        <div>
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-primary bg-opacity-10 text-primary">#${p.id}</span>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" onclick="editarPlan(${p.id})" title="Editar Plan">
                <i class="bi bi-pencil-square"></i>
              </button>
              <button class="btn btn-outline-danger" onclick="eliminarPlan(${p.id})" title="Eliminar / Retirar Plan">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
          <h4 class="fw-bold text-primary">${esc(p.nombre)}</h4>
          <h2 class="my-3 fw-bold">$${esc(p.precio)}
            <span class="fs-6 text-muted">/ ${p.duracion_dias} días</span>
          </h2>
          <p class="text-muted small">${esc(p.descripcion) || "Sin descripción."}</p>
        </div>
        <button class="btn btn-outline-primary w-100 mt-3" onclick="asignarPlan(${p.id})">
          <i class="bi bi-person-plus me-1"></i> Asignar a Socio
        </button>
      </div>
    </div>
  `).join("");
}

function abrirNuevoPlan() {
  document.getElementById("form-plan").reset();
  document.getElementById("p-id").value = "";
  document.getElementById("modalPlanTitulo").innerHTML = '<i class="bi bi-tag-fill me-2 text-primary"></i>Registrar Plan';
  document.getElementById("p-boton-submit").textContent = "Guardar Plan";
  document.getElementById("p-error").classList.add("d-none");
  new bootstrap.Modal(document.getElementById("modalPlan")).show();
}

function editarPlan(planId) {
  const plan = catalogo.planes.find(p => p.id === planId);
  if (!plan) return;

  document.getElementById("p-id").value = plan.id;
  document.getElementById("p-nombre").value = plan.nombre;
  document.getElementById("p-descripcion").value = plan.descripcion || "";
  document.getElementById("p-duracion").value = plan.duracion_dias;
  document.getElementById("p-precio").value = plan.precio;

  document.getElementById("modalPlanTitulo").innerHTML = '<i class="bi bi-pencil-square me-2 text-primary"></i>Editar Plan';
  document.getElementById("p-boton-submit").textContent = "Actualizar Plan";
  document.getElementById("p-error").classList.add("d-none");
  new bootstrap.Modal(document.getElementById("modalPlan")).show();
}

async function guardarPlan(e) {
  e.preventDefault();
  const planId = document.getElementById("p-id").value;
  const datos = {
    nombre: document.getElementById("p-nombre").value.trim(),
    descripcion: document.getElementById("p-descripcion").value.trim() || null,
    duracion_dias: Number(document.getElementById("p-duracion").value),
    precio: document.getElementById("p-precio").value
  };

  try {
    if (planId) {
      await apiFetch(`/planes/${planId}`, "PUT", datos);
    } else {
      await apiFetch("/planes/", "POST", datos);
    }
    cerrarModal("modalPlan", "form-plan", "p-error");
    await cargarCatalogos();
    pintarPlanes();
    prepararFormularioSuscripcion();
  } catch (err) {
    mostrarErrorEnFormulario("p-error", err);
  }
}

async function eliminarPlan(planId) {
  const plan = catalogo.planes.find(p => p.id === planId);
  const nombre = plan ? `"${plan.nombre}"` : "este plan";

  if (!confirm(`¿Deseas eliminar el plan ${nombre}?`)) return;

  try {
    await apiFetch(`/planes/${planId}`, "DELETE");
    await cargarCatalogos();
    pintarPlanes();
    prepararFormularioSuscripcion();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();

    // Si tiene suscripciones, el API responde 409. Ofrecer desactivar el plan.
    if (confirm(`El plan ${nombre} tiene suscripciones registradas y no puede borrarse físicamente para proteger el historial.\n\n¿Deseas desactivarlo para que no aparezca en nuevas asignaciones?`)) {
      try {
        await apiFetch(`/planes/${planId}`, "PUT", { activo: false });
        await cargarCatalogos();
        pintarPlanes();
        prepararFormularioSuscripcion();
      } catch (errDesactivar) {
        alert(errDesactivar.message);
      }
    }
  }
}

/** Repinta desde el catalogo ya cargado: el filtro no vuelve a consultar. */
function pintarSuscripciones() {
  const tbody = document.getElementById("tabla-suscripciones");
  const filtro = document.getElementById("filtro-estatus").value;

  const filas = filtro
    ? catalogo.suscripciones.filter(s => s.estatus === filtro)
    : catalogo.suscripciones;

  if (filas.length === 0) {
    vacio(tbody, 6, filtro ? "No hay suscripciones con ese estatus." : "Todavía no hay suscripciones.");
    return;
  }

  tbody.innerHTML = filas.map(s => `
    <tr>
      <td class="d-flex align-items-center">
        ${avatar(nombreMiembro(s.miembro_id))}
        <div>
          <div class="fw-bold">${esc(nombreMiembro(s.miembro_id))}</div>
          <div class="text-muted small font-monospace">${idSocio(s.miembro_id)}</div>
        </div>
      </td>
      <td>${esc(nombrePlan(s.plan_id))}</td>
      <td class="text-muted small">${fecha(s.fecha_inicio)} → ${fecha(s.fecha_fin)}</td>
      <td>${badgeEstatus(s.estatus)}</td>
      <td>$${esc(s.precio_pagado)}</td>
      <td>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-success" onclick="renovarSuscripcion(${s.id})" title="Renovar Suscripción">
            <i class="bi bi-arrow-repeat"></i> Renovar
          </button>
          <button class="btn btn-outline-danger" onclick="eliminarSuscripcion(${s.id})" title="Desasignar / Eliminar Suscripción">
            <i class="bi bi-person-x"></i> Desasignar
          </button>
        </div>
      </td>
    </tr>
  `).join("");
}

function prepararFormularioSuscripcion() {
  llenarSelect(
    "s-miembro",
    catalogo.miembros.filter(m => m.activo).map(m => ({ valor: m.id, texto: `${m.nombre_completo} (${idSocio(m.id)})` })),
    "No hay socios activos"
  );
  llenarSelect(
    "s-plan",
    catalogo.planes
      .filter(p => p.activo)
      .map(p => ({ valor: p.id, texto: `${p.nombre} · $${p.precio} (${p.duracion_dias}d)` })),
    "No hay planes activos"
  );

  proponerVigencia();
}

/**
 * Propone fecha de fin y precio segun el plan y el socio elegido.
 *
 * LÓGICA DE RENOVACIÓN ACUMULATIVA:
 * Si el socio tiene una suscripcion activa con dias restantes (fecha_fin >= hoy),
 * el nuevo periodo se acumula a partir de su vencimiento actual (fecha_fin)
 * en lugar de empezar hoy.
 */
function proponerVigencia() {
  const miembroId = Number(document.getElementById("s-miembro").value);
  const plan = catalogo.planes.find(p => p.id === Number(document.getElementById("s-plan").value));
  const aviso = document.getElementById("s-aviso-renovacion");
  const hiddenRenovada = document.getElementById("s-renovada-de-id");

  if (!plan) return;

  const hoyStr = new Date().toISOString().slice(0, 10);
  const vigente = miembroId ? vigenciaDe(miembroId) : null;

  let fechaInicioPropuesta = hoyStr;
  let esRenovacionActiva = false;

  if (vigente && vigente.fecha_fin >= hoyStr) {
    // Si aún tiene vigencia, sumamos el nuevo periodo a partir de su vencimiento
    fechaInicioPropuesta = vigente.fecha_fin;
    esRenovacionActiva = true;
    if (hiddenRenovada) hiddenRenovada.value = String(vigente.id);
  } else {
    if (hiddenRenovada) hiddenRenovada.value = "";
  }

  document.getElementById("s-inicio").value = fechaInicioPropuesta;

  const fin = new Date(`${fechaInicioPropuesta}T00:00:00`);
  fin.setDate(fin.getDate() + plan.duracion_dias);
  const fechaFinCalculada = fin.toISOString().slice(0, 10);

  document.getElementById("s-fin").value = fechaFinCalculada;
  document.getElementById("s-precio").value = plan.precio;

  if (aviso) {
    if (esRenovacionActiva) {
      aviso.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i> <strong>Renovación continua:</strong> El socio tiene vigencia activa hasta el ${fecha(vigente.fecha_fin)}. El nuevo periodo de ${plan.duracion_dias} días se acumula hasta el <strong>${fecha(fechaFinCalculada)}</strong>.`;
      aviso.classList.remove("d-none");
    } else {
      aviso.classList.add("d-none");
    }
  }
}

function abrirModalAsignar() {
  prepararFormularioSuscripcion();
  proponerVigencia();
  document.getElementById("modalSuscripcionTitulo").innerHTML = '<i class="bi bi-card-checklist me-2 text-primary"></i>Asignar Plan a Socio';
  document.getElementById("s-boton-submit").textContent = "Asignar Suscripción";
  new bootstrap.Modal(document.getElementById("modalSuscripcion")).show();
}

function abrirAsignarSuscripcionParaMiembro(miembroId) {
  prepararFormularioSuscripcion();
  document.getElementById("s-miembro").value = String(miembroId);
  proponerVigencia();
  document.getElementById("modalSuscripcionTitulo").innerHTML = '<i class="bi bi-card-checklist me-2 text-primary"></i>Asignar / Renovar Plan';
  document.getElementById("s-boton-submit").textContent = "Guardar Suscripción";
  new bootstrap.Modal(document.getElementById("modalSuscripcion")).show();
}

function asignarPlan(planId) {
  prepararFormularioSuscripcion();
  document.getElementById("s-plan").value = String(planId);
  proponerVigencia();
  document.getElementById("modalSuscripcionTitulo").innerHTML = '<i class="bi bi-card-checklist me-2 text-primary"></i>Asignar Plan a Socio';
  document.getElementById("s-boton-submit").textContent = "Asignar Suscripción";
  new bootstrap.Modal(document.getElementById("modalSuscripcion")).show();
}

function renovarSuscripcion(suscripcionId) {
  const suscripcion = catalogo.suscripciones.find(s => s.id === suscripcionId);
  if (!suscripcion) return;

  prepararFormularioSuscripcion();
  document.getElementById("s-miembro").value = String(suscripcion.miembro_id);
  document.getElementById("s-plan").value = String(suscripcion.plan_id);
  proponerVigencia();
  document.getElementById("modalSuscripcionTitulo").innerHTML = '<i class="bi bi-arrow-repeat me-2 text-success"></i>Renovar Suscripción de Socio';
  document.getElementById("s-boton-submit").textContent = "Confirmar Renovación";
  new bootstrap.Modal(document.getElementById("modalSuscripcion")).show();
}

async function guardarSuscripcion(e) {
  e.preventDefault();
  const renovadaDeId = document.getElementById("s-renovada-de-id")?.value;

  const datos = {
    miembro_id: Number(document.getElementById("s-miembro").value),
    plan_id: Number(document.getElementById("s-plan").value),
    fecha_inicio: document.getElementById("s-inicio").value,
    fecha_fin: document.getElementById("s-fin").value,
    precio_pagado: document.getElementById("s-precio").value,
    renovada_de_id: renovadaDeId ? Number(renovadaDeId) : null
  };
  try {
    await apiFetch("/suscripciones/", "POST", datos);
    cerrarModal("modalSuscripcion", "form-suscripcion", "s-error");
    cargarSuscripciones();
  } catch (err) {
    mostrarErrorEnFormulario("s-error", err);
  }
}

function eliminarSuscripcion(id) {
  eliminarRecurso("suscripciones", id, "¿Deseas desasignar / eliminar esta suscripción del socio?", cargarSuscripciones);
}

// --- RECEPCION / CHECK-IN Y BUSQUEDA DINAMICA ---
let temporizadorCheckin = null;

async function prepararCheckin() {
  document.getElementById("checkin-resultado").innerHTML = "";
  const sugerencias = document.getElementById("checkin-sugerencias");
  if (sugerencias) {
    sugerencias.innerHTML = "";
    sugerencias.classList.add("d-none");
  }
  const inputCheckin = document.getElementById("checkin-id");
  if (inputCheckin) {
    inputCheckin.value = "";
    inputCheckin.focus();
  }
  try {
    await cargarCatalogos();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) salir();
  }
}

/** Búsqueda dinámica en tiempo real mientras se escribe en el check-in */
function alEscribirCheckin() {
  clearTimeout(temporizadorCheckin);
  const consulta = document.getElementById("checkin-id").value.trim();
  const cajaSugerencias = document.getElementById("checkin-sugerencias");

  if (!consulta || consulta.length < 2) {
    if (cajaSugerencias) {
      cajaSugerencias.innerHTML = "";
      cajaSugerencias.classList.add("d-none");
    }
    return;
  }

  temporizadorCheckin = setTimeout(async () => {
    try {
      const encontrados = await apiFetch(`/miembros/buscar?q=${encodeURIComponent(consulta)}&limite=6`);
      if (!cajaSugerencias) return;

      if (encontrados.length === 0) {
        cajaSugerencias.innerHTML = '<div class="p-2 text-muted small">No se encontraron socios que coincidan.</div>';
        cajaSugerencias.classList.remove("d-none");
        return;
      }

      cajaSugerencias.innerHTML = `
        <div class="list-group">
          ${encontrados.map(m => {
            const vigente = vigenciaDe(m.id);
            return `
            <button type="button" class="list-group-item list-group-item-action bg-dark text-white border-secondary d-flex justify-content-between align-items-center py-2" onclick="seleccionarYValidarSocio(${m.id})">
              <div class="d-flex align-items-center">
                ${avatar(m.nombre_completo)}
                <div>
                  <div class="fw-semibold">${esc(m.nombre_completo)} <span class="font-monospace text-primary small">${idSocio(m.id)}</span></div>
                  <div class="small text-muted">${m.telefono ? esc(m.telefono) + ' · ' : ''}${vigente ? 'Vence: ' + fecha(vigente.fecha_fin) : 'Sin suscripción'}</div>
                </div>
              </div>
              <div>
                ${vigente ? badgeEstatus(vigente.estatus) : '<span class="badge bg-secondary">Sin Plan</span>'}
                <span class="btn btn-sm btn-primary ms-2"><i class="bi bi-qr-code"></i> Validar</span>
              </div>
            </button>`;
          }).join("")}
        </div>
      `;
      cajaSugerencias.classList.remove("d-none");
    } catch (err) {
      // Ignorar errores de sugerencias en segundo plano
    }
  }, 200);
}

function seleccionarYValidarSocio(miembroId) {
  const inputCheckin = document.getElementById("checkin-id");
  if (inputCheckin) inputCheckin.value = String(miembroId);

  const cajaSugerencias = document.getElementById("checkin-sugerencias");
  if (cajaSugerencias) {
    cajaSugerencias.innerHTML = "";
    cajaSugerencias.classList.add("d-none");
  }

  ejecutarValidacion(miembroId);
}

/**
 * Valida el acceso por ID o por Nombre del socio.
 */
async function validarAcceso(e) {
  e.preventDefault();
  const consulta = document.getElementById("checkin-id").value.trim();
  const cajaSugerencias = document.getElementById("checkin-sugerencias");
  if (cajaSugerencias) cajaSugerencias.classList.add("d-none");

  if (!consulta) return;

  const idCandidato = consulta.replace(/^#/, "").trim();

  // Si es un ID numérico directo
  if (/^\d+$/.test(idCandidato)) {
    return ejecutarValidacion(Number(idCandidato));
  }

  // Si es una búsqueda por texto / nombre
  const caja = document.getElementById("checkin-resultado");
  caja.innerHTML = '<div class="text-muted"><i class="bi bi-hourglass-split me-1"></i> Buscando socio...</div>';

  try {
    const encontrados = await apiFetch(`/miembros/buscar?q=${encodeURIComponent(consulta)}&limite=5`);

    if (encontrados.length === 0) {
      caja.innerHTML = veredicto("danger", "x-circle-fill", "ACCESO DENEGADO", `No se encontró ningún socio con el término "${consulta}"`);
      return;
    }

    if (encontrados.length === 1) {
      return ejecutarValidacion(encontrados[0].id);
    }

    // Múltiples coincidencias: mostrar opciones claras para seleccionar y validar
    caja.innerHTML = `
      <div class="alert alert-info text-start mb-3">
        <h6 class="fw-bold mb-2"><i class="bi bi-people-fill me-1"></i> Múltiples socios encontrados para "${esc(consulta)}":</h6>
        <div class="list-group">
          ${encontrados.map(m => `
            <button type="button" class="list-group-item list-group-item-action bg-dark text-white border-secondary d-flex justify-content-between align-items-center py-2" onclick="seleccionarYValidarSocio(${m.id})">
              <span><strong>${esc(m.nombre_completo)}</strong> <span class="font-monospace text-primary">${idSocio(m.id)}</span></span>
              <span class="btn btn-sm btn-primary">Validar este socio</span>
            </button>
          `).join("")}
        </div>
      </div>
    `;
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    caja.innerHTML = veredicto("warning", "exclamation-triangle-fill", "ERROR DE BÚSQUEDA", err.message);
  }
}

async function ejecutarValidacion(miembroId) {
  const caja = document.getElementById("checkin-resultado");
  caja.innerHTML = '<div class="text-muted"><i class="bi bi-hourglass-split me-1"></i> Validando acceso...</div>';

  let miembro;
  try {
    miembro = await apiFetch(`/miembros/${miembroId}`);
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    caja.innerHTML = veredicto("danger", "x-circle-fill", "ACCESO DENEGADO", "Socio no encontrado");
    return;
  }

  if (!miembro.activo) {
    caja.innerHTML = veredicto(
      "danger",
      "x-circle-fill",
      "ACCESO DENEGADO",
      `${idSocio(miembro.id)} · ${miembro.nombre_completo} está dado de baja`
    );
    return;
  }

  const vigente = vigenciaDe(miembro.id);
  if (!vigente) {
    caja.innerHTML =
      veredicto(
        "danger",
        "x-circle-fill",
        "ACCESO DENEGADO",
        `${idSocio(miembro.id)} · ${miembro.nombre_completo} · Sin suscripción vigente`
      ) +
      botonRegistrarIgual(miembro.id);
    return;
  }

  try {
    await apiFetch("/asistencias/", "POST", {
      miembro_id: miembro.id,
      suscripcion_id: vigente.id
    });
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    caja.innerHTML = veredicto("warning", "exclamation-triangle-fill", "NO SE PUDO REGISTRAR", err.message);
    return;
  }

  const restantes = diasRestantes(vigente.fecha_fin);
  const detalle =
    vigente.estatus === "por_vencer"
      ? `${idSocio(miembro.id)} · ${miembro.nombre_completo} · Vence en ${restantes} día(s) (${fecha(vigente.fecha_fin)})`
      : `${idSocio(miembro.id)} · ${miembro.nombre_completo} · Vigente hasta ${fecha(vigente.fecha_fin)}`;

  caja.innerHTML = veredicto(
    vigente.estatus === "por_vencer" ? "warning" : "success",
    "check-circle-fill",
    "ACCESO PERMITIDO",
    detalle
  );
  document.getElementById("form-checkin").reset();
}

/** Registro de Pase del Día / Visita Rápida */
async function registrarPaseDia(e) {
  e.preventDefault();
  const nombre = document.getElementById("pd-nombre").value.trim() || "Visitante";
  const monto = parseFloat(document.getElementById("pd-monto").value) || 50.0;
  const notas = document.getElementById("pd-notas").value.trim() || null;
  const cajaError = document.getElementById("pd-error");

  cajaError.classList.add("d-none");

  try {
    const res = await apiFetch("/asistencias/pase-dia", "POST", {
      nombre,
      monto,
      notas
    });

    cerrarModal("modalPaseDia", "form-pase-dia", "pd-error");

    const caja = document.getElementById("checkin-resultado");
    caja.innerHTML = veredicto(
      "success",
      "ticket-perforated-fill",
      `ACCESO PERMITIDO · PASE DEL DÍA ($${monto.toFixed(2)})`,
      `${res.nombre_visitante} · Entrada registrada correctamente`
    );

    await cargarCatalogos();
  } catch (err) {
    mostrarErrorEnFormulario("pd-error", err);
  }
}

function veredicto(color, icono, titulo, detalle) {
  return `
    <div class="alert alert-${color} d-flex align-items-center justify-content-center p-3 mb-2 text-start">
      <i class="bi bi-${icono} fs-2 me-3 flex-shrink-0"></i>
      <div class="flex-grow-1">
        <h5 class="mb-0 fw-bold">${esc(titulo)}</h5>
        <div>${esc(detalle)}</div>
      </div>
    </div>`;
}

function botonRegistrarIgual(miembroId) {
  return `
    <div class="mt-2">
      <button class="btn btn-outline-secondary btn-sm" onclick="registrarEntradaSinVigencia(${miembroId})">
        <i class="bi bi-pencil-square me-1"></i> Registrar la entrada de todos modos
      </button>
    </div>`;
}

async function registrarEntradaSinVigencia(miembroId) {
  const caja = document.getElementById("checkin-resultado");
  try {
    await apiFetch("/asistencias/", "POST", { miembro_id: miembroId, suscripcion_id: null });
    caja.innerHTML = veredicto(
      "secondary",
      "pencil-square",
      "ENTRADA REGISTRADA",
      `${idSocio(miembroId)} · Queda anotada sin suscripción vigente`
    );
    document.getElementById("form-checkin").reset();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    caja.innerHTML = veredicto("warning", "exclamation-triangle-fill", "NO SE PUDO REGISTRAR", err.message);
  }
}
