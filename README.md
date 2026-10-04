# Ingredients Network Company Directory

Flask app for browsing the cleaned company profiles from `code2.py`. It reads from Supabase when configured, with the cleaned CSV as a local fallback. Search covers every displayed field; results are paginated.

## Set up Supabase

1. Create a Supabase project.
2. In the Supabase SQL Editor, run [`supabase_schema.sql`](./supabase_schema.sql) to create the table, public read-only row-level-security policy, and restricted import function.
3. Set the project URL and **service_role** key in your local PowerShell session, then import the CSV. Do not commit or publish the service-role key:

   ```powershell
   $env:SUPABASE_URL = "https://your-project.supabase.co"
   $env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
   .\.venv\Scripts\python.exe .\import_supabase.py
   ```

   The import atomically replaces the table contents with the CSV, retaining duplicate company names as separate profiles. It refuses to import an empty file.

4. Verify the `company_profiles` table in Supabase. For the app, use the project URL and the **anon/public** key; do not use the service-role key in the web app.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_ANON_KEY = "your-anon-public-key"
python app.py
```

Open <http://127.0.0.1:5000>. When both Supabase app variables are set, the app reads profiles from Supabase. When neither is set, it uses `ingredientsnetwork_clean.csv` beside `app.py`. A partial Supabase configuration or database error is shown as an explicit service-unavailable error; it does not silently fall back to stale CSV data.

## Deploy on Railway

1. Push this project to a GitHub repository. Include `supabase_schema.sql`, `railway.json`, the Python files, templates, static assets, and `requirements.txt`. The CSV is only needed for local fallback or import; it is not required at runtime when Supabase is configured.
2. In Railway, create a project and deploy from the GitHub repository. Railway reads [`railway.json`](./railway.json) to install dependencies, bind Gunicorn to Railway's `$PORT`, and health-check `/`.
3. In the Railway service's **Variables** settings, add:
   - `SUPABASE_URL` — Supabase project URL.
   - `SUPABASE_ANON_KEY` — Supabase anon/public key.
4. Wait for the Railway deployment to finish and open its generated public domain.

The service-role key is only for running the one-time CSV import locally; do not add it to Railway.
