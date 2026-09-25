# Deploying ExpenseMate on Vercel — every step

This guide assumes you have the project folder (`ExpenseMate/`) on your computer.
Two methods are given: **CLI** (fastest) and **GitHub import** (no terminal needed after push).

> **Read this first — the one real caveat**
> Vercel runs your app as a *serverless function*. Its filesystem is **read-only except `/tmp`**,
> and `/tmp` is **wiped between cold starts and every new deployment**.
> ExpenseMate stores data in SQLite, so on Vercel the app works perfectly for a **demo /
> submission / viva**, but data will **not persist long-term**.
> → For permanent data, see **"Making the database persistent"** at the bottom (3 options),
> or deploy on **Render / Railway / PythonAnywhere** instead (see last section) — those give
> you a real disk and the project runs there with almost no changes.

The repo already contains the two files Vercel needs:

| File | Purpose |
|---|---|
| `api/index.py` | Serverless entrypoint — exposes the Flask `app` object; auto-switches the DB to `/tmp` on Vercel |
| `vercel.json` | Tells Vercel to build `api/index.py` with the Python runtime, bundle the `app/` folder (backend **+** frontend), and rewrite **all** URLs to it |
| `requirements.txt` | Vercel installs these (`Flask`) automatically |

---

## Method 1 — Vercel CLI (recommended, ~5 minutes)

### Step 1 — Check prerequisites
Open a terminal in the project folder and run:

```bash
python --version      # need 3.10 or newer
node --version        # need Node.js 18+ (the CLI is an npm package)
```

If `node` is missing → install Node.js LTS from <https://nodejs.org> (tick "add to PATH"), then reopen the terminal.

### Step 2 — Install the Vercel CLI
```bash
npm install -g vercel
```
Verify:
```bash
vercel --version
```
> On Windows PowerShell, if `vercel` is "not recognized" after install, close and reopen the terminal (PATH refresh), or use `npx vercel` instead of `vercel` everywhere below.

### Step 3 — Log in to Vercel
```bash
vercel login
```
It opens a browser. Sign up / sign in (GitHub login is easiest). In the terminal, press **Enter** to confirm, or pick your email.

### Step 4 — Deploy to a preview URL
From the **project root** (the folder that contains `vercel.json`, `api/`, `app/`, `run.py`):
```bash
cd ExpenseMate
vercel
```
Answer the prompts:
| Prompt | Answer |
|---|---|
| Set up and deploy? | **Y** |
| Which scope? | your account |
| Link to existing project? | **N** |
| Project name? | `expensemate` (must be lowercase; add numbers if taken) |
| Directory with your code? | **./**  ← important, press Enter |
| Override settings? | **N** (our `vercel.json` already has the right config) |

Wait for the build. It prints a URL like `https://expensemate-xxxx.vercel.app`.

### Step 5 — Deploy to PRODUCTION (the permanent URL)
```bash
vercel --prod
```
You now get `https://<project>.vercel.app`. Open it in a browser → register → log in → use the app.

### Step 6 — Verify it works
```bash
curl https://<your-app>.vercel.app/api/currencies
```
You should get JSON with `rates`, `symbols`, `currencies`, `table`. Then click through the UI:
Dashboard → Add Transaction (try a **PKR** amount) → Currency tab (switch base currency, watch totals convert) → Analytics (charts) → CSV Tools.

---

## Method 2 — Deploy from GitHub (no CLI)

### Step 1 — Install Git (if needed)
<https://git-scm.com/downloads> → install with defaults → reopen terminal.

### Step 2 — Put the project on GitHub
Create an **empty** repo on github.com (no README/license — the folder already has files). Then:

```bash
cd ExpenseMate

git init
git add .
git commit -m "ExpenseMate: expense manager with multi-currency, budgets, alerts, charts"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/ExpenseMate.git
git push -u origin main
```

> **Add a `.gitignore` first** if you don't want junk in the repo:
> ```bash
> echo "__pycache__/" > .gitignore
> echo "*.pyc" >> .gitignore
> echo "app/data/" >> .gitignore
> echo ".pytest_cache/" >> .gitignore
> ```

### Step 3 — Import into Vercel
1. Go to <https://vercel.com/new>
2. Sign in with **GitHub** and allow Vercel to access your repos
3. Find **ExpenseMate** → click **Import**
4. On the configure screen:
   - **Framework Preset:** `Other`
   - **Build Command:** leave **empty**
   - **Output Directory:** leave **empty**
   - **Install Command:** leave **empty** (it reads `requirements.txt` automatically)
   - **Root Directory:** leave **empty** (project root)
5. Click **Deploy**

### Step 4 — Wait ~60–90 seconds
Vercel shows "Congratulations!" with your URL: `https://expensemate.vercel.app`.

### Step 5 — Every later change
```bash
git add .
git commit -m "update"
git push
```
Vercel auto-redeploys on push. Done.

---

## Environment variables (optional)

Vercel → your project → **Settings → Environment Variables**:

| Name | Value | Why |
|---|---|---|
| `EXPENSEMATE_DB` | `/tmp/data/expensemate.db` | Explicit DB location (already the default on Vercel) |
| `EXPENSEMATE_DB` | *a Turso/Neon URL* | Only if you switch to a persistent DB (see below) |

After adding/changing variables, click **Deployments → ⋯ → Redeploy**.

---

## Making the database persistent (pick ONE)

**Option A — Turso (libSQL): closest to "keep SQLite, just host it"**
1. Create a free account at <https://turso.tech>, make a database, copy its URL + auth token.
2. `pip install libsql-experimental` (or `libsql-client`).
3. In `app/backend/db.py`, when a Turso URL is present, connect with that driver instead of `sqlite3.connect(path)` — the SQL is unchanged (it *is* SQLite).
4. Add `TURSO_URL` / `TURSO_TOKEN` as Vercel env vars.

**Option B — Postgres on Neon/Supabase (free tiers)**
1. Create a free DB, copy the connection string.
2. `pip install psycopg2-binary` (add to `requirements.txt`).
3. Swap the `sqlite3` calls in `db.py` for `psycopg2` and change `?` placeholders to `%s`.
4. Put the connection string in a Vercel env var.

**Option C — Don't use Vercel for storage; use a host with a real disk**
Render, Railway, PythonAnywhere (details in the next section). Zero code changes.

> For a university submission, deploying on Vercel as-is and stating the limitation
> ("SQLite on serverless is ephemeral; persistent storage is future work") is a
> perfectly good, honest engineering answer — and it shows you understand the trade-off.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `Function crashed` / 500 on every page | The DB path isn't writable. Confirm `api/index.py` is being used (not `run.py`) and that `VERCEL` env handling points at `/tmp`. Check **Deployments → Functions → Logs**. |
| `ModuleNotFoundError: No module named 'app'` | `vercel.json` rewrite points at `api/index.py` but the `app/` folder wasn't bundled. Confirm `"includeFiles": "app/**"` is present (it is in this repo) and redeploy with `vercel --prod --force`. |
| `ModuleNotFoundError: No module named 'flask'` | `requirements.txt` missing/not at the repo **root**. It must list `Flask>=3.0`. |
| Page loads but **no styles / no charts** | Static files not bundled → same `includeFiles` fix; hard-refresh (Ctrl+F5). Chart.js is bundled locally (`/static/chart.umd.min.js`), so no CDN/internet is needed. |
| 404 on `/api/...` but `/` works | The rewrite rule was overridden. Re-check the `rewrites` block in `vercel.json`. |
| Data disappears after a while | Expected on Vercel (`/tmp` is ephemeral). Use Option A/B/C above. |
| Build says "no framework detected" | That's fine — we use the raw Python runtime via `builds`. Just Deploy. |
| Windows: `vercel` not recognized | Reopen terminal, or use `npx vercel`. |
| Want a nicer URL | Vercel → project → **Settings → Domains** → add/rename, e.g. `expensemate.vercel.app`. |

**Useful commands**
```bash
vercel ls                     # list deployments
vercel logs <url>             # stream function logs
vercel inspect <url>          # build details
vercel --prod --force         # redeploy ignoring cache
vercel remove <project>       # delete deployment
vercel whoami                 # confirm logged in
```

---

## Easier alternatives (same project, real disk, SQLite keeps working)

**Render (free tier, ~5 min)**
1. Push to GitHub → <https://render.com> → **New → Web Service** → pick the repo.
2. Runtime **Python 3**, Build `pip install -r requirements.txt`, Start `python run.py`.
3. Add env var `PORT=10000` (Render injects `PORT`; `run.py` already reads it).
4. Deploy → you get `https://expensemate.onrender.com`.
   *Note: free-tier disks are also ephemeral; attach a Render **Disk** for persistence.*

**Railway** — `railway init` → `railway up`, or connect the GitHub repo; it detects Python and runs `run.py`. Add a Volume for the DB.

**PythonAnywhere (simplest for Flask + SQLite)**
1. Sign up free → **Files** → upload the project ZIP → open a **Bash console** → unzip.
2. `pip install --user flask`
3. **Web → Add a new web app → Flask**, Python 3.x, source dir = your project folder,
   WSGI file edited to:
   ```python
   import sys
   path = "/home/<YOUR_USERNAME>/ExpenseMate"
   if path not in sys.path: sys.path.append(path)
   from app.backend.server import create_app
   application = create_app()
   ```
4. Reload the web app → `https://<username>.pythonanywhere.com`. SQLite persists on the real disk. ✅

---

## Deploying from PyCharm specifically

1. PyCharm → **View → Tool Windows → Terminal** (opens at the project root).
2. Run the Method 1 commands there exactly as written (`npm install -g vercel`, `vercel login`, `vercel --prod`).
3. Or use PyCharm's **Git** panel (top-right "Share Project on GitHub" button) for Method 2 Step 2, then import on vercel.com.
4. If PyCharm's terminal says `pip`/`npm` is not recognized → it's a PATH problem, not a project problem:
   use `py -m pip install ...` for Python, and reinstall/reopen for Node.
