document.addEventListener("DOMContentLoaded", () => {
  cargarMiembros();
});

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
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Error al cargar miembros</td></tr>`;
  }
}

document.getElementById("form-miembro").addEventListener("submit", async (e) => {
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
    alert("Error al guardar miembro");
  }
});

async function eliminarMiembro(id) {
  if (confirm("¿Deseas eliminar este miembro?")) {
    await apiFetch(`/miembros/${id}`, "DELETE");
    cargarMiembros();
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
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center">Error al cargar usuarios</td></tr>`;
  }
}

async function eliminarUsuario(id) {
  if (confirm("¿Deseas eliminar este usuario?")) {
    await apiFetch(`/usuarios/${id}`, "DELETE");
    cargarUsuarios();
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
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center">Error al cargar planes</td></tr>`;
  }
}