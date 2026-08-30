# Hotel Sagar Bela — Website

A Flask-based website for Hotel Sagar Bela, Puri, with a public-facing site and an
admin dashboard for managing content (floors/rooms, image galleries, homepage
slider, offers, posts, and booking info). Content is stored in a SQLite database
and rendered with Jinja2 templates.

---

## Features

**Public site**
- Home page with an image slider, active offer banner, floors, and posts
- About, Services, and Contact pages
- Floor detail pages with image galleries
- Post detail pages
- Visitor counter (counts unique visits per session)
- SEO support: `robots.txt` and a dynamically generated `sitemap.xml`

**Admin dashboard** (`/dashboard`, login required)
- Manage floors: create, edit, delete
- Upload / delete gallery images per floor, edit captions
- Manage homepage slides (title, subtitle, image, order)
- Manage offers (with WhatsApp message, active toggle)
- Manage posts (content, image, order, active toggle)
- Update booking info (phone, cab phone, heading, subtext)

---

## Tech stack

- **Python / Flask** — web framework
- **Flask-SQLAlchemy** — ORM
- **SQLite** — database (`instance/floors.db`)
- **Jinja2** — templating
- **Gunicorn** — production WSGI server (also deployable via Passenger on cPanel)

---

## Project structure

```
website/
├── app.py                 # Main Flask application (routes, models, seed data)
├── passenger_wsgi.py      # WSGI entry point for cPanel / Passenger hosting
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment variables (local dev)
├── .env.production        # Template for production env vars (rename to .env on server)
├── .htaccess              # Security headers + file protection (Apache)
├── .gitignore
├── DEPLOYMENT.md          # Shared-hosting deployment guide
├── instance/
│   └── floors.db          # SQLite database (auto-created on first run)
├── templates/             # Jinja2 templates
│   ├── base.html, home.html, about.html, services.html, contact.html
│   ├── floor.html, post.html, login.html
│   └── dashboard/         # Admin dashboard templates
└── static/
    ├── css/               # Stylesheets
    ├── images/            # Site images
    └── uploads/           # User-uploaded images (created automatically)
```

---

## Configuration

The app reads these values from environment variables (with development fallbacks):

| Variable         | Purpose                                   | Default (dev only)                 |
|------------------|-------------------------------------------|------------------------------------|
| `SECRET_KEY`     | Flask session signing key                 | `dev-secret-key-change-in-production` |
| `ADMIN_USERNAME` | Dashboard login username                  | `admin`                            |
| `ADMIN_PASSWORD` | Dashboard login password                  | `admin123`                         |
| `FLASK_DEBUG`    | Enable debug mode (`True`/`False`)         | `False`                            |

For local development, copy `.env.example` to `.env` and fill in values.
**Never commit a real `.env` file.** In production, set a strong `SECRET_KEY` and
`ADMIN_PASSWORD`.

---

## Running locally

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Create a `.env` file from the example and set credentials:
   ```bash
   cp .env.example .env
   ```

4. Run the app:
   ```bash
   python app.py
   ```
   The app starts on http://127.0.0.1:5000

To enable auto-reload/debug during development:
```bash
FLASK_DEBUG=True python app.py
```

---

## Database

The SQLite database is created **automatically** on first run via `db.create_all()`
in `app.py`. On an empty database, it seeds default data:

- 3 floors (First, Second, Third)
- 3 homepage slides
- A visitor counter (starting at 0)
- Default booking info

No manual migration or setup command is needed. To keep existing data when moving
servers, copy `instance/floors.db`. To start fresh, simply omit it and the app
rebuilds it.

> Note: `db.create_all()` only creates missing tables; it does not alter existing
> ones. If you change a model's columns later, you'll need to migrate manually.

---

## Admin access

Visit `/login` and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
After login, the dashboard is available at `/dashboard`.

---

## Deployment

This app is built to run on cPanel shared hosting via Phusion Passenger (the same
setup used for the related `expense-dashboard` project). See **`DEPLOYMENT.md`** for
full step-by-step instructions.

Quick summary:
1. Set a strong `ADMIN_PASSWORD` in `.env.production`.
2. Upload the project (excluding `venv/`, `.git/`, `__pycache__/`, `.DS_Store`).
3. Copy `.env.production` to `.env` on the server.
4. In cPanel → **Setup Python App**: startup file `passenger_wsgi.py`, entry point `application`.
5. Install `requirements.txt`, make `instance/` and `static/uploads/` writable, then restart.

---

## Security notes

- Secrets are read from environment variables — do not hardcode them.
- Debug mode is off by default in production.
- `.htaccess` blocks direct web access to `.env`, `app.py`, `passenger_wsgi.py`, and `*.db`.
- Enable HTTPS on your domain and back up `instance/floors.db` regularly.
- Max upload size is 16 MB; allowed image types: png, jpg, jpeg, gif, svg, webp.
