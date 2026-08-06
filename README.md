# Django on Vercel

A Django starter with server-rendered templates and a Django REST Framework API,
backed by Neon Postgres and ready to deploy on Vercel.

## Stack

- **Django 5.1** — web framework (templates + admin)
- **Django REST Framework** — JSON API at `/api/`
- **Neon Postgres** — database via the `DATABASE_URL` environment variable
- **WhiteNoise** — static file serving

## Project layout

```
config/         Django project (settings, urls, wsgi/asgi)
core/           Template-rendered pages (home, task CRUD)
api/            DRF API (Task model, serializer, viewset)
templates/      HTML templates
static/         CSS and static assets
vercel.json     Vercel build & routing config
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

The app reads `DATABASE_URL` from the environment (or `.env.development.local`).
Without it, Django falls back to a local SQLite database.

## Endpoints

- `/` — home page with a task list and create form
- `/api/tasks/` — REST API (list, create, retrieve, update, delete)
- `/admin/` — Django admin

## Deploying to Vercel

The `DATABASE_URL` is already provided by the Neon integration. Push to your
connected Git repository or run `vercel deploy`. The build step installs
dependencies and runs `collectstatic`; apply migrations against Neon with
`python manage.py migrate` (e.g. from a local shell pointed at the same
`DATABASE_URL`).
