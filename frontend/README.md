# Frontend (Angular)

Pendiente. Se genera en una fase posterior con:

```bash
ng new gym-frontend --directory . --routing --style=scss
```

El build estático (`frontend/dist/...`) se monta en el contenedor `proxy` (Nginx),
que lo sirve en `/` y redirige `/api` al backend.
