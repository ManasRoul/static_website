# Deployment Guide — Website (Flask on cPanel Shared Hosting)

This app uses the same hosting pattern as the working `expense-dashboard`:
cPanel **Setup Python App** (Phusion Passenger) + `passenger_wsgi.py` + a `.env` file.
Difference: this app keeps **SQLite** (no MySQL setup needed).

---

## Files in this project (what they do)

- `app.py` — the Flask application. Reads `SECRET_KEY`, `ADMIN_USERNAME`,
  `ADMIN_PASSWORD` from environment variables. Debug is OFF unless `FLASK_DEBUG=True`.
- `passenger_wsgi.py` — entry point Passenger uses. Loads the venv + `.env`,
  then imports `from app import app as application`.
- `.env.production` — template with a pre-generated SECRET_KEY. Rename to `.env` on server.
- `.env.example` — reference copy for local development.
- `.htaccess` — security headers, disables directory listing, blocks direct access to
  `.env`, `app.py`, `passenger_wsgi.py`, and `*.db`.
- `.gitignore` — keeps venv/secrets/db/uploads out of Git.
- `requirements.txt` — flask, flask-sqlalchemy, gunicorn.

---

## Step-by-step deployment

### 1. Set your admin password
Open `.env.production`, set a strong `ADMIN_PASSWORD` (and change `ADMIN_USERNAME`
if you want). The `SECRET_KEY` is already filled with a random value.

### 2. Upload files via FTP or cPanel File Manager
Upload the whole project into a folder under your account, e.g.
`/home/USERNAME/website` (or into `public_html/website`).

Upload everything EXCEPT:
- `venv/`            (recreated on the server)
- `__pycache__/`
- `.DS_Store`
- `.git/`

DO upload:
- `app.py`, `passenger_wsgi.py`, `requirements.txt`, `.htaccess`
- `templates/`, `static/` (including `static/uploads/` if you want existing images)
- `instance/floors.db` ONLY if you want to keep your current data. If you skip it,
  the app auto-creates a fresh database with default seed data on first run.

### 3. Create the .env file on the server
In the app folder, copy `.env.production` to `.env`:
```
cp .env.production .env
```
(Or rename it in File Manager. The filename must be exactly `.env`.)

### 4. Create the Python App in cPanel
cPanel → **Setup Python App** → Create Application:
- Python version: 3.x (highest available)
- Application root: `/home/USERNAME/website`  (the folder you uploaded to)
- Application URL: your domain or subdomain (e.g. `website` or a subdomain)
- Application startup file: `passenger_wsgi.py`
- Application Entry point: `application`

Save. cPanel creates a `venv` for the app.

### 5. Install dependencies
In the Setup Python App screen, use "Run Pip Install" with `requirements.txt`,
OR via SSH:
```
cd /home/USERNAME/website
source /home/USERNAME/virtualenv/website/3.x/bin/activate   # path shown in cPanel
pip install -r requirements.txt
```

### 6. Make sure the app can write its data
SQLite and uploads need writable folders:
```
chmod -R 755 instance static/uploads
```
The `instance/` folder must exist and be writable so `floors.db` can be created/updated.
The app creates `static/uploads/` automatically if missing.

### 7. Restart the app
In cPanel Setup Python App, click **Restart**.

### 8. Test
- Visit your site root — the home page should load.
- Visit `/login` and log in with your `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
- Confirm the dashboard loads and you can upload an image.

---

## Troubleshooting

- **500 error:** Check cPanel → Errors / the app's `stderr` log. The
  `passenger_wsgi.py` prints import errors and tracebacks there.
- **"No module named flask":** dependencies not installed into the app's venv —
  redo step 5 with the correct venv activated.
- **Login fails:** `.env` not loaded. Confirm the file is named exactly `.env`,
  is in the app root, and you restarted the app.
- **Images upload but don't persist / permission denied:** `static/uploads` or
  `instance/` not writable — redo step 6.
- **Changes not taking effect:** always **Restart** the Python App after edits.

---

## Security reminders
- Never commit the real `.env` (already in `.gitignore`).
- Use a strong `ADMIN_PASSWORD`.
- Enable HTTPS (free Let's Encrypt SSL in cPanel).
- Back up `instance/floors.db` periodically — it holds all your content.
