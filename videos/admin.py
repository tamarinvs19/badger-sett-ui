from django.contrib import admin
from django.utils.html import format_html

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("name", "wallpaper_preview", "video_url", "created_at")
    list_display_links = ("name", "wallpaper_preview")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "wallpaper_preview")
    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (
            "Media",
            {
                "fields": ("wallpaper", "wallpaper_preview", "video_url"),
                "description": "The video itself is stored in Yandex Cloud Video; "
                "here you only manage the poster and the link to it.",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Wallpaper")
    def wallpaper_preview(self, obj):
        if not obj.wallpaper:
            return "— no image"
        return format_html(
            '<img src="{}" alt="{}" style="max-height:48px;border-radius:4px;'
            'max-width:86px;object-fit:cover;">',
            obj.wallpaper.url,
            obj.name,
        )