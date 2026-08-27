// --- SESION ---
let usuarioActual = null;

document.addEventListener("DOMContentLoaded", iniciar);

async function iniciar() {
  document.getElementById("form-login").addEventListener("submit", entrar);
  document.getElementById("btn-salir").addEventListener("click", salir);
  document.getElementById("form-miembro").addEventListener("submit", guardarMiembro);

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

/**
 * Si el problema fue la sesion, devuelve al login; cualquier otro error se
 * muestra en la tabla. Centralizado para no repetirlo en cada pantalla.
 */
function manejarError(err, tbody, columnas, mensaje) {
  if (err instanceof ErrorNoAutenticado) {
    salir();
    return;
  }
  tbody.innerHTML =
    `<tr><td colspan="${columnas}" class="text-danger text-center">${mensaje}</td></tr>`;
}

// --- MIEMBROS ---
async function cargarMiembros() {
  const tbody = document.getElementById("tabla-miembros");
  tbody.innerHTML = '<tr><td colspan="5" class="text-center">Cargando...</td></tr>';
  try {
    const miembros = await apiFetch("/miembros/");
    tbody.innerHTML = miembros.map(m => `
      <tr>
        <td>${m.id}</td>
        <td>${m.nombre || m.name || '-'}</td>
        <td>${m.email || '-'}</td>
        <td>${m.telefono || m.phone || '-'}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarMiembro(${m.id})"><i class="bi bi-trash"></i></button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 5, "Error al cargar miembros");
  }
}

async function guardarMiembro(e) {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("m-nombre").value,
    email: document.getElementById("m-email").value,
    telefono: document.getElementById("m-telefono").value
  };
  try {
    await apiFetch("/miembros/", "POST", datos);
    bootstrap.Modal.getInstance(document.getElementById("modalMiembro")).hide();
    document.getElementById("form-miembro").reset();
    cargarMiembros();
  } catch (err) {
    if (err instanceof ErrorNoAutenticado) return salir();
    alert("Error al guardar miembro");
  }
}

async function eliminarMiembro(id) {
  if (confirm("¿Deseas eliminar este miembro?")) {
    try {
      await apiFetch(`/miembros/${id}`, "DELETE");
      cargarMiembros();
    } catch (err) {
      if (err instanceof ErrorNoAutenticado) return salir();
      alert(err.message);
    }
  }
}

// --- USUARIOS ---
async function cargarUsuarios() {
  const tbody = document.getElementById("tabla-usuarios");
  tbody.innerHTML = '<tr><td colspan="4" class="text-center">Cargando...</td></tr>';
  try {
    const usuarios = await apiFetch("/usuarios/");
    tbody.innerHTML = usuarios.map(u => `
      <tr>
        <td>${u.id}</td>
        <td>${u.username || u.nombre_usuario || '-'}</td>
        <td>${u.rol || u.role || 'Usuario'}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="eliminarUsuario(${u.id})"><i class="bi bi-trash"></i></button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 4, "Error al cargar usuarios");
  }
}

async function eliminarUsuario(id) {
  if (confirm("¿Deseas eliminar este usuario?")) {
    try {
      await apiFetch(`/usuarios/${id}`, "DELETE");
      cargarUsuarios();
    } catch (err) {
      if (err instanceof ErrorNoAutenticado) return salir();
      alert(err.message);
    }
  }
}

// --- PLANES ---
async function cargarPlanes() {
  const tbody = document.getElementById("tabla-planes");
  tbody.innerHTML = '<tr><td colspan="4" class="text-center">Cargando...</td></tr>';
  try {
    const planes = await apiFetch("/planes/");
    tbody.innerHTML = planes.map(p => `
      <tr>
        <td>${p.id}</td>
        <td>${p.nombre || p.name || '-'}</td>
        <td>$${p.precio || p.price || 0}</td>
        <td>${p.duracion_dias || p.duration_days || '-'}</td>
      </tr>
    `).join("");
  } catch (err) {
    manejarError(err, tbody, 4, "Error al cargar planes");
  }
}
