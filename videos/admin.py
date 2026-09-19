from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Video
from .yandex import fill_video_from_link


class VideoAdminForm(forms.ModelForm):
    auto_fill = forms.BooleanField(
        required=False,
        initial=True,
        label="Fill fields from the storage link",
        help_text=(
            "Fetch name, description and wallpaper from Yandex Cloud Video and "
            "fill the fields left empty. Uncheck to enter everything manually."
        ),
    )

    class Meta:
        model = Video
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When editing an already complete video, don't refetch by default.
        if self.instance.pk and (
            self.instance.name or self.instance.description or self.instance.wallpaper
        ):
            self.fields["auto_fill"].initial = False


@admin.action(description="Fill empty fields from storage link")
def fill_from_link(modeladmin, request, queryset):
    """Changelist action: fetch metadata for the selected videos."""
    updated = 0
    for video in queryset:
        if fill_video_from_link(video):
            video.save()
            updated += 1
    modeladmin.message_user(request, f"Filled metadata for {updated} video(s) from their links.")


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    form = VideoAdminForm
    actions = [fill_from_link]
    list_display = ("name", "wallpaper_preview", "video_url", "created_at")
    list_display_links = ("name", "wallpaper_preview")
    search_fields = ("name", "description", "video_url")
    readonly_fields = ("created_at", "updated_at", "wallpaper_preview")
    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (
            "Media",
            {
                "fields": ("wallpaper", "wallpaper_preview", "video_url"),
                "description": "The video itself is stored in Yandex Cloud Video; "
                "here you manage the poster and the link to it.",
            },
        ),
        (
            "Import from link",
            {
                "fields": ("auto_fill",),
                "description": "Paste only the storage link above, leave the fields empty, "
                "tick this box and save — name, description and wallpaper are fetched "
                "from the link automatically.",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("auto_fill"):
            filled = fill_video_from_link(obj)
            if not obj.name and obj.video_url:
                obj.name = obj.display_title  # fallback name derived from the link
                filled.append("name (fallback)")
            if filled:
                self.message_user(request, f"Auto-filled from link: {', '.join(filled)}.")
            else:
                self.message_user(
                    request,
                    "Could not fetch metadata from the link (is the video public?).",
                )
        super().save_model(request, obj, form, change)

    @admin.display(description="Wallpaper")
    def wallpaper_preview(self, obj):
        if not obj.wallpaper:
            return "— no image"
        return format_html(
            '<img src="{}" alt="{}" style="max-height:48px;border-radius:4px;'
            'max-width:86px;object-fit:cover;">',
            obj.wallpaper.url,
            obj.display_title,
        )