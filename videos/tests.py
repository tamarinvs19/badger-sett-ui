from django.test import TestCase
from django.urls import reverse

from .models import Video


class VideoModelTests(TestCase):
    def test_direct_file_detection(self):
        player = Video(name="A", video_url="https://runtime.strm.yandex.ru/player/vplv123")
        assert player.is_direct_file is False

        direct = Video(name="B", video_url="https://example.com/video.mp4")
        assert direct.is_direct_file is True


class VideoViewTests(TestCase):
    def setUp(self):
        self.video = Video.objects.create(
            name="First video",
            description="Hello",
            video_url="https://runtime.strm.yandex.ru/player/vplv123",
        )
        Video.objects.create(
            name="Second video",
            video_url="https://example.com/clip.mp4",
        )

    def test_list_page_shows_all_videos(self):
        response = self.client.get(reverse("videos:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First video")
        self.assertContains(response, "Second video")

    def test_detail_page_renders_player(self):
        response = self.client.get(self.video.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.video_url)
        self.assertContains(response, 'class="player"')

    def test_detail_page_not_found(self):
        response = self.client.get(reverse("videos:detail", kwargs={"pk": 999}))
        self.assertEqual(response.status_code, 404)