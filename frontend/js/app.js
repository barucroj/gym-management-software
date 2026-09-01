// Sesion, navegacion y utilidades compartidas.

let usuarioActual = null;

// El API devuelve ids, no nombres. El catalogo se carga una vez por pantalla
// y se resuelve en memoria, en lugar de pedir el nombre de cada fila aparte.
let catalogo = { miembros: [], planes: [], suscripciones: [] };

document.addEventListener("DOMContentLoaded", iniciar);

async function iniciar() {
  document.getElementById("form-login").addEventListener("submit", entrar);
  document.getElementById("btn-salir").addEventListener("click", salir);
  document.getElementById("form-miembro").addEventListener("submit", guardarMiembro);
  document.getElementById("buscar-socio").addEventListener("input", alEscribirBusqueda);
  document.getElementById("form-usuario").addEventListener("submit", guardarUsuario);
  document.getElementById("form-plan").addEventListener("submit", guardarPlan);
  document.getElementById("form-suscripcion").addEventListener("submit", guardarSuscripcion);
  document.getElementById("form-checkin").addEventListener("submit", validarAcceso);
  document.getElementById("form-pase-dia")?.addEventListener("submit", registrarPaseDia);

  // Búsqueda dinámica en tiempo real para Check-in
  document.getElementById("checkin-id")?.addEventListener("input", alEscribirCheckin);

  // Al cambiar socio, plan o fecha de inicio se recalcula la vigencia y acumulacion.
  document.getElementById("s-miembro")?.addEventListener("change", proponerVigencia);
  document.getElementById("s-plan")?.addEventListener("change", proponerVigencia);
  document.getElementById("s-inicio")?.addEventListener("change", proponerVigencia);

  // Restriccion estricta de teléfono a solo números de 10 dígitos
  document.getElementById("m-telefono")?.addEventListener("input", function() {
    this.value = this.value.replace(/\D/g, "").slice(0, 10);
  });

  if (!leerToken()) {
    mostrarLogin();
    return;
  }

  // Hay un token guardado, pero pudo haber vencido mientras la pestaña estaba
  // cerrada. Se comprueba contra el API antes de mostrar nada, en lugar de
  // confiar en que sigue sirviendo y llenar la pantalla de errores.
  try {
    usuarioActual = await apiFetch("/auth/yo");
    mostrarApp();
  } catch (err) {
    mostrarLogin();
  }
}

async function entrar(e) {
  e.preventDefault();
  const error = document.getElementById("login-error");
  const boton = document.getElementById("btn-entrar");

  error.classList.add("d-none");
  boton.disabled = true;

  try {
    await login(
      document.getElementById("login-email").value,
      document.getElementById("login-password").value
    );
    usuarioActual = await apiFetch("/auth/yo");
    document.getElementById("form-login").reset();
    mostrarApp();
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove("d-none");
  } finally {
    boton.disabled = false;
  }
}

function salir() {
  borrarToken();
  usuarioActual = null;
  mostrarLogin();
}

function mostrarLogin() {
  document.getElementById("pantalla-login").classList.remove("d-none");
  document.getElementById("pantalla-app").classList.add("d-none");
}

function mostrarApp() {
  document.getElementById("pantalla-login").classList.add("d-none");
  document.getElementById("pantalla-app").classList.remove("d-none");

  document.getElementById("avatar-usuario").textContent = iniciales(usuarioActual.nombre);
  document.getElementById("nombre-usuario").textContent = usuarioActual.nombre;
  document.getElementById("rol-usuario").textContent =
    usuarioActual.rol === "admin" ? "Administrador" : "Recepción";

  // La seccion de usuarios solo se ofrece al administrador: al resto el API le
  // responde 403, asi que mostrarla seria prometer algo que no funciona.
  document
    .getElementById("item-usuarios")
    .classList.toggle("d-none", usuarioActual.rol !== "admin");

  // En version Starter, iniciamos directamente en el modulo operativo de Miembros
  switchTab("miembros");
}


// --- NAVEGACION ---
const SECCIONES = ["dashboard", "miembros", "suscripciones", "checkin", "usuarios"];

function switchTab(seccion) {
  SECCIONES.forEach(nombre => {
    document.getElementById(`sec-${nombre}`).classList.toggle("d-none", nombre !== seccion);
  });
  document.querySelectorAll(".sidebar .nav-link").forEach(enlace => {
    enlace.classList.toggle("active", enlace.dataset.seccion === seccion);
  });

  // El mapa se arma aqui adentro y no a nivel de modulo: pantallas.js se carga
  // despues que este archivo, asi que sus funciones aun no existirian.
  const cargadores = {
    dashboard: cargarDashboard,
    miembros: cargarMiembros,
    suscripciones: cargarSuscripciones,
    checkin: prepararCheckin,
    usuarios: cargarUsuarios
  };
  cargadores[seccion]?.();
}

// --- UTILIDADES ---

/**
 * Escapa el texto antes de interpolarlo en HTML. Sin esto, un socio con
 * comillas o etiquetas en el nombre rompe la tabla, y en el peor caso ejecuta
 * lo que le hayan puesto adentro.
 */
function esc(valor) {
  if (valor === null || valor === undefined) return "";
  return String(valor).replace(
    /[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function iniciales(nombre) {
  return String(nombre || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(parte => parte[0] || "")
    .join("")
    .toUpperCase();
}

/** Avatar dibujado localmente: el nombre del socio no sale del gimnasio. */
function avatar(nombre) {
  return `<span class="avatar-iniciales me-3">${esc(iniciales(nombre))}</span>`;
}

function badgeEstado(activo) {
  return activo
    ? '<span class="badge bg-success bg-opacity-10 text-success px-3 py-2">Activo</span>'
    : '<span class="badge bg-secondary bg-opacity-10 text-secondary px-3 py-2">Inactivo</span>';
}

const ETIQUETA_ESTATUS = {
  activa: { texto: "Activa", clase: "bg-success bg-opacity-10 text-success" },
  por_vencer: { texto: "Por vencer", clase: "bg-warning bg-opacity-10 text-warning" },
  vencida: { texto: "Vencida", clase: "bg-danger bg-opacity-10 text-danger" }
};

function badgeEstatus(estatus) {
  const etiqueta = ETIQUETA_ESTATUS[estatus] || {
    texto: estatus,
    clase: "bg-secondary bg-opacity-10 text-secondary"
  };
  return `<span class="badge ${etiqueta.clase} px-3 py-2">${esc(etiqueta.texto)}</span>`;
}

/** Formatea una fecha ISO (2026-08-31) como 31/08/2026. */
function fecha(iso) {
  if (!iso) return "-";
  const [anio, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

function cargando(tbody, columnas) {
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-center text-muted py-3">Cargando...</td></tr>`;
}

function vacio(tbody, columnas, mensaje) {
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-center text-muted py-3">${esc(mensaje)}</td></tr>`;
}

/** Si el problema fue la sesion vuelve al login; si no, lo muestra. */
function manejarError(err, tbody, columnas, mensaje) {
  if (err instanceof ErrorNoAutenticado) {
    salir();
    return;
  }
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-danger text-center py-3">${esc(mensaje)}</td></tr>`;
}

function cerrarModal(idModal, idFormulario, idError) {
  bootstrap.Modal.getInstance(document.getElementById(idModal))?.hide();
  document.getElementById(idFormulario).reset();
  document.getElementById(idError).classList.add("d-none");
}

function mostrarErrorEnFormulario(idError, err) {
  if (err instanceof ErrorNoAutenticado) {
    salir();
    return;
  }
  const caja = document.getElementById(idError);
  caja.textContent = err.message;
  caja.classList.remove("d-none");
}

/** Confirma, ejecuta el borrado y recarga; muestra el motivo si el API lo niega. */
async function eliminarRecurso(recurso, id, pregunta, recargar) {
  if (!confirm(pregunta)) return;
  try {
    await apiFetch(`/${recurso}/${id}`, "DELETE");
    recargar();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    alert(err.message);
  }
}

function llenarSelect(idSelect, opciones, textoVacio) {
  const select = document.getElementById(idSelect);
  select.innerHTML = opciones.length
    ? opciones.map(o => `<option value="${o.valor}">${esc(o.texto)}</option>`).join("")
    : `<option value="">${esc(textoVacio)}</option>`;
}

// --- CATALOGO COMPARTIDO ---
async function cargarCatalogos() {
  const [miembros, planes, suscripciones] = await Promise.all([
    apiFetch("/miembros/"),
    apiFetch("/planes/"),
    apiFetch("/suscripciones/")
  ]);
  catalogo = { miembros, planes, suscripciones };
}

/**
 * ID visible del socio, con el mismo formato en todas las pantallas.
 *
 * No es un adorno: es el numero que recepcion teclea en el check-in, asi que
 * quien atiende tiene que poder leerlo desde cualquier lista sin ir a buscarlo
 * a la seccion de Miembros.
 */
function idSocio(id) {
  return `#${id}`;
}

function nombreMiembro(id) {
  const miembro = catalogo.miembros.find(m => m.id === id);
  // El id ya se pinta aparte con idSocio(): repetirlo aqui daria "#5 · #5".
  return miembro ? miembro.nombre_completo : "socio no encontrado";
}

function nombrePlan(id) {
  const plan = catalogo.planes.find(p => p.id === id);
  return plan ? plan.nombre : `#${id}`;
}

/** Suscripcion no vencida de un miembro, la de vigencia mas larga. */
function vigenciaDe(miembroId) {
  return (
    catalogo.suscripciones
      .filter(s => s.miembro_id === miembroId && s.estatus !== "vencida")
      .sort((a, b) => b.fecha_fin.localeCompare(a.fecha_fin))[0] || null
  );
}

// --- MIEMBROS ---

// El API no acepta consultas de menos de dos caracteres: con una letra
// cualquier umbral de parecido devuelve medio padron.
const LONGITUD_MINIMA_BUSQUEDA = 2;

// Se espera a que deje de teclear en vez de consultar en cada letra.
const ESPERA_BUSQUEDA_MS = 250;

let temporizadorBusqueda = null;

// Las respuestas pueden llegar desordenadas: la de "men" despues de la de
// "mendoza". El contador deja pintar solo a la ultima que se pidio.
let ultimaBusqueda = 0;

function textoBuscado() {
  return document.getElementById("buscar-socio").value.trim();
}

function alEscribirBusqueda() {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(() => {
    refrescarTablaMiembros().catch(err =>
      manejarError(err, document.getElementById("tabla-miembros-body"), 5, "Error al buscar")
    );
  }, ESPERA_BUSQUEDA_MS);
}

async function cargarMiembros() {
  const tbody = document.getElementById("tabla-miembros-body");
  cargando(tbody, 5);
  try {
    await cargarCatalogos();
    await refrescarTablaMiembros();
  } catch (err) {
    manejarError(err, tbody, 5, "Error al cargar los socios");
  }
}

/**
 * Repinta la tabla segun lo que haya escrito en el buscador.
 *
 * No recarga los catalogos: el filtrado por parecido lo resuelve PostgreSQL,
 * pero la vigencia de cada fila sale de las suscripciones que ya estan en
 * memoria, y volver a bajarlas en cada tecla no aportaria nada.
 */
async function refrescarTablaMiembros() {
  const tbody = document.getElementById("tabla-miembros-body");
  const consulta = textoBuscado();

  // Un id de un solo digito tambien busca: los primeros socios los tienen.
  const buscable = consulta.length >= LONGITUD_MINIMA_BUSQUEDA || /^\d+$/.test(consulta);

  let miembros = catalogo.miembros;
  if (buscable) {
    const propia = ++ultimaBusqueda;
    const encontrados = await apiFetch(
      `/miembros/buscar?q=${encodeURIComponent(consulta)}&limite=50`
    );
    if (propia !== ultimaBusqueda) return;
    miembros = encontrados;
  }

  pintarMiembros(miembros, consulta);
}

function pintarMiembros(miembros, consulta) {
  const tbody = document.getElementById("tabla-miembros-body");

  if (miembros.length === 0) {
    return vacio(
      tbody,
      5,
      consulta
        ? `Ningún socio se parece a "${consulta}".`
        : "Todavía no hay socios registrados."
    );
  }

  tbody.innerHTML = miembros.map(m => {
    const vigente = vigenciaDe(m.id);
    return `
    <tr>
      <td class="d-flex align-items-center">
        ${avatar(m.nombre_completo)}
        <div>
          <div class="fw-bold">${esc(m.nombre_completo)}</div>
          <div class="text-muted small font-monospace">${idSocio(m.id)}</div>
        </div>
      </td>
      <td>
        <div>${esc(m.email) || '-'}</div>
        <div class="text-muted small">${esc(m.telefono) || '-'}</div>
      </td>
      <td>
        ${vigente
          ? `${badgeEstatus(vigente.estatus)}<div class="text-muted small mt-1">hasta ${fecha(vigente.fecha_fin)}</div>`
          : '<span class="text-muted small">sin suscripción</span>'}
      </td>
      <td>${badgeEstado(m.activo)}</td>
      <td>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-primary" onclick="abrirAsignarSuscripcionParaMiembro(${m.id})" title="Asignar o Renovar Plan">
            <i class="bi bi-card-checklist"></i> Plan
          </button>
          <button class="btn btn-outline-danger" onclick="eliminarMiembro(${m.id})" title="Eliminar Socio">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </td>
    </tr>`;
  }).join("");
}

async function guardarMiembro(e) {
  e.preventDefault();
  const telValor = document.getElementById("m-telefono").value.trim();

  // Validación de número de teléfono a exactamente 10 dígitos si se proporciona
  if (telValor && !/^\d{10}$/.test(telValor)) {
    const errorCaja = document.getElementById("m-error");
    errorCaja.textContent = "El número telefónico debe contener exactamente 10 dígitos numéricos.";
    errorCaja.classList.remove("d-none");
    document.getElementById("m-telefono").focus();
    return;
  }

  const datos = {
    nombre: document.getElementById("m-nombre").value.trim(),
    apellidos: document.getElementById("m-apellidos").value.trim(),
    email: document.getElementById("m-email").value.trim() || null,
    telefono: telValor || null,
    fecha_nacimiento: document.getElementById("m-nacimiento").value || null,
    notas: document.getElementById("m-notas").value.trim() || null
  };
  try {
    await apiFetch("/miembros/", "POST", datos);
    cerrarModal("modalNuevoMiembro", "form-miembro", "m-error");
    cargarMiembros();
  } catch (err) {
    mostrarErrorEnFormulario("m-error", err);
  }
}

function eliminarMiembro(id) {
  eliminarRecurso("miembros", id, "¿Deseas eliminar este socio?", cargarMiembros);
}


// --- USUARIOS ---
async function cargarUsuarios() {
  const tbody = document.getElementById("tabla-usuarios");
  cargando(tbody, 5);
  try {
    const usuarios = await apiFetch("/usuarios/");
    tbody.innerHTML = usuarios.map(u => `
      <tr>
        <td class="d-flex align-items-center">
          ${avatar(u.nombre)}
          <span class="fw-bold">${esc(u.nombre)}</span>
        </td>
        <td>${esc(u.email)}</td>
        <td>${u.rol === "admin" ? "Administrador" : "Recepción"}</td>
        <td>${badgeEstado(u.activo)}</td>
        <td>
          <button class="btn btn-sm btn-outline-danger" onclick="eliminarUsuario(${u.id})" title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 5, "Error al cargar usuarios");
  }
}

async function guardarUsuario(e) {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("u-nombre").value,
    email: document.getElementById("u-email").value,
    password: document.getElementById("u-password").value,
    rol: document.getElementById("u-rol").value
  };
  try {
    await apiFetch("/usuarios/", "POST", datos);
    cerrarModal("modalUsuario", "form-usuario", "u-error");
    cargarUsuarios();
  } catch (err) {
    mostrarErrorEnFormulario("u-error", err);
  }
}

function eliminarUsuario(id) {
  eliminarRecurso("usuarios", id, "¿Deseas eliminar este usuario?", cargarUsuarios);
}
