document.addEventListener("DOMContentLoaded", () => {
  initChart();
  cargarMiembros();
  cargarPlanes();
});

// --- NAVEGACIÓN ENTRE PESTAÑAS ---
function switchTab(tabId) {
  const secciones = ['dashboard', 'miembros', 'suscripciones', 'checkin'];
  secciones.forEach(sec => {
    const el = document.getElementById(`sec-${sec}`);
    if (el) el.classList.add('d-none');
  });

  const secActiva = document.getElementById(`sec-${tabId}`);
  if (secActiva) secActiva.classList.remove('d-none');
}

// --- GRÁFICO (Chart.js) ---
function initChart() {
  const ctx = document.getElementById('chartAsistencias');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
      datasets: [{
        label: 'Asistencias',
        data: [42, 58, 65, 50, 72, 85, 30],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#334155' } },
        y: { grid: { color: '#334155' } }
      }
    }
  });
}

// --- MIEMBROS ---
async function cargarMiembros() {
  const tbody = document.getElementById("tabla-miembros-body");
  if (!tbody) return;
  
  try {
    const miembros = await apiFetch("/miembros/");
    document.getElementById("kpi-total-miembros").innerText = miembros.length;
    document.getElementById("kpi-activos").innerText = miembros.length;

    tbody.innerHTML = miembros.map(m => `
      <tr>
        <td class="d-flex align-items-center">
          <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(m.nombre || m.name || 'S')}&background=random" class="avatar-img me-3">
          <div>
            <div class="fw-bold">${m.nombre || m.name || '-'}</div>
            <div class="text-muted small">ID: ${m.id}</div>
          </div>
        </td>
        <td>
          <div>${m.email || '-'}</div>
          <div class="text-muted small">${m.telefono || m.phone || '-'}</div>
        </td>
        <td><span class="badge bg-success bg-opacity-10 text-success px-3 py-2">Activo</span></td>
        <td>
          <button class="btn btn-sm btn-outline-danger" onclick="eliminarMiembro(${m.id})"><i class="bi bi-trash"></i></button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center py-3">Error al conectar con la API</td></tr>`;
  }
}

// Crear Miembro desde Modal
document.getElementById("form-miembro").addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = {
    nombre: document.getElementById("m-nombre").value,
    email: document.getElementById("m-email").value,
    telefono: document.getElementById("m-telefono").value
  };

  try {
    await apiFetch("/miembros/", "POST", datos);
    const modalEl = document.getElementById("modalNuevoMiembro");
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.hide();
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

// --- PLANES DE SUSCRIPCIÓN ---
async function cargarPlanes() {
  const contenedor = document.getElementById("contenedor-planes");
  if (!contenedor) return;

  try {
    const planes = await apiFetch("/planes/");
    contenedor.innerHTML = planes.map(p => `
      <div class="col-md-4">
        <div class="kpi-card p-4 text-center h-100 d-flex flex-column justify-content-between">
          <div>
            <h4 class="fw-bold text-primary">${p.nombre || p.name}</h4>
            <h2 class="my-3 fw-bold">$${p.precio || p.price} <span class="fs-6 text-muted">/ ${p.duracion_dias || 30} días</span></h2>
            <p class="text-muted small">Acceso ilimitado a las instalaciones y áreas de peso libre.</p>
          </div>
          <button class="btn btn-outline-primary w-100 mt-3" onclick="asignarPlan(${p.id})">Asignar a Socio</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    contenedor.innerHTML = `<div class="col-12 text-center text-muted py-4">Carga planes mediante el backend para mostrarlos aquí.</div>`;
  }
}

function asignarPlan(planId) {
  const socioId = prompt("Ingresa el ID del Socio para asignarle este plan:");
  if (socioId) {
    alert(`Plan #${planId} asignado con éxito al socio #${socioId}`);
  }
}

// --- RECEPCIÓN / CHECK-IN ---
async function validarAcceso() {
  const idInput = document.getElementById("checkin-id").value;
  const resDiv = document.getElementById("checkin-resultado");
  if (!idInput) return;

  try {
    const miembro = await apiFetch(`/miembros/${idInput}`);
    if (miembro && miembro.id) {
      resDiv.innerHTML = `
        <div class="alert alert-success d-flex align-items-center justify-content-center p-3">
          <i class="bi bi-check-circle-fill fs-2 me-3"></i>
          <div>
            <h5 class="mb-0">ACCESO PERMITIDO</h5>
            <small>${miembro.nombre || 'Socio Activo'}</small>
          </div>
        </div>`;
    }
  } catch (err) {
    resDiv.innerHTML = `
      <div class="alert alert-danger d-flex align-items-center justify-content-center p-3">
        <i class="bi bi-x-circle-fill fs-2 me-3"></i>
        <div>
          <h5 class="mb-0">ACCESO DENEGADO</h5>
          <small>Socio no encontrado o membresía vencida</small>
        </div>
      </div>`;
  }
}