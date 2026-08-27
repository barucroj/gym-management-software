# Frontend

Interfaz del sistema: HTML, Bootstrap 5 y JavaScript sin framework. **No hay
paso de build**: son archivos estáticos que Nginx sirve tal cual, montados
como volumen desde el `docker-compose.yml`. Editar y recargar el navegador
alcanza; no hace falta reconstruir ninguna imagen.

> Las versiones anteriores de este documento planteaban Angular. Se descartó:
> para el alcance de este sistema, un framework agregaba un paso de build y
> una cadena de dependencias que no se compensaban con lo que aportaba.

## Cómo se abre

Con el stack levantado (`docker compose up -d --build`), en:

```
http://localhost/
```

Se entra con un usuario del sistema. Si todavía no existe ninguno, se crea el
primer administrador desde la consola (ver el README de la raíz).

## Archivos

| Archivo | Qué contiene |
|---|---|
| `index.html` | Estructura, pestañas y modales |
| `js/api.js` | Sesión, token y llamadas HTTP al API |
| `js/app.js` | Login, utilidades compartidas, miembros, usuarios y planes |
| `js/pantallas.js` | Suscripciones y asistencias |

## Cómo habla con el API

La URL base es **relativa** (`/api/v1`). Frontend y API salen por el mismo
Nginx, así que el navegador no cruza de origen y CORS no interviene. Por eso
no debe volver a escribirse como `http://localhost:8000`: eso saltearía el
proxy y obligaría a reactivar CORS.

El token se guarda en `localStorage` y se adjunta como
`Authorization: Bearer <token>` en cada petición. Ante un `401`, `apiFetch`
descarta el token y devuelve a la pantalla de login.

## Convenciones

- **Nunca interpolar datos del API en HTML sin pasarlos por `esc()`.** Todo lo
  que se muestra viene de la base y puede contener `<` o comillas.
- **Los nombres de campo se consultan, no se adivinan.** El contrato está en
  `http://localhost/openapi.json` y la referencia navegable en
  `http://localhost/docs`.
- Los errores del API llegan en `detail`; se muestran tal cual en lugar de un
  código.
