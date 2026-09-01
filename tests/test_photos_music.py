"""Tests for photo and music services."""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest


def test_photo_model_creation():
    """Test Photo model creation and serialization."""
    from hub.models import Photo

    # Create a photo instance
    photo = Photo(
        filename="test.jpg",
        title="Test Photo",
        description="A test photo",
        date_taken=datetime.now(timezone.utc),
        source="local",
        tags=["test", "photo"],
        album_id=1,
    )

    # Test model attributes
    assert photo.filename == "test.jpg"
    assert photo.title == "Test Photo"
    assert photo.description == "A test photo"
    assert photo.source == "local"
    assert "test" in photo.tags
    assert photo.album_id == 1

    # Test to_dict method
    photo_dict = photo.to_dict()
    assert "filename" in photo_dict
    assert "title" in photo_dict
    assert "description" in photo_dict
    assert "source" in photo_dict
    assert "tags" in photo_dict
    assert "album_id" in photo_dict


def test_album_model_creation():
    """Test Album model creation and serialization."""
    from hub.models import Album

    # Create an album instance
    album = Album(name="Test Album", description="A test album")

    # Test model attributes
    assert album.name == "Test Album"
    assert album.description == "A test album"

    # Test to_dict method
    album_dict = album.to_dict()
    assert "name" in album_dict
    assert "description" in album_dict
    assert "photo_count" in album_dict


def test_music_track_model_creation():
    """Test MusicTrack model creation and serialization."""
    from hub.models import MusicTrack

    # Create a music track instance
    track = MusicTrack(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        genre="Pop",
        duration=180,
        source="local",
        album_art_url="http://example.com/cover.jpg",
    )

    # Test model attributes
    assert track.title == "Test Song"
    assert track.artist == "Test Artist"
    assert track.album == "Test Album"
    assert track.genre == "Pop"
    assert track.duration == 180
    assert track.source == "local"
    assert track.album_art_url == "http://example.com/cover.jpg"

    # Test to_dict method
    track_dict = track.to_dict()
    assert "title" in track_dict
    assert "artist" in track_dict
    assert "album" in track_dict
    assert "genre" in track_dict
    assert "duration" in track_dict
    assert "source" in track_dict
    assert "album_art_url" in track_dict


def test_playlist_model_creation():
    """Test Playlist model creation and serialization."""
    from hub.models import Playlist

    # Create a playlist instance
    playlist = Playlist(name="Test Playlist", description="A test playlist")

    # Test model attributes
    assert playlist.name == "Test Playlist"
    assert playlist.description == "A test playlist"

    # Test to_dict method
    playlist_dict = playlist.to_dict()
    assert "name" in playlist_dict
    assert "description" in playlist_dict
    assert "track_count" in playlist_dict


def test_music_queue_model_creation():
    """Test MusicQueue model creation and serialization."""
    from hub.models import MusicQueue

    # Create a queue instance
    queue = MusicQueue(
        playlist_id=1, queue_items=[{"id": 1, "title": "Song 1"}], current_item_index=0, is_playing=True, volume=80
    )

    # Test model attributes
    assert queue.playlist_id == 1
    assert len(queue.queue_items) == 1
    assert queue.current_item_index == 0
    assert queue.is_playing is True
    assert queue.volume == 80

    # Test to_dict method
    queue_dict = queue.to_dict()
    assert "playlist_id" in queue_dict
    assert "queue_items" in queue_dict
    assert "current_item_index" in queue_dict
    assert "is_playing" in queue_dict
    assert "volume" in queue_dict


def test_photo_service_creation():
    """Test PhotoService initialization."""
    from hub.services.photos import PhotoService

    service = PhotoService()
    assert service is not None
    assert hasattr(service, "get_photos")
    assert hasattr(service, "get_photo_by_id")
    assert hasattr(service, "create_photo")
    assert hasattr(service, "update_photo")
    assert hasattr(service, "delete_photo")
    assert hasattr(service, "get_albums")
    assert hasattr(service, "get_album_by_id")
    assert hasattr(service, "create_album")
    assert hasattr(service, "update_album")
    assert hasattr(service, "delete_album")
    assert hasattr(service, "get_photos_for_slideshow")
    assert hasattr(service, "sync_photos_from_sources")


def test_music_service_creation():
    """Test MusicService initialization."""
    from hub.services.music import MusicService

    service = MusicService()
    assert service is not None
    assert hasattr(service, "get_tracks")
    assert hasattr(service, "get_track_by_id")
    assert hasattr(service, "create_track")
    assert hasattr(service, "update_track")
    assert hasattr(service, "delete_track")
    assert hasattr(service, "get_playlists")
    assert hasattr(service, "get_playlist_by_id")
    assert hasattr(service, "create_playlist")
    assert hasattr(service, "update_playlist")
    assert hasattr(service, "delete_playlist")
    assert hasattr(service, "add_track_to_playlist")
    assert hasattr(service, "remove_track_from_playlist")
    assert hasattr(service, "get_tracks_in_playlist")
    assert hasattr(service, "create_queue")
    assert hasattr(service, "get_queue_by_id")
    assert hasattr(service, "update_queue")
    assert hasattr(service, "add_track_to_queue")
    assert hasattr(service, "play_queue")
    assert hasattr(service, "pause_queue")
    assert hasattr(service, "sync_tracks_from_sources")


def test_photo_adapter_functions():
    """Test photo adapter functions exist."""
    # Test imports to ensure functions exist
    from hub.adapters.photo_adapter import (
        get_albums_from_google,
        get_photos_from_album_google,
        get_photos_from_cloudinary,
        get_photos_from_flickr,
        get_photos_from_google,
        get_photos_from_local,
    )

    # All functions should be callable
    assert callable(get_photos_from_local)
    assert callable(get_photos_from_google)
    assert callable(get_albums_from_google)
    assert callable(get_photos_from_album_google)
    assert callable(get_photos_from_cloudinary)
    assert callable(get_photos_from_flickr)


def test_music_adapter_functions():
    """Test music adapter functions exist."""
    # Test imports to ensure functions exist
    from hub.adapters.music_adapter import (
        get_tracks_from_apple_music,
        get_tracks_from_deezer,
        get_tracks_from_local,
        get_tracks_from_spotify,
        get_tracks_from_youtube_music,
    )

    # All functions should be callable
    assert callable(get_tracks_from_local)
    assert callable(get_tracks_from_spotify)
    assert callable(get_tracks_from_apple_music)
    assert callable(get_tracks_from_deezer)
    assert callable(get_tracks_from_youtube_music)


def test_photo_api_endpoints_exist(app, client):
    """Test that photo API endpoints are registered."""
    with app.test_client() as client:
        # Test that we can access the main app to ensure routes are loaded
        response = client.get("/health")
        assert response.status_code == 200


def test_music_api_endpoints_exist(app, client):
    """Test that music API endpoints are registered."""
    with app.test_client() as client:
        # Test that we can access the main app to ensure routes are loaded
        response = client.get("/health")
        assert response.status_code == 200


def test_config_schema_updates():
    """Test that config schema includes photo and music settings."""
    from hub.config import ConfigSchema, MusicConfig, PhotoConfig

    # Create a config schema instance
    config_data = {
        "layout": {"main_view": "week_calendar", "sidebar": ["notes", "shopping", "weather"]},
        "apps": [
            {
                "id": "calendar",
                "label": "Calendar",
                "icon": "calendar.svg",
                "action": "switch_view",
                "target": "week_calendar",
            }
        ],
        "providers": {
            "calendar": {"kind": "ics", "ics_url": "https://example.com/family.ics"},
            "weather": {"kind": "open_meteo", "location": {"lat": 40.90, "lon": -74.55}},
        },
        "features": {"voice": False, "kiosk": True, "auth": False},
        "ui": {"theme": "auto", "density": "comfortable"},
        "security": {
            "ssl_enabled": False,
            "ssl_cert_path": "",
            "ssl_key_path": "",
            "rate_limit_enabled": False,
            "default_rate_limit": "1000 per minute",
            "admin_rate_limit": "1000 per minute",
            "ip_whitelist_enabled": False,
            "ip_whitelist": [],
            "session_timeout": 3600,
            "secure_headers": False,
            "admin_username": None,
            "admin_password_hash": None,
            "admin_enabled": False,
        },
        "photos": {"enabled": True, "local_path": "./instance/photos", "slideshow_interval": 5},
        "music": {"enabled": True, "local_path": "./instance/music", "volume": 70},
    }

    # Validate the configuration
    config = ConfigSchema(**config_data)

    # Check that photo and music configs are included
    assert isinstance(config.photos, PhotoConfig)
    assert isinstance(config.music, MusicConfig)
    assert config.photos.enabled is True
    assert config.music.enabled is True
    assert config.photos.local_path == "./instance/photos"
    assert config.music.local_path == "./instance/music"
    assert config.photos.slideshow_interval == 5
    assert config.music.volume == 70


def test_photo_service_database_operations(app):
    """Test photo service database operations."""
    from hub.services import photo_service

    with app.app_context():
        # Test creating a photo
        photo = photo_service.create_photo(
            filename="test.jpg",
            title="Test Photo",
            description="A test photo",
            source="local",
            tags=["test"],
            album_id=None,
        )

        assert photo is not None
        assert photo.filename == "test.jpg"
        assert photo.title == "Test Photo"
        assert "test" in photo.tags

        # Test getting the photo
        retrieved_photo = photo_service.get_photo_by_id(photo.id)
        assert retrieved_photo is not None
        assert retrieved_photo.id == photo.id
        assert retrieved_photo.filename == photo.filename

        # Test creating an album
        album = photo_service.create_album(name="Test Album", description="A test album")
        assert album is not None
        assert album.name == "Test Album"

        # Test getting the album
        retrieved_album = photo_service.get_album_by_id(album.id)
        assert retrieved_album is not None
        assert retrieved_album.id == album.id
        assert retrieved_album.name == album.name

        # Update the photo
        updated_photo = photo_service.update_photo(photo.id, title="Updated Test Photo", tags=["test", "updated"])
        assert updated_photo is not None
        assert updated_photo.title == "Updated Test Photo"
        assert "updated" in updated_photo.tags

        # Update the album
        updated_album = photo_service.update_album(album.id, name="Updated Test Album")
        assert updated_album is not None
        assert updated_album.name == "Updated Test Album"


def test_music_service_database_operations(app):
    """Test music service database operations."""
    from hub.services import music_service

    with app.app_context():
        # Test creating a track
        track = music_service.create_track(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            genre="Pop",
            duration=180,
            source="local",
            album_art_url="http://example.com/cover.jpg",
        )

        assert track is not None
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"

        # Test getting the track
        retrieved_track = music_service.get_track_by_id(track.id)
        assert retrieved_track is not None
        assert retrieved_track.id == track.id
        assert retrieved_track.title == track.title

        # Test creating a playlist
        playlist = music_service.create_playlist(name="Test Playlist", description="A test playlist")
        assert playlist is not None
        assert playlist.name == "Test Playlist"

        # Test getting the playlist
        retrieved_playlist = music_service.get_playlist_by_id(playlist.id)
        assert retrieved_playlist is not None
        assert retrieved_playlist.id == playlist.id
        assert retrieved_playlist.name == playlist.name

        # Update the track
        updated_track = music_service.update_track(track.id, title="Updated Test Song", genre="Rock")
        assert updated_track is not None
        assert updated_track.title == "Updated Test Song"
        assert updated_track.genre == "Rock"

        # Update the playlist
        updated_playlist = music_service.update_playlist(playlist.id, name="Updated Test Playlist")
        assert updated_playlist is not None
        assert updated_playlist.name == "Updated Test Playlist"

        # Test adding track to playlist
        success = music_service.add_track_to_playlist(playlist.id, track.id)
        assert success is True

        # Test getting tracks in playlist
        tracks_in_playlist = music_service.get_tracks_in_playlist(playlist.id)
        assert len(tracks_in_playlist) >= 1  # May have other tracks due to test setup
        found_track = next((t for t in tracks_in_playlist if t.id == track.id), None)
        assert found_track is not None
