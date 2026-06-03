# SKU / SKUSavvy Dashboard — GitHub Pages + Python

Este proyecto corre gratis en GitHub usando:

- **GitHub Pages** para mostrar el dashboard estático.
- **GitHub Actions** para ejecutar Python y generar `data/dashboard.json`.
- **GitHub Secrets** para guardar `SKUSAVVY_TOKEN` sin ponerlo en el código.

## Warehouse default

El filtro default es:

```text
Wellington Warehouse
019b6b44-4eea-7613-9f82-9af97d2255d
```

## Archivos importantes

```text
index.html
scripts/generate_data.py
.github/workflows/update-dashboard.yml
README.md
```

Ya no necesitas Railway ni `server.js` para correr esta versión.

## Cómo instalar en GitHub

1. Sube estos archivos al repositorio en GitHub.
2. En GitHub ve a:

```text
Settings → Secrets and variables → Actions → New repository secret
```

3. Crea este secret:

```text
SKUSAVVY_TOKEN = tu_token_real
```

4. Activa GitHub Pages:

```text
Settings → Pages → Source → GitHub Actions
```

5. Corre el workflow manualmente:

```text
Actions → Update SKUSavvy Dashboard → Run workflow
```

6. Cuando termine, GitHub te dará una URL como:

```text
https://TU-USUARIO.github.io/TU-REPO/
```

## Nota importante sobre warehouse inventory

El script ya intenta leer inventario por warehouse con varios queries candidatos. Si SKUSavvy usa otro nombre en GraphQL, el dashboard se publica, pero mostrará un aviso y también generará:

```text
site/data/schema-debug.json
```

Ese archivo ayuda a identificar el campo exacto de SKUSavvy para `warehouse inventory`.

## Seguridad

No pongas el token en `index.html`, `README.md`, ni ningún archivo del repo. El token solo debe estar en GitHub Secrets.

Importante: si usas GitHub Pages gratis con repo público, el dashboard publicado y los datos generados quedan visibles en internet. El token sigue seguro, pero los datos de inventario publicados no son privados.


## Actualización automática y refresh manual

Este proyecto no necesita Railway ni servidor activo.

- **Automático diario:** el workflow `.github/workflows/update-dashboard.yml` corre todos los días a las **6:00 AM UTC** y vuelve a generar `data/dashboard.json` desde SKUSavvy.
- **Refresh manual:** en el dashboard hay un botón **Actualizar ahora**. Ese botón abre el workflow de GitHub Actions. Debes presionar **Run workflow** para generar datos nuevos en ese momento.
- Después de que GitHub Actions termine, vuelve al dashboard y presiona **Recargar datos**.

Importante: desde GitHub Pages no se puede ejecutar directamente el workflow en un solo clic sin exponer un token de GitHub en el navegador. Por seguridad, el botón abre GitHub Actions y el usuario autorizado lo ejecuta manualmente.
