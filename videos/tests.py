from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import yandex
from .models import Video


class VideoModelTests(TestCase):
    def test_direct_file_detection(self):
        player = Video(name="A", video_url="https://runtime.strm.yandex.ru/player/vplv123")
        assert player.is_direct_file is False

        direct = Video(name="B", video_url="https://example.com/video.mp4")
        assert direct.is_direct_file is True

    def test_display_title_falls_back_to_link(self):
        video = Video(video_url="https://runtime.strm.yandex.ru/player/vplv1234567890")
        self.assertEqual(video.display_title, "vplv1234567890")
        video.name = "Named"
        self.assertEqual(video.display_title, "Named")


class YandexMetadataTests(TestCase):
    PLAYER_URL = "https://runtime.strm.yandex.ru/player/vplv1234567890"
    PLAYER_PAGE = "https://runtime.video.cloud.yandex.net/player/video/vplv1234567890"

    def test_extract_video_id_supported_formats(self):
        for url in (
            "https://runtime.strm.yandex.ru/player/vplv1234567890",
            "https://strm.yandex.ru/vplv1234567890",
            "https://runtime.video.cloud.yandex.net/player/video/vplv1234567890?autoplay=0&mute=0",
            "https://video.cloud.yandex.net/org/videos/vplv1234567890",
        ):
            self.assertEqual(yandex.extract_video_id(url), "vplv1234567890")

    def test_extract_video_id_returns_none(self):
        self.assertIsNone(yandex.extract_video_id("https://example.com/some/other/video"))
        self.assertIsNone(yandex.extract_video_id(""))

    def test_parse_og_metadata(self):
        html = """
        <meta property="og:title" content="My great video">
        <meta property="og:description" content="A short description">
        <meta property="og:image" content="/poster/vplv123.jpg">
        """
        meta = yandex.parse_og_metadata(html)
        self.assertEqual(meta["title"], "My great video")
        self.assertEqual(meta["description"], "A short description")
        self.assertTrue(meta["image"].startswith("https://runtime.video.cloud.yandex.net/"))

    def test_fetch_metadata_uses_player_page(self):
        html = '<meta property="og:title" content="Fetched title">' '<meta property="og:image" content="https://cdn.example/poster.jpg">'
        with mock.patch.object(yandex, "_http_get", return_value=html) as get:
            meta = yandex.fetch_metadata(self.PLAYER_URL)
        get.assert_called_once_with(self.PLAYER_PAGE)
        self.assertEqual(meta["name"], "Fetched title")
        self.assertEqual(meta["wallpaper_url"], "https://cdn.example/poster.jpg")

    def test_fetch_metadata_network_error_uses_id_as_name(self):
        with mock.patch.object(yandex, "_http_get", side_effect=OSError("boom")):
            meta = yandex.fetch_metadata(self.PLAYER_URL)
        self.assertEqual(meta["name"], "vplv1234567890")
        self.assertEqual(meta["description"], "")
        self.assertEqual(meta["wallpaper_url"], "")

    def test_fill_video_from_link_populates_empty_fields(self):
        video = Video(video_url=self.PLAYER_URL)
        html = (
            '<meta property="og:title" content="Autofilled name">'
            '<meta property="og:description" content="Autofilled description">'
            '<meta property="og:image" content="https://cdn.example/poster.jpg">'
        )
        poster = (b"\xff\xd8\xff\xe0fake-jpeg", ".jpg")
        with mock.patch.object(yandex, "_http_get", return_value=html), mock.patch.object(yandex, "download_poster", return_value=poster):
            filled = yandex.fill_video_from_link(video)
        self.assertEqual(filled, ["name", "description", "wallpaper"])
        self.assertEqual(video.name, "Autofilled name")
        self.assertEqual(video.description, "Autofilled description")
        self.assertTrue(video.wallpaper)

    def test_fill_video_from_link_keeps_existing_values(self):
        video = Video(name="Kept", description="Kept desc", video_url=self.PLAYER_URL)
        with mock.patch.object(yandex, "_http_get", return_value=""), mock.patch.object(yandex, "download_poster", return_value=None):
            filled = yandex.fill_video_from_link(video)
        self.assertEqual(filled, [])
        self.assertEqual(video.name, "Kept")
        self.assertEqual(video.description, "Kept desc")


class AdminAutoFillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@example.com", "secret")
        self.client.force_login(self.user)
        self.url = "https://runtime.strm.yandex.ru/player/vplv1234567890"

    @mock.patch("videos.admin.fill_video_from_link")
    def test_add_video_by_link_only(self, fill):
        fill.return_value = ["name", "description", "wallpaper"]
        response = self.client.post(
            reverse("admin:videos_video_add"),
            {"video_url": self.url, "auto_fill": "on", "_save": "Save"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        video = Video.objects.get(video_url=self.url)
        # untouched by the mocked fetch; fallback name derived from the link
        self.assertEqual(video.name, "vplv1234567890")
        fill.assert_called_once()

    @mock.patch("videos.admin.fill_video_from_link")
    def test_no_fetch_when_autofill_unchecked(self, fill):
        self.client.post(
            reverse("admin:videos_video_add"),
            {"name": "Manual", "video_url": self.url, "_save": "Save"},
            follow=True,
        )
        fill.assert_not_called()
        video = Video.objects.get(video_url=self.url)
        self.assertEqual(video.name, "Manual")


class HealthTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("videos:health"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})


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