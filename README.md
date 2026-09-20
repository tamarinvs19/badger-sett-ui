# Badger Sett — minimal video sharing site (Django + Yandex Cloud Video)

A tiny web service to share a catalog of videos. Videos live in
[Yandex Cloud Video](https://cloud.yandex.com/services/video); this app only
stores metadata (name, description, poster wallpaper, and the link to the
storage) and serves a YouTube-style catalog plus a player page.

## Features

- Single `Video` model: `name`, `description`, `wallpaper` (poster image),
  `video_url` (link to Yandex Cloud Video), timestamps.
- Django admin for adding/editing videos, uploads wallpaper, shows a preview,
  and links out to Yandex Cloud Video.
- **Add a video by link only**: paste the storage link, leave the fields
  empty, and the name, description and wallpaper are fetched from the link
  automatically (an "Import from link" checkbox in the admin controls it; a
  changelist action "Fill empty fields from storage link" does the same for
  existing rows).
- `/` — all videos in a responsive YouTube-style grid (newest first).
- `/video/<id>/` — full page with the embedded player (16:9).
- `/health` — liveness probe, returns `{"status": "ok"}` with HTTP 200
  (useful for load balancers, uptime checks, Kubernetes probes).
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

### Adding a video by link only

On the admin "Add video" page you only need to paste the storage link and
save — the **Import from link** checkbox (ticked by default) fetches the
name, description and wallpaper from Yandex Cloud Video and fills the empty
fields. This works because the public player page
(`runtime.video.cloud.yandex.net/player/video/<id>`) is server-rendered with
Open Graph meta tags, so no API credentials are needed (`videos/yandex.py`).

Notes:

- The video must be **published and publicly accessible** — otherwise Yandex
  serves an empty page and the metadata can't be fetched.
- Only empty fields are filled: a name or description you typed yourself is
  never overwritten.
- If fetching fails, the video is still saved, with its name derived from the
  link (the video id `vplv…` or the last URL segment).
- The wallpaper is downloaded into your own `media/wallpapers/` folder; a
  video with no wallpaper shows a placeholder in the catalog.

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

Point load balancer/uptime health checks at `http://host/health`.

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

### Run as a systemd service

The repo ships a ready-made systemd unit for gunicorn:
[`deploy/badger-sett.service`](deploy/badger-sett.service). Assuming the app
lives at `/srv/badger-sett`:

```bash
# 1. deploy the code to /srv/badger-sett and create the venv + .env there,
#    then make sure the service user can write the database and uploads:
sudo chown -R www-data:www-data /srv/badger-sett

# 2. install the unit and start it
sudo cp deploy/badger-sett.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now badger-sett

# 3. verify
systemctl status badger-sett
journalctl -u badger-sett -f
curl http://127.0.0.1:8000/health/
```

The unit runs gunicorn as `www-data`, loads the app `.env`, binds to
`127.0.0.1:8000` (overriding `gunicorn.conf.py` — nginx proxies to it), and
restarts on failure. Override paths or options with a drop-in:

```bash
sudo systemctl edit badger-sett
```

## Tests

```bash
.venv/bin/python manage.py test
```