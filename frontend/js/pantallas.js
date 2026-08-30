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
      '<div class="col-12 text-center text-muted py-4">Todavía no hay planes cargados.</div>';
    return;
  }

  contenedor.innerHTML = planes.map(p => `
    <div class="col-md-4">
      <div class="kpi-card p-4 text-center h-100 d-flex flex-column justify-content-between">
        <div>
          <h4 class="fw-bold text-primary">${esc(p.nombre)}</h4>
          <h2 class="my-3 fw-bold">$${esc(p.precio)}
            <span class="fs-6 text-muted">/ ${p.duracion_dias} días</span>
          </h2>
          <p class="text-muted small">${esc(p.descripcion) || "Sin descripción."}</p>
        </div>
        <button class="btn btn-outline-primary w-100 mt-3" onclick="asignarPlan(${p.id})">
          Asignar a Socio
        </button>
      </div>
    </div>
  `).join("");
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
        <button class="btn btn-sm btn-outline-danger" onclick="eliminarSuscripcion(${s.id})" title="Eliminar">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

function prepararFormularioSuscripcion() {
  llenarSelect(
    "s-miembro",
    catalogo.miembros.filter(m => m.activo).map(m => ({ valor: m.id, texto: m.nombre_completo })),
    "No hay socios activos"
  );
  llenarSelect(
    "s-plan",
    catalogo.planes
      .filter(p => p.activo)
      .map(p => ({ valor: p.id, texto: `${p.nombre} · $${p.precio}` })),
    "No hay planes activos"
  );

  document.getElementById("s-inicio").value = new Date().toISOString().slice(0, 10);
  proponerVigencia();
}

/**
 * Propone fecha de fin y precio segun el plan elegido. El API igual exige los
 * dos datos: esto es una comodidad de la pantalla, no una regla de negocio.
 */
function proponerVigencia() {
  const plan = catalogo.planes.find(p => p.id === Number(document.getElementById("s-plan").value));
  const inicio = document.getElementById("s-inicio").value;
  if (!plan || !inicio) return;

  const fin = new Date(`${inicio}T00:00:00`);
  fin.setDate(fin.getDate() + plan.duracion_dias);
  document.getElementById("s-fin").value = fin.toISOString().slice(0, 10);
  document.getElementById("s-precio").value = plan.precio;
}

/** Abre el alta con el plan ya elegido. Antes solo mostraba un aviso falso. */
function asignarPlan(planId) {
  prepararFormularioSuscripcion();
  document.getElementById("s-plan").value = String(planId);
  proponerVigencia();
  new bootstrap.Modal(document.getElementById("modalSuscripcion")).show();
}

async function guardarSuscripcion(e) {
  e.preventDefault();
  const datos = {
    miembro_id: Number(document.getElementById("s-miembro").value),
    plan_id: Number(document.getElementById("s-plan").value),
    fecha_inicio: document.getElementById("s-inicio").value,
    fecha_fin: document.getElementById("s-fin").value,
    // Se manda como texto: el precio es Decimal en el API y pasarlo por Number
    // introduce el redondeo binario que justamente se quiere evitar.
    precio_pagado: document.getElementById("s-precio").value
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
  eliminarRecurso("suscripciones", id, "¿Deseas eliminar esta suscripción?", cargarSuscripciones);
}

async function guardarPlan(e) {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("p-nombre").value,
    descripcion: document.getElementById("p-descripcion").value || null,
    duracion_dias: Number(document.getElementById("p-duracion").value),
    precio: document.getElementById("p-precio").value
  };
  try {
    await apiFetch("/planes/", "POST", datos);
    cerrarModal("modalPlan", "form-plan", "p-error");
    cargarSuscripciones();
  } catch (err) {
    mostrarErrorEnFormulario("p-error", err);
  }
}

// --- RECEPCION / CHECK-IN ---
async function prepararCheckin() {
  document.getElementById("checkin-resultado").innerHTML = "";
  document.getElementById("checkin-id").focus();
  try {
    await cargarCatalogos();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) salir();
  }
}

/**
 * Valida el acceso y, si corresponde, registra la entrada.
 *
 * Dos cosas que antes no ocurrian: el veredicto mira el estatus real de la
 * suscripcion (antes bastaba con que el socio existiera) y la entrada queda
 * registrada (antes la pantalla no escribia nada en ninguna parte).
 */
async function validarAcceso(e) {
  e.preventDefault();
  const id = Number(document.getElementById("checkin-id").value);
  const caja = document.getElementById("checkin-resultado");
  if (!id) return;

  caja.innerHTML = '<div class="text-muted">Consultando...</div>';

  let miembro;
  try {
    miembro = await apiFetch(`/miembros/${id}`);
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
        `${idSocio(miembro.id)} · ${miembro.nombre_completo} · sin suscripción vigente`
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
      ? `${idSocio(miembro.id)} · ${miembro.nombre_completo} · vence en ${restantes} día(s)`
      : `${idSocio(miembro.id)} · ${miembro.nombre_completo} · vigente hasta ${fecha(vigente.fecha_fin)}`;

  caja.innerHTML = veredicto(
    vigente.estatus === "por_vencer" ? "warning" : "success",
    "check-circle-fill",
    "ACCESO PERMITIDO",
    detalle
  );
  document.getElementById("form-checkin").reset();
}

function veredicto(color, icono, titulo, detalle) {
  return `
    <div class="alert alert-${color} d-flex align-items-center justify-content-center p-3 mb-2">
      <i class="bi bi-${icono} fs-2 me-3"></i>
      <div class="text-start">
        <h5 class="mb-0">${esc(titulo)}</h5>
        <small>${esc(detalle)}</small>
      </div>
    </div>`;
}

/**
 * El modelo admite registrar una entrada sin suscripcion vigente para no
 * perder el dato. Se ofrece como accion explicita, no automatica: el acceso
 * se denego y quien atiende decide si igual deja pasar.
 */
function botonRegistrarIgual(miembroId) {
  return `
    <button class="btn btn-outline-secondary btn-sm" onclick="registrarEntradaSinVigencia(${miembroId})">
      <i class="bi bi-pencil-square me-1"></i> Registrar la entrada de todos modos
    </button>`;
}

async function registrarEntradaSinVigencia(miembroId) {
  const caja = document.getElementById("checkin-resultado");
  try {
    await apiFetch("/asistencias/", "POST", { miembro_id: miembroId, suscripcion_id: null });
    caja.innerHTML = veredicto(
      "secondary",
      "pencil-square",
      "ENTRADA REGISTRADA",
      `${idSocio(miembroId)} · queda anotada sin suscripción vigente`
    );
    document.getElementById("form-checkin").reset();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    caja.innerHTML = veredicto("warning", "exclamation-triangle-fill", "NO SE PUDO REGISTRAR", err.message);
  }
}
