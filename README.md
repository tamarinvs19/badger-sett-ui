# VideoShare — minimal video sharing site (Django + Yandex Cloud Video)

A tiny web service to share a catalog of videos. Videos live in
[Yandex Cloud Video](https://cloud.yandex.com/services/video); this app only
stores metadata (name, description, poster wallpaper, and the link to the
storage) and serves a YouTube-style catalog plus a player page.

## Features

- Single `Video` model: `name`, `description`, `wallpaper` (poster image),
  `video_url` (link to Yandex Cloud Video), timestamps.
- Django admin for adding/editing videos, uploads wallpaper, shows a preview,
  and links out to Yandex Cloud Video.
- `/` — all videos in a responsive YouTube-style grid (newest first).
- `/video/<id>/` — full page with the embedded player (16:9).
- Production mode via WSGI: `gunicorn` + `config.wsgi`, environment-driven
  settings, WhiteNoise for static files, ready for nginx in front.

## Project layout

```
config/            Django project (settings, urls, wsgi)
videos/            The app: model, admin, views, templates
static/css/        Minimal stylesheet
media/             Uploaded wallpapers (gitignored)
staticfiles/       Output of collectstatic (gitignored)
gunicorn.conf.py   Production WSGI server config
```

## Getting the video link from Yandex Cloud Video

1. Upload your video in the Yandex Cloud Video console.
2. Open it and copy the **player link**, it looks like
   `https://runtime.strm.yandex.ru/player/vplvXXXXXX`. Paste it into the
   **Link to storage** field in the admin.
3. Optionally download/upload the poster image as the **wallpaper**.

The template embeds the player link in an `<iframe>`. If you paste a direct
media URL instead (e.g. `.mp4`), the page renders a plain `<video>` tag, so
both work.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/ and `/admin/` to add videos.

## Production (WSGI)

```bash
# 1. Install dependencies and configure
cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_DEBUG=false

# 2. Prepare the database and static files
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput

# 3. Run behind a reverse proxy
gunicorn -c gunicorn.conf.py
```

Sample nginx site:

```nginx
server {
    listen 80;
    server_name example.com;

    client_max_body_size 25m;  # uploaded wallpapers

    location /static/ {
        alias /srv/videoshare/staticfiles/;
    }
    location /media/ {
        alias /srv/videoshare/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Run gunicorn on `127.0.0.1:8000` for the socket that nginx proxies to
(override with `-b`), and terminate TLS in nginx. Static files come from
WhiteNoise; uploaded wallpapers under `/media/` are served by nginx.

## Tests

```bash
.venv/bin/python manage.py test
```