// Pantallas de suscripciones y asistencias.
//
// Se apoyan en un catalogo en memoria porque el API devuelve ids, no nombres:
// pedir el nombre de cada miembro fila por fila serian decenas de peticiones
// para pintar una tabla.

let catalogo = { miembros: [], planes: [], suscripciones: [] };

async function cargarCatalogos() {
  const [miembros, planes, suscripciones] = await Promise.all([
    apiFetch("/miembros/"),
    apiFetch("/planes/"),
    apiFetch("/suscripciones/")
  ]);
  catalogo = { miembros, planes, suscripciones };
}

function nombreMiembro(id) {
  const miembro = catalogo.miembros.find(m => m.id === id);
  return miembro ? miembro.nombre_completo : `#${id}`;
}

function nombrePlan(id) {
  const plan = catalogo.planes.find(p => p.id === id);
  return plan ? plan.nombre : `#${id}`;
}

/** Formatea una fecha ISO (2026-08-31) como 31/08/2026. */
function fecha(iso) {
  if (!iso) return "-";
  const [anio, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

/** El API sella las horas en UTC, asi que se muestran tal cual llegan. */
function fechaHora(iso) {
  if (!iso) return "-";
  return `${fecha(iso)} ${iso.slice(11, 16)}`;
}

const ETIQUETA_ESTATUS = {
  activa: { texto: "Activa", clase: "bg-success" },
  por_vencer: { texto: "Por vencer", clase: "bg-warning text-dark" },
  vencida: { texto: "Vencida", clase: "bg-danger" }
};

function badgeEstatus(estatus) {
  const etiqueta = ETIQUETA_ESTATUS[estatus] || { texto: estatus, clase: "bg-secondary" };
  return `<span class="badge ${etiqueta.clase}">${esc(etiqueta.texto)}</span>`;
}

function llenarSelect(idSelect, opciones, textoVacio) {
  const select = document.getElementById(idSelect);
  select.innerHTML = opciones.length
    ? opciones.map(o => `<option value="${o.valor}">${esc(o.texto)}</option>`).join("")
    : `<option value="">${esc(textoVacio)}</option>`;
}

// --- SUSCRIPCIONES ---
async function cargarSuscripciones() {
  const tbody = document.getElementById("tabla-suscripciones");
  cargando(tbody, 8);
  try {
    await cargarCatalogos();
    prepararFormularioSuscripcion();
    pintarSuscripciones();
  } catch (err) {
    manejarError(err, tbody, 8, "Error al cargar suscripciones");
  }
}

/** Repinta desde el catalogo ya cargado: el filtro no vuelve a consultar. */
function pintarSuscripciones() {
  const tbody = document.getElementById("tabla-suscripciones");
  const filtro = document.getElementById("filtro-estatus").value;

  avisarVencimientos();

  const filas = filtro
    ? catalogo.suscripciones.filter(s => s.estatus === filtro)
    : catalogo.suscripciones;

  if (filas.length === 0) {
    vacio(tbody, 8, filtro ? "No hay suscripciones con ese estatus." : "Todavía no hay suscripciones.");
    return;
  }

  tbody.innerHTML = filas.map(s => `
    <tr>
      <td>${s.id}</td>
      <td>${esc(nombreMiembro(s.miembro_id))}</td>
      <td>${esc(nombrePlan(s.plan_id))}</td>
      <td>${fecha(s.fecha_inicio)}</td>
      <td>${fecha(s.fecha_fin)}</td>
      <td>${badgeEstatus(s.estatus)}</td>
      <td>$${esc(s.precio_pagado)}</td>
      <td>
        <button class="btn btn-sm btn-danger" onclick="eliminarSuscripcion(${s.id})" title="Eliminar">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

/** El objetivo del sistema: avisar de lo que esta por vencer. */
function avisarVencimientos() {
  const aviso = document.getElementById("aviso-vencimientos");
  const porVencer = catalogo.suscripciones.filter(s => s.estatus === "por_vencer");

  if (porVencer.length === 0) {
    aviso.classList.add("d-none");
    return;
  }

  const nombres = porVencer
    .map(s => `${esc(nombreMiembro(s.miembro_id))} (${fecha(s.fecha_fin)})`)
    .join(", ");
  aviso.innerHTML =
    `<i class="bi bi-exclamation-triangle"></i> <strong>${porVencer.length}</strong> ` +
    `suscripción(es) por vencer: ${nombres}`;
  aviso.classList.remove("d-none");
}

function prepararFormularioSuscripcion() {
  llenarSelect(
    "s-miembro",
    catalogo.miembros.filter(m => m.activo).map(m => ({ valor: m.id, texto: m.nombre_completo })),
    "No hay miembros activos"
  );
  llenarSelect(
    "s-plan",
    catalogo.planes.filter(p => p.activo).map(p => ({ valor: p.id, texto: `${p.nombre} · $${p.precio}` })),
    "No hay planes activos"
  );

  const hoy = new Date().toISOString().slice(0, 10);
  document.getElementById("s-inicio").value = hoy;
  proponerVigencia();
}

/**
 * Propone fecha de fin y precio a partir del plan elegido. El API igual exige
 * ambos datos: esto es una comodidad de la pantalla, no una regla de negocio.
 */
function proponerVigencia() {
  const planId = Number(document.getElementById("s-plan").value);
  const plan = catalogo.planes.find(p => p.id === planId);
  const inicio = document.getElementById("s-inicio").value;
  if (!plan || !inicio) return;

  const fin = new Date(`${inicio}T00:00:00`);
  fin.setDate(fin.getDate() + plan.duracion_dias);
  document.getElementById("s-fin").value = fin.toISOString().slice(0, 10);
  document.getElementById("s-precio").value = plan.precio;
}

async function guardarSuscripcion(e) {
  e.preventDefault();
  const datos = {
    miembro_id: Number(document.getElementById("s-miembro").value),
    plan_id: Number(document.getElementById("s-plan").value),
    fecha_inicio: document.getElementById("s-inicio").value,
    fecha_fin: document.getElementById("s-fin").value,
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

// --- ASISTENCIAS ---
async function cargarAsistencias() {
  const tbody = document.getElementById("tabla-asistencias");
  cargando(tbody, 5);
  try {
    await cargarCatalogos();
    llenarSelect(
      "a-miembro",
      catalogo.miembros.filter(m => m.activo).map(m => ({ valor: m.id, texto: m.nombre_completo })),
      "No hay miembros activos"
    );
    mostrarVigencia();

    const asistencias = await apiFetch("/asistencias/");
    if (asistencias.length === 0) return vacio(tbody, 5, "Todavía no hay entradas registradas.");

    tbody.innerHTML = asistencias.map(a => `
      <tr>
        <td>${a.id}</td>
        <td>${esc(nombreMiembro(a.miembro_id))}</td>
        <td>${fechaHora(a.registrada_en)}</td>
        <td>${a.suscripcion_id ? `#${a.suscripcion_id}` : '<span class="text-muted">sin vigencia</span>'}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarAsistencia(${a.id})" title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 5, "Error al cargar asistencias");
  }
}

/** Suscripcion no vencida del miembro, si la hay. */
function vigenciaDe(miembroId) {
  return (
    catalogo.suscripciones
      .filter(s => s.miembro_id === miembroId && s.estatus !== "vencida")
      .sort((a, b) => b.fecha_fin.localeCompare(a.fecha_fin))[0] || null
  );
}

function mostrarVigencia() {
  const caja = document.getElementById("a-vigencia");
  const miembroId = Number(document.getElementById("a-miembro").value);
  if (!miembroId) {
    caja.classList.add("d-none");
    return;
  }

  const vigente = vigenciaDe(miembroId);
  if (vigente) {
    caja.className = "alert alert-info py-2";
    caja.innerHTML =
      `Suscripción vigente hasta el <strong>${fecha(vigente.fecha_fin)}</strong> ` +
      badgeEstatus(vigente.estatus);
  } else {
    // Se avisa, pero no se bloquea: el modelo admite registrar la entrada sin
    // vigencia para no perder el dato.
    caja.className = "alert alert-warning py-2";
    caja.textContent = "Sin suscripción vigente. La entrada se registrará igual.";
  }
  caja.classList.remove("d-none");
}

async function guardarAsistencia(e) {
  e.preventDefault();
  const miembroId = Number(document.getElementById("a-miembro").value);
  const vigente = vigenciaDe(miembroId);
  const datos = {
    miembro_id: miembroId,
    // Se adjunta la vigencia del momento para que el historial conserve con
    // que suscripcion entro, aunque despues se renueve o venza.
    suscripcion_id: vigente ? vigente.id : null
  };
  try {
    await apiFetch("/asistencias/", "POST", datos);
    cerrarModal("modalAsistencia", "form-asistencia", "a-error");
    cargarAsistencias();
  } catch (err) {
    mostrarErrorEnFormulario("a-error", err);
  }
}

function eliminarAsistencia(id) {
  eliminarRecurso("asistencias", id, "¿Deseas eliminar este registro?", cargarAsistencias);
}
