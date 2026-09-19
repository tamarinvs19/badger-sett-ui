from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("videos.urls")),
]

# Serve uploaded media (wallpapers) by the dev server only.
# In production nginx (or another web server) serves /media/ and /static/.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)