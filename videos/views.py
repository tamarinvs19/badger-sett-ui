from django.http import JsonResponse
from django.views.generic import DetailView, ListView

from .models import Video


def health(request):
    """Liveness probe for load balancers / orchestrators."""
    return JsonResponse({"status": "ok"})


class VideoListView(ListView):
    """Main page: all videos in a YouTube-style grid, newest first."""

    model = Video
    template_name = "videos/video_list.html"
    context_object_name = "videos"


class VideoDetailView(DetailView):
    """Single video page with the player embedded from Yandex Cloud Video."""

    model = Video
    template_name = "videos/video_detail.html"
    context_object_name = "video"