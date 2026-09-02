from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

from hub.adapters.google_home_adapter import GoogleHomeAdapter, discover_google_home_devices
from hub.models import CastingDevice


@patch("hub.adapters.google_home_adapter.GoogleCastAdapter")
def test_speak_text_uses_tts_template(mock_cast_class):
    mock_cast = mock_cast_class.return_value
    mock_cast.connect.return_value = True
    mock_cast.play_media.return_value = True

    adapter = GoogleHomeAdapter(
        {
            "name": "Kitchen Home",
            "tts_url_template": "http://tts.local/say?text={text}",
        }
    )

    assert adapter.speak_text("hello world") is True
    expected_url = f"http://tts.local/say?text={quote_plus('hello world')}"
    mock_cast.play_media.assert_called_once()
    assert mock_cast.play_media.call_args.args[0] == expected_url


@patch("hub.adapters.google_home_adapter.GoogleCastAdapter")
def test_play_media_uses_cast_adapter(mock_cast_class):
    mock_cast = mock_cast_class.return_value
    mock_cast.connect.return_value = True
    mock_cast.play_media.return_value = True

    adapter = GoogleHomeAdapter(
        {
            "name": "Kitchen Home",
            "media_content_type": "audio/ogg",
        }
    )

    assert adapter.play_media("http://example.com/audio.ogg", title="Song") is True
    mock_cast.play_media.assert_called_once_with(
        "http://example.com/audio.ogg",
        content_type="audio/ogg",
        title="Song",
        thumb="",
    )


def test_speak_text_requires_template():
    adapter = GoogleHomeAdapter({"name": "Kitchen Home"})
    assert adapter.speak_text("hello") is False


@patch("hub.adapters.google_home_adapter.discover_google_cast_devices")
def test_discover_google_home_devices_filters_by_name(mock_discover):
    mock_discover.return_value = [
        CastingDevice(name="Kitchen Home", friendly_name="Kitchen Home"),
        CastingDevice(name="Living Nest", friendly_name="Living Nest"),
        CastingDevice(name="Bedroom TV", friendly_name="Bedroom TV"),
    ]

    devices = discover_google_home_devices()
    device_names = [device.name for device in devices]

    assert "Kitchen Home" in device_names
    assert "Living Nest" in device_names
    assert "Bedroom TV" not in device_names
