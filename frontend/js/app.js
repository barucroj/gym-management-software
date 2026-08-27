// --- SESION ---
let usuarioActual = null;

document.addEventListener("DOMContentLoaded", iniciar);

async function iniciar() {
  document.getElementById("form-login").addEventListener("submit", entrar);
  document.getElementById("btn-salir").addEventListener("click", salir);
  document.getElementById("form-miembro").addEventListener("submit", guardarMiembro);
  document.getElementById("form-usuario").addEventListener("submit", guardarUsuario);
  document.getElementById("form-plan").addEventListener("submit", guardarPlan);

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
  document.getElementById("barra-usuario").classList.remove("d-flex");
  document.getElementById("barra-usuario").classList.add("d-none");
}

function mostrarApp() {
  document.getElementById("pantalla-login").classList.add("d-none");
  document.getElementById("pantalla-app").classList.remove("d-none");
  document.getElementById("barra-usuario").classList.remove("d-none");
  document.getElementById("barra-usuario").classList.add("d-flex");
  document.getElementById("etiqueta-usuario").textContent =
    `${usuarioActual.nombre} · ${usuarioActual.rol}`;

  // La pestaña de usuarios solo se ofrece al administrador: al resto el API
  // le responde 403, asi que mostrarla seria prometer algo que no funciona.
  document
    .getElementById("item-usuarios")
    .classList.toggle("d-none", usuarioActual.rol !== "admin");

  cargarMiembros();
}

// --- UTILIDADES ---

/**
 * Escapa el texto antes de interpolarlo en HTML. Sin esto, un miembro con
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

function badgeEstado(activo) {
  return activo
    ? '<span class="badge bg-success">Activo</span>'
    : '<span class="badge bg-secondary">Inactivo</span>';
}

/** Si el problema fue la sesion vuelve al login; si no, lo muestra. */
function manejarError(err, tbody, columnas, mensaje) {
  if (err instanceof ErrorNoAutenticado) {
    salir();
    return;
  }
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-danger text-center">${esc(mensaje)}</td></tr>`;
}

function cargando(tbody, columnas) {
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-center text-muted">Cargando...</td></tr>`;
}

function vacio(tbody, columnas, mensaje) {
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-center text-muted">${esc(mensaje)}</td></tr>`;
}

/** Cierra el modal, limpia el formulario y oculta el error anterior. */
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

// --- MIEMBROS ---
async function cargarMiembros() {
  const tbody = document.getElementById("tabla-miembros");
  cargando(tbody, 6);
  try {
    const miembros = await apiFetch("/miembros/");
    if (miembros.length === 0) return vacio(tbody, 6, "Todavía no hay miembros registrados.");

    tbody.innerHTML = miembros.map(m => `
      <tr>
        <td>${m.id}</td>
        <td>${esc(m.nombre_completo)}</td>
        <td>${esc(m.email) || '-'}</td>
        <td>${esc(m.telefono) || '-'}</td>
        <td>${badgeEstado(m.activo)}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarMiembro(${m.id})" title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 6, "Error al cargar miembros");
  }
}

async function guardarMiembro(e) {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("m-nombre").value,
    apellidos: document.getElementById("m-apellidos").value,
    email: document.getElementById("m-email").value || null,
    telefono: document.getElementById("m-telefono").value || null,
    fecha_nacimiento: document.getElementById("m-nacimiento").value || null,
    notas: document.getElementById("m-notas").value || null
  };
  try {
    await apiFetch("/miembros/", "POST", datos);
    cerrarModal("modalMiembro", "form-miembro", "m-error");
    cargarMiembros();
  } catch (err) {
    mostrarErrorEnFormulario("m-error", err);
  }
}

function eliminarMiembro(id) {
  eliminarRecurso("miembros", id, "¿Deseas eliminar este miembro?", cargarMiembros);
}

// --- USUARIOS ---
async function cargarUsuarios() {
  const tbody = document.getElementById("tabla-usuarios");
  cargando(tbody, 5);
  try {
    const usuarios = await apiFetch("/usuarios/");
    tbody.innerHTML = usuarios.map(u => `
      <tr>
        <td>${u.id}</td>
        <td>${esc(u.nombre)}</td>
        <td>${esc(u.email)}</td>
        <td>${esc(u.rol)}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarUsuario(${u.id})" title="Eliminar">
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

// --- PLANES ---
async function cargarPlanes() {
  const tbody = document.getElementById("tabla-planes");
  cargando(tbody, 6);
  try {
    const planes = await apiFetch("/planes/");
    if (planes.length === 0) return vacio(tbody, 6, "Todavía no hay planes cargados.");

    tbody.innerHTML = planes.map(p => `
      <tr>
        <td>${p.id}</td>
        <td>${esc(p.nombre)}</td>
        <td>$${esc(p.precio)}</td>
        <td>${p.duracion_dias}</td>
        <td>${badgeEstado(p.activo)}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarPlan(${p.id})" title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 6, "Error al cargar planes");
  }
}

async function guardarPlan(e) {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("p-nombre").value,
    descripcion: document.getElementById("p-descripcion").value || null,
    duracion_dias: Number(document.getElementById("p-duracion").value),
    // Se manda como texto: el precio es Decimal en el API y pasar por Number
    // introduce el redondeo binario que justamente se quiere evitar.
    precio: document.getElementById("p-precio").value
  };
  try {
    await apiFetch("/planes/", "POST", datos);
    cerrarModal("modalPlan", "form-plan", "p-error");
    cargarPlanes();
  } catch (err) {
    mostrarErrorEnFormulario("p-error", err);
  }
}

function eliminarPlan(id) {
  eliminarRecurso("planes", id, "¿Deseas eliminar este plan?", cargarPlanes);
}
