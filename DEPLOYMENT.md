# Deploying Zaika to Railway — Step by Step

Your app's real name is **Zaika** — that's set on the login screen and it's what
you'll name the Railway project too. This guide takes you from "nothing online"
to a public URL anyone can open.

Time: about 20-30 minutes. Cost: Railway's free trial credit covers this
comfortably to start; after that it's usage-based, roughly $5-10/month for an
app this size.

---

## Before you start

You need a **GitHub account** (Railway deploys by connecting to a GitHub repo,
not by file upload). If you don't have your code on GitHub yet:

1. Create a new repository at github.com → name it `zaika` (or `zaika-backend`)
2. In your project folder (the one from this zip), run:
   ```
   git init
   git add .
   git commit -m "Zaika - ready to deploy"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/zaika.git
   git push -u origin main
   ```
   **Important:** `.env` is in `.gitignore` on purpose — your real secrets
   (Cloudinary, Razorpay) should never go to GitHub. You'll re-enter them
   directly into Railway in Step 4.

---

## Step 1 — Create the Railway project

1. Go to **railway.com** → sign up (GitHub login is easiest, since you'll
   need that connection anyway)
2. Click **New Project** → **Deploy from GitHub repo**
3. Pick your `zaika` repo → Railway starts building automatically
4. Rename the project itself to **Zaika** (top-left, click the project name)

Railway auto-detects this is a Python app (via `requirements.txt`) and a
`Procfile` (already in this zip, tells it to run with gunicorn — the dev
server we've been using isn't safe for production).

## Step 2 — Add the MySQL database

1. In your Zaika project, click **+ New** → **Database** → **Add MySQL**
2. That's it — Railway creates a managed MySQL instance in the same project
3. Click the MySQL service → **Data** tab → **Query** — paste in the full
   contents of `database/schema.sql` and run it. This creates all 9 tables.

Your Flask service will automatically see this database's connection details
— that's what the config.py change in this zip was for (it reads Railway's
`MYSQLHOST`/`MYSQLUSER`/etc. automatically, no manual wiring needed).

## Step 3 — Generate a public URL

1. Click your **web service** (the Flask app, not the MySQL one) → **Settings** → **Networking**
2. Click **Generate Domain**
3. You'll get something like `zaika-production.up.railway.app` — that's
   your live app, today. (A custom domain like `zaika.in` can be added later
   from this same screen once you own one.)

## Step 4 — Set environment variables

Click your web service → **Variables** tab → **New Variable**, add each of these:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any long random string (e.g. generate one at randomkeygen.com) |
| `JWT_SECRET_KEY` | a **different** long random string |
| `FLASK_ENV` | `production` |
| `RAZORPAY_KEY_ID` | from your Razorpay dashboard (if using payments) |
| `RAZORPAY_KEY_SECRET` | from your Razorpay dashboard |
| `CLOUDINARY_CLOUD_NAME` | `pm6rcioz` |
| `CLOUDINARY_API_KEY` | `361969227951825` |
| `CLOUDINARY_API_SECRET` | `6w7EnCwhD6SJzI84xHND5CcS1GY` |

You do **not** need to set `DB_USER`/`DB_HOST`/etc. — those come from the
MySQL service automatically once it's in the same project.

Railway redeploys automatically every time you save a variable.

## Step 5 — Create your admin account

Same script as local, just run it against Railway's database instead:

1. Web service → **Settings** → find the **Deploy** section → there's a way
   to open a one-off shell (search "Railway run command" in their docs if
   the button isn't obvious — this changes occasionally)
2. Run: `python create_admin.py`
3. Answer the prompts — this creates your first admin login

## Step 6 — Test it

Open your Railway domain in a browser. You should see the Zaika login
screen. Register a test customer, browse (empty until a restaurant signs
up), and confirm the whole thing loads — that confirms WhiteNoise is
serving `static/js/app.js` correctly and the database connection works.

---

## What changed in this zip to make this possible
- `Procfile` — tells Railway to run with `gunicorn`, not Flask's dev server
- `app/config.py` — now reads Railway's MySQL variables automatically, falls
  back to your local XAMPP `.env` values when there's no Railway variable
- `app/__init__.py` — added WhiteNoise, so `/static/*` files (your whole
  frontend) serve reliably behind Railway's proxy — this is a real, common
  gotcha that silently breaks the frontend if skipped
- `run.py` — binds to Railway's dynamic `$PORT` instead of a hardcoded 5000

## If something breaks
- **Blank page / no styling**: check the deploy logs (web service → Deployments → View Logs) for a WhiteNoise or static-file error
- **500 error on any page touching the database**: MySQL variables didn't link — check the web service's Variables tab shows the Mysql ones with a "connected" icon
- **"relation does not exist" type errors**: schema.sql wasn't run — go back to Step 2
