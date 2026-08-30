import sys
import os
import traceback

# Add your project directory to the sys.path
project_home = os.path.dirname(__file__)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set up virtual environment
VENV_PATH = os.path.join(project_home, 'venv', 'bin', 'activate_this.py')
if os.path.exists(VENV_PATH):
    exec(open(VENV_PATH).read(), {'__file__': VENV_PATH})
else:
    # Modern venv (python -m venv) doesn't have activate_this.py
    # Manually add the site-packages to sys.path
    import site
    import glob
    venv_site = os.path.join(project_home, 'venv', 'lib')
    site_packages = glob.glob(os.path.join(venv_site, 'python*', 'site-packages'))
    if site_packages:
        site.addsitedir(site_packages[0])

# Load environment variables from .env if it exists
env_file = os.path.join(project_home, '.env')
if os.path.exists(env_file):
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"[passenger_wsgi] Loaded environment variables from {env_file}")
    except Exception as e:
        print(f"[passenger_wsgi] Error loading .env: {e}")
else:
    print(f"[passenger_wsgi] Warning: .env file not found at {env_file}")

# Import your Flask application (after loading env vars)
try:
    from app import app as application
    print("[passenger_wsgi] Successfully imported Flask app")

    # Also expose as 'app' for compatibility
    app = application
except Exception as e:
    print("[passenger_wsgi] ERROR: Failed to import Flask application")
    print(f"[passenger_wsgi] Error: {e}")
    print("[passenger_wsgi] Traceback:")
    traceback.print_exc()
    raise
