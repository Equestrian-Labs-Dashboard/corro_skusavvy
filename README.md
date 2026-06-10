# SKUSavvy Inventory Intelligence — GitHub Pages + Python

Static GitHub Pages dashboard. GitHub Actions runs Python to fetch SKUSavvy data and write `data/dashboard.json`.

## Required setup

1. Upload these files/folders to the repo root:
   - `index.html`
   - `scripts/generate_data.py`
   - `.github/workflows/update-dashboard.yml`
   - `data/dashboard.json`
   - `.gitignore`

2. Add the SKUSavvy token:
   - Repo → Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `SKUSAVVY_TOKEN`
   - Value: your SKUSavvy token

3. Allow Actions to commit data:
   - Repo → Settings → Actions → General
   - Workflow permissions: **Read and write permissions**
   - Save

4. Enable Pages:
   - Repo → Settings → Pages
   - Source: **Deploy from a branch**
   - Branch: `main`
   - Folder: `/ (root)`
   - Save

5. Generate data now:
   - Repo → Actions → **Update SKUSavvy Dashboard Data**
   - Run workflow

The dashboard URL should be:

`https://arojas-company.github.io/corro_skusavvy/`

## Update schedule

The workflow updates data every day at 6:00 AM UTC.

## Manual refresh button

The dashboard button opens the GitHub Actions workflow page. Run the workflow, wait until it finishes, then click **Reload data** on the dashboard.


## Warehouse COGS fix

This version does not hardcode reference totals. It calculates COGS / Capital as `warehouse stock × SKUSavvy variant cost`, and retail value as `warehouse stock × SKUSavvy variant price`. Wellington Warehouse remains the default warehouse.
