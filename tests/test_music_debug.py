from app import create_app
from hub.db import init_db
from hub.services.music import music_service


def test_music_debug_flow():
    app = create_app()

    with app.app_context():
        # Initialize database
        init_db()

        # Create a track
        track = music_service.create_track(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            genre="Pop",
            duration=180,
            source="local",
            album_art_url="http://example.com/cover.jpg",
        )
        print("Track created:", track)

        # Create a playlist
        playlist = music_service.create_playlist(name="Test Playlist", description="A test playlist")
        print("Playlist created:", playlist)

        # Add track to playlist
        success = music_service.add_track_to_playlist(playlist.id, track.id)
        print("Added track to playlist:", success)

        # Get tracks in playlist
        tracks_in_playlist = music_service.get_tracks_in_playlist(playlist.id)
        print("Tracks in playlist:", tracks_in_playlist)
        print("Number of tracks:", len(tracks_in_playlist))
