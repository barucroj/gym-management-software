// Ruta relativa: el frontend y el API salen por el mismo Nginx, asi que el
// navegador no cruza de origen y no interviene CORS. Ademas la app funciona
// igual desde cualquier maquina de la red, no solo desde localhost.
const API_URL = "/api/v1";
const CLAVE_TOKEN = "gym_token";

/**
 * El token se guarda en localStorage: sobrevive a recargar la pagina y es lo
 * mas simple para una app que corre en la red interna del gimnasio. La
 * alternativa mas segura es una cookie httpOnly, que el JavaScript no puede
 * leer y por lo tanto un XSS no puede robar; exige cambios en el backend.
 */
function guardarToken(token) {
  localStorage.setItem(CLAVE_TOKEN, token);
}

function leerToken() {
  return localStorage.getItem(CLAVE_TOKEN);
}

function borrarToken() {
  localStorage.removeItem(CLAVE_TOKEN);
}

/** Se distingue del resto de errores para poder devolver al login. */
class ErrorNoAutenticado extends Error {}

async function login(email, password) {
  // El login espera un formulario, no JSON: lo exige el estandar OAuth2, y el
  // campo se llama "username" aunque lleve el email.
  const respuesta = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password })
  });

  if (!respuesta.ok) {
    throw new Error("Email o contraseña incorrectos");
  }

  const datos = await respuesta.json();
  guardarToken(datos.access_token);
  return datos.access_token;
}

async function apiFetch(endpoint, method = "GET", body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" }
  };

  const token = leerToken();
  if (token) options.headers["Authorization"] = `Bearer ${token}`;
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_URL}${endpoint}`, options);

  // 401: el token vencio o ya no sirve. Se descarta aqui, en un solo lugar,
  // para no repetir la logica en cada pantalla.
  if (response.status === 401) {
    borrarToken();
    throw new ErrorNoAutenticado("La sesión expiró");
  }
  if (response.status === 403) {
    throw new Error("No tienes permisos para esta acción");
  }
  if (response.status === 204) return null;
  if (!response.ok) throw new Error(await mensajeDeError(response));
  return response.json();
}

/**
 * El API explica cada rechazo en "detail": un texto en los errores de negocio
 * (409, 422 propios) y una lista de campos en los de validacion de pydantic.
 * Mostrarlo es mucho mas util que un "Error 409: Conflict".
 */
async function mensajeDeError(response) {
  try {
    const cuerpo = await response.json();
    if (typeof cuerpo.detail === "string") return cuerpo.detail;
    if (Array.isArray(cuerpo.detail)) {
      return cuerpo.detail
        .map(e => `${e.loc?.slice(1).join(".") || "dato"}: ${e.msg}`)
        .join(" · ");
    }
  } catch (err) {
    // Respuesta sin cuerpo JSON: se cae al mensaje generico.
  }
  return `Error ${response.status}: ${response.statusText}`;
}
