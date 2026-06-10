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

## Validated warehouse COGS totals

The dashboard uses SKUSavvy `variants(inStock: warehouseId)` for warehouse SKU filtering. For the capital/COGS KPI, it applies the validated warehouse totals provided by operations while exact per-SKU cost-by-warehouse is being mapped:

- Wellington Warehouse: Cost $850,628.65, Retail Value $1,927,768.15, Margin 56%
- Corro Trailer 1: Cost $39,290.39, Retail Value $83,528.06, Margin 53%

Month changes recalculate estimated sales using SKUSavvy average daily sales. Current inventory/COGS is a snapshot and does not change by month unless a historical inventory or Shopify monthly sales source is connected.
