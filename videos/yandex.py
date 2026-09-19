"""Fetching metadata for a video from its Yandex Cloud Video storage link.

The public player page (https://runtime.video.cloud.yandex.net/player/video/<id>)
is server-rendered and carries Open Graph meta tags (title, description,
image), so a storage link alone is enough to fill in name, description and
wallpaper. Everything here degrades gracefully: on any failure the video is
still usable, just with a name derived from the link.
"""

import mimetypes
import re
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile

_PLAYER_BASE = "https://runtime.video.cloud.yandex.net"
_USER_AGENT = "Mozilla/5.0 (compatible; BadgerSett/1.0)"
_TIMEOUT = 10
_MAX_POSTER_BYTES = 10 * 1024 * 1024

_VIDEO_ID_RE = re.compile(r"\b(vplv[a-zA-Z0-9]{6,})\b")

# Candidate <meta> tags per field, tried in order.
_OG_TAGS = {
    "title": ["og:title", "twitter:title"],
    "description": ["og:description", "twitter:description", "description"],
    "image": ["og:image", "twitter:image", "twitter:image:src"],
}
_META_RE = re.compile(r"<meta\s+(?P<attrs>[^>]*?)/?>", re.IGNORECASE)


def extract_video_id(url):
    """Return the Yandex Cloud Video id (vplv...) from any supported URL, or None."""
    if not url:
        return None
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def player_page_url(video_id):
    """Public player page carrying Open Graph metadata for a video id."""
    return f"{_PLAYER_BASE}/player/video/{video_id}"


def default_name(url):
    """A sensible display name for a video when nothing better is available."""
    video_id = extract_video_id(url)
    if video_id:
        return video_id
    path = unquote(urlsplit(url or "").path).strip("/")
    segment = path.split("/")[-1] if path else ""
    return segment or "Untitled video"


def _http_get(url):
    """Fetch a URL as text. Raises on transport errors."""
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def _attr_value(attrs, attr_name):
    match = re.search(attr_name + r'\s*=\s*"([^"]*)"', attrs, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(attr_name + r"\s*=\s*'([^']*)'", attrs, re.IGNORECASE)
    return match.group(1) if match else ""


def parse_og_metadata(html):
    """Extract title/description/image from Open Graph meta tags of a page."""
    result = {"title": "", "description": "", "image": ""}
    for match in _META_RE.finditer(html or ""):
        attrs = match.group("attrs")
        tag_name = _attr_value(attrs, "property") or _attr_value(attrs, "name")
        if not tag_name:
            continue
        for key, candidates in _OG_TAGS.items():
            if tag_name.lower() in candidates and not result[key]:
                result[key] = _attr_value(attrs, "content")
    if result["image"].startswith("/"):
        result["image"] = f"{_PLAYER_BASE}{result['image']}"
    return result


def fetch_metadata(video_url):
    """Return {"name", "description", "wallpaper_url"} for a storage link.

    Never raises. When the player page is unreachable or carries no metadata,
    the name falls back to the video id / last URL segment.
    """
    video_id = extract_video_id(video_url)
    name = video_id or default_name(video_url)
    if not video_id:
        return {"name": name, "description": "", "wallpaper_url": ""}
    try:
        html = _http_get(player_page_url(video_id))
    except (HTTPError, URLError, OSError, ValueError):
        return {"name": name, "description": "", "wallpaper_url": ""}
    og = parse_og_metadata(html)
    return {
        "name": og["title"] or name,
        "description": og["description"],
        "wallpaper_url": og["image"],
    }


def download_poster(url):
    """Download a poster image; returns (bytes, extension) or None."""
    if not url:
        return None
    try:
        request = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(request, timeout=_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if not content_type.startswith("image/"):
                return None
            data = response.read(_MAX_POSTER_BYTES + 1)
        if not data or len(data) > _MAX_POSTER_BYTES:
            return None
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext in (".jpe", ".jfif"):
            ext = ".jpg"
        return data, ext
    except (HTTPError, URLError, OSError, ValueError):
        return None


def fill_video_from_link(video):
    """Fill empty name/description/wallpaper of a Video from its storage link.

    Returns the list of field names that were filled ([] if none). The poster
    is saved into the ImageField; the model itself is not saved here.
    """
    meta = fetch_metadata(video.video_url)
    filled = []
    if not video.name and meta.get("name"):
        video.name = meta["name"].strip()
        filled.append("name")
    if not video.description and meta.get("description"):
        video.description = meta["description"].strip()
        filled.append("description")
    if not video.wallpaper and meta.get("wallpaper_url"):
        image = download_poster(meta["wallpaper_url"])
        if image:
            data, ext = image
            video_id = extract_video_id(video.video_url) or "video"
            video.wallpaper.save(f"wallpaper_{video_id}{ext}", ContentFile(data), save=False)
            filled.append("wallpaper")
    return filled