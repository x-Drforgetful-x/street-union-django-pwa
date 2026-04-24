# Street Union PWA Deployment Notes

This build includes PWA support so the Django system can be installed on an iPhone from Safari.

## PWA files added
- static/manifest.json
- static/icons/app-icon-192.png
- static/icons/app-icon-512.png
- templates/service-worker.js
- /service-worker.js route in config/urls.py
- service worker registration in templates/base.html

## Production files added
- Procfile
- build.sh
- .env.example
- .gitignore
- production-ready requirements.txt
- WhiteNoise static file support
- DATABASE_URL support for PostgreSQL or SQLite fallback

## Local test

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Render build command

```bash
./build.sh
```

## Render start command

```bash
gunicorn config.wsgi:application
```

## Render environment variables

```env
DEBUG=False
SECRET_KEY=replace-with-a-long-secret-key
ALLOWED_HOSTS=your-app-name.onrender.com
SECURE_SSL_REDIRECT=True
```

If using a Render PostgreSQL database, add the DATABASE_URL from Render.
