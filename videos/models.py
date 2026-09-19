import re

from django.db import models
from django.urls import reverse

_VIDEO_ID_RE = re.compile(r"\b(vplv[a-zA-Z0-9]{6,})\b")


class Video(models.Model):
    """A single video shared on the site, stored in Yandex Cloud Video."""

    name = models.CharField(
        "Video name",
        max_length=200,
        blank=True,
        help_text="Can be left empty: when saving with auto-fill enabled it is fetched from the storage link.",
    )
    description = models.TextField("Description", blank=True)
    wallpaper = models.ImageField(
        "Wallpaper / poster",
        upload_to="wallpapers/",
        blank=True,
        help_text="Preview image shown in the catalog. Leave empty to use a placeholder.",
    )
    video_url = models.URLField(
        "Link to storage",
        help_text="Yandex Cloud Video player link "
        "(e.g. https://runtime.strm.yandex.ru/player/vplvXXXXXX) "
        "or a direct media file URL (mp4, webm, ...).",
    )
    created_at = models.DateTimeField("Created", auto_now_add=True)
    updated_at = models.DateTimeField("Updated", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "video"
        verbose_name_plural = "videos"

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        """Name with a fallback derived from the storage link."""
        if self.name.strip():
            return self.name
        match = _VIDEO_ID_RE.search(self.video_url or "")
        if match:
            return match.group(1)
        last = (self.video_url or "").rstrip("/").split("/")[-1].split("?")[0]
        return last or "Untitled video"

    def get_absolute_url(self):
        return reverse("videos:detail", kwargs={"pk": self.pk})

    @property
    def is_direct_file(self) -> bool:
        """True when the link points to a playable media file (uses <video> tag)."""
        path = self.video_url.split("?", 1)[0].lower()
        return path.endswith((".mp4", ".webm", ".mov", ".ogg", ".m3u8"))