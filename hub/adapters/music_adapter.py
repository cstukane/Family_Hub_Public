"""Music adapters for different music sources"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from hub.utils.http import RateLimitError, rate_limited_get

logger = logging.getLogger(__name__)
_SPOTIFY_LOG_SUPPRESSION_SECONDS = 120
_LAST_SPOTIFY_LOG_AT: Dict[str, float] = {}


def _log_spotify_warning(key: str, message: str, *args) -> None:
    now = time.monotonic()
    last = _LAST_SPOTIFY_LOG_AT.get(key, 0.0)
    if now - last < _SPOTIFY_LOG_SUPPRESSION_SECONDS:
        return
    _LAST_SPOTIFY_LOG_AT[key] = now
    logger.warning(message, *args)


# Try to import mutagen, but gracefully handle if it's not available
try:
    from mutagen import File as MutagenFile

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    MutagenFile = None


def get_tracks_from_local(music_path: str) -> List[Dict[str, Any]]:
    """
    Get music tracks from local directory.

    Args:
        music_path: Path to the directory containing music files

    Returns:
        List of track information dictionaries
    """

    # Define supported music extensions
    supported_extensions = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}

    tracks = []

    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(music_path):
        for file in files:
            # Get file extension
            _, ext = os.path.splitext(file.lower())

            # Check if it's a supported music format
            if ext in supported_extensions:
                file_path = os.path.join(root, file)

                # If mutagen is not available, create basic track info without metadata
                if not MUTAGEN_AVAILABLE:
                    track_info = {
                        "title": os.path.splitext(file)[0],  # Use filename without extension
                        "artist": "Unknown Artist",
                        "album": "Unknown Album",
                        "genre": None,
                        "duration": 0,
                        "source": "local",
                        "album_art_url": None,
                        "file_path": os.path.relpath(file_path, music_path),
                    }
                    tracks.append(track_info)
                    continue

                try:
                    # Try to read metadata from the file
                    audio_file = MutagenFile(file_path)

                    # Initialize with default values
                    title = os.path.splitext(file)[0]  # Use filename without extension as default
                    artist = "Unknown Artist"
                    album = "Unknown Album"
                    genre = None
                    duration = 0

                    if audio_file is not None:
                        # Extract common metadata fields
                        if hasattr(audio_file, "tags") and audio_file.tags:
                            # Attempt to get title
                            for tag_name in ["TIT2", "Title", "??nam", "title"]:
                                if tag_name in audio_file.tags:
                                    title = str(audio_file.tags[tag_name])
                                    break

                            # Attempt to get artist
                            for tag_name in ["TPE1", "Artist", "??ART", "artist"]:
                                if tag_name in audio_file.tags:
                                    artist = str(audio_file.tags[tag_name])
                                    break

                            # Attempt to get album
                            for tag_name in ["TALB", "Album", "??alb", "album"]:
                                if tag_name in audio_file.tags:
                                    album = str(audio_file.tags[tag_name])
                                    break

                            # Attempt to get genre
                            for tag_name in ["TCON", "Genre", "??gen", "genre"]:
                                if tag_name in audio_file.tags:
                                    genre = str(audio_file.tags[tag_name])
                                    break

                    # Get duration in seconds
                    if hasattr(audio_file, "info") and audio_file.info:
                        duration = int(audio_file.info.length) if audio_file.info.length else 0

                    track_info = {
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "genre": genre,
                        "duration": duration,
                        "source": "local",
                        "album_art_url": None,  # Will be populated if found in metadata
                        "file_path": os.path.relpath(file_path, music_path),  # Store relative path
                    }

                    tracks.append(track_info)
                except Exception as e:
                    print(f"Error processing music file {file_path}: {e}")
                    # Add a minimal entry for files that can't be read properly
                    track_info = {
                        "title": os.path.splitext(file)[0],
                        "artist": "Unknown Artist",
                        "album": "Unknown Album",
                        "genre": None,
                        "duration": 0,
                        "source": "local",
                        "album_art_url": None,
                        "file_path": os.path.relpath(file_path, music_path),
                    }
                    tracks.append(track_info)

    return tracks


def get_tracks_from_spotify(access_token: str) -> List[Dict[str, Any]]:
    """
    Get tracks from Spotify playlist or user library using an access token issued
    via the Authorization Code Flow with PKCE.

    Args:
        access_token: Spotify API access token

    Returns:
        List of track information dictionaries
    """

    try:
        from hub.integrations import spotify_auth

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        # Get user's saved tracks (liked tracks)
        saved_tracks_url = "https://api.spotify.com/v1/me/tracks"
        params = {"limit": 50}

        all_tracks = []

        def _spotify_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
            nonlocal access_token
            try:
                response = rate_limited_get(url, headers=headers, params=params, service_name="spotify")
            except RateLimitError as exc:
                _log_spotify_warning(
                    "spotify_rate_limited",
                    "Spotify rate limited during sync: %s",
                    exc,
                )
                return None

            if response.status_code == 401:
                refreshed = spotify_auth.refresh_access_token()
                if not refreshed or not refreshed.get("access_token"):
                    _log_spotify_warning(
                        "spotify_auth_expired",
                        "Spotify access token expired; reconnect to resume sync.",
                    )
                    return None
                access_token = refreshed["access_token"]
                headers["Authorization"] = f"Bearer {access_token}"
                try:
                    response = rate_limited_get(url, headers=headers, params=params, service_name="spotify")
                except RateLimitError as exc:
                    _log_spotify_warning(
                        "spotify_rate_limited",
                        "Spotify rate limited during sync: %s",
                        exc,
                    )
                    return None

            return response

        # Paginate through saved tracks
        while True:
            response = _spotify_get(saved_tracks_url, params=params)
            if not response:
                return []
            if response.status_code != 200:
                _log_spotify_warning(
                    "spotify_saved_tracks_failed",
                    "Failed to fetch saved tracks from Spotify: %s",
                    response.text,
                )
                break

            data = response.json()
            for item in data.get("items", []):
                track = item.get("track", {})
                album = track.get("album", {})

                # Get album art (preferably large or medium size)
                album_art_url = None
                images = album.get("images", [])
                if images:
                    best_image = None
                    for img in images:
                        if not best_image or img.get("height", 0) > best_image.get("height", 0):
                            best_image = img
                    if best_image:
                        album_art_url = best_image.get("url")

                track_info = {
                    "title": track.get("name", "Unknown Title"),
                    "artist": ", ".join([artist["name"] for artist in track.get("artists", [])]),
                    "album": album.get("name", "Unknown Album"),
                    "genre": album.get("genres", [None])[0] if album.get("genres") else None,
                    "duration": (
                        int(track.get("duration_ms", 0) / 1000) if track.get("duration_ms") else 0
                    ),  # Convert ms to seconds
                    "source": "spotify",
                    "album_art_url": album_art_url,
                    "spotify_id": track.get("id"),
                }

                all_tracks.append(track_info)

            # Check if there are more pages
            if not data.get("next"):
                break

            # Make the next request with the URL provided by the API
            response = _spotify_get(data["next"])
            if not response:
                return []
            if response.status_code != 200:
                _log_spotify_warning(
                    "spotify_saved_tracks_page_failed",
                    "Failed to fetch next page of saved tracks: %s",
                    response.text,
                )
                break

            data = response.json()

        # Also get user's playlists and the tracks in them
        playlists_url = "https://api.spotify.com/v1/me/playlists"
        playlists_params = {"limit": 50}

        playlist_response = _spotify_get(playlists_url, params=playlists_params)
        if not playlist_response:
            return all_tracks
        if playlist_response.status_code != 200:
            _log_spotify_warning(
                "spotify_playlists_failed",
                "Failed to fetch user playlists from Spotify: %s",
                playlist_response.text,
            )
        else:
            playlists_data = playlist_response.json()
            for playlist in playlists_data.get("items", []):
                playlist_id = playlist.get("id")
                playlist_name = playlist.get("name")

                # Get tracks from this playlist
                playlist_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                playlist_params = {"limit": 100}

                playlist_track_response = _spotify_get(playlist_tracks_url, params=playlist_params)
                if not playlist_track_response:
                    return all_tracks
                if playlist_track_response.status_code != 200:
                    _log_spotify_warning(
                        "spotify_playlist_tracks_failed",
                        "Failed to fetch tracks from playlist %s: %s",
                        playlist_name,
                        playlist_track_response.text,
                    )
                    break

                playlist_tracks_data = playlist_track_response.json()
                for item in playlist_tracks_data.get("items", []):
                    track = item.get("track", {})
                    if not track:  # Skip if no track data
                        continue

                    album = track.get("album", {})

                    # Get album art (preferably large or medium size)
                    album_art_url = None
                    images = album.get("images", [])
                    if images:
                        best_image = None
                        for img in images:
                            if not best_image or img.get("height", 0) > best_image.get("height", 0):
                                best_image = img
                        if best_image:
                            album_art_url = best_image.get("url")

                    track_info = {
                        "title": track.get("name", "Unknown Title"),
                        "artist": ", ".join([artist["name"] for artist in track.get("artists", [])]),
                        "album": album.get("name", "Unknown Album"),
                        "genre": album.get("genres", [None])[0] if album.get("genres") else None,
                        "duration": (
                            int(track.get("duration_ms", 0) / 1000) if track.get("duration_ms") else 0
                        ),  # Convert ms to seconds
                        "source": "spotify",
                        "album_art_url": album_art_url,
                        "spotify_id": track.get("id"),
                        "playlist_name": playlist_name,  # Add playlist info for context
                    }

                    # Avoid duplicates - check if already in the main list
                    if not any(t["spotify_id"] == track_info["spotify_id"] for t in all_tracks):
                        all_tracks.append(track_info)

        return all_tracks

    except RateLimitError as e:
        _log_spotify_warning("spotify_rate_limited", "Spotify rate limited during sync: %s", e)
        return []
    except Exception as e:
        _log_spotify_warning("spotify_sync_error", "Error fetching tracks from Spotify: %s", e)
        return []


def get_tracks_from_apple_music(developer_token: str, user_token: str = None) -> List[Dict[str, Any]]:
    """
    Get tracks from Apple Music.

    Args:
        developer_token: Apple Music developer token
        user_token: Apple Music user token (optional, for user-specific data)

    Returns:
        List of track information dictionaries
    """
    tracks = []

    try:
        # Note: Apple Music API implementation can be complex due to authentication
        # This is a basic implementation that might need to be expanded based on specific needs
        headers = {"Authorization": f"Bearer {developer_token}", "Content-Type": "application/json"}

        # Construct the API URL (this is just an example, actual implementation may vary)
        # Apple Music API requires storefront, which is typically 'us' for US
        url = "https://api.music.apple.com/v1/me/library/songs"

        # If user token is provided, make authenticated request
        if user_token:
            headers["Music-User-Token"] = user_token

        params = {"limit": 100}

        response = rate_limited_get(url, headers=headers, params=params, service_name="apple_music")
        if response.status_code != 200:
            print(f"Failed to fetch tracks from Apple Music: {response.text}")
            return []

        data = response.json()

        for item in data.get("data", []):
            attributes = item.get("attributes", {})

            track_info = {
                "title": attributes.get("name", "Unknown Title"),
                "artist": attributes.get("artistName", "Unknown Artist"),
                "album": attributes.get("albumName", "Unknown Album"),
                "genre": attributes.get("genreNames", [None])[0] if attributes.get("genreNames") else None,
                "duration": (
                    int(attributes.get("durationInMillis", 0) / 1000) if attributes.get("durationInMillis") else 0
                ),  # Convert ms to seconds
                "source": "apple_music",
                "album_art_url": attributes.get("artwork", {}).get("url"),  # Apple artwork URL template
                "apple_music_id": item.get("id"),
            }

            # Process artwork URL template if present
            if track_info["album_art_url"]:
                # Apple provides a URL with {w}x{h} placeholders
                artwork = attributes.get("artwork", {})
                width = artwork.get("width", 400)
                height = artwork.get("height", 400)
                track_info["album_art_url"] = (
                    track_info["album_art_url"].replace("{w}", str(width)).replace("{h}", str(height))
                )

            tracks.append(track_info)

        return tracks

    except RateLimitError as e:
        print(f"Apple Music rate limited: {e}")
        return []
    except Exception as e:
        print(f"Error fetching tracks from Apple Music: {e}")
        return []


def get_tracks_from_deezer(user_id: str) -> List[Dict[str, Any]]:
    """
    Get tracks from Deezer user library.

    Args:
        user_id: Deezer user ID

    Returns:
        List of track information dictionaries
    """

    try:
        # Deezer API - get user's favorite tracks
        user_tracks_url = f"https://api.deezer.com/user/{user_id}/tracks"

        params = {"limit": 100}

        all_tracks = []

        # Paginate through user's tracks
        while True:
            response = rate_limited_get(user_tracks_url, params=params, service_name="deezer")
            if response.status_code != 200:
                print(f"Failed to fetch tracks from Deezer: {response.text}")
                break

            data = response.json()

            for item in data.get("data", []):
                track_info = {
                    "title": item.get("title", "Unknown Title"),
                    "artist": item.get("artist", {}).get("name", "Unknown Artist"),
                    "album": item.get("album", {}).get("title", "Unknown Album"),
                    "genre": None,  # Deezer doesn't provide genre at track level directly
                    "duration": item.get("duration", 0),
                    "source": "deezer",
                    "album_art_url": item.get("album", {}).get("cover_medium"),  # Use medium quality cover
                    "deezer_id": item.get("id"),
                }

                all_tracks.append(track_info)

            # Check if there are more pages (Deezer uses next URL)
            next_url = data.get("next")
            if not next_url:
                break

            # Make the next request
            response = rate_limited_get(next_url, service_name="deezer")
            if response.status_code != 200:
                print(f"Failed to fetch next page of tracks from Deezer: {response.text}")
                break

            data = response.json()

        return all_tracks

    except RateLimitError as e:
        print(f"Deezer rate limited: {e}")
        return []
    except Exception as e:
        print(f"Error fetching tracks from Deezer: {e}")
        return []


def get_tracks_from_youtube_music(api_key: str, playlist_id: str) -> List[Dict[str, Any]]:
    """
    Get tracks from YouTube Music playlist.

    Args:
        api_key: YouTube Data API key
        playlist_id: YouTube playlist ID

    Returns:
        List of track information dictionaries
    """

    try:
        # YouTube Data API - get playlist items
        playlist_items_url = "https://www.googleapis.com/youtube/v3/playlistItems"

        params = {"part": "snippet", "playlistId": playlist_id, "key": api_key, "maxResults": 50}

        all_tracks = []

        # Paginate through playlist items
        while True:
            response = rate_limited_get(playlist_items_url, params=params, service_name="youtube")
            if response.status_code != 200:
                print(f"Failed to fetch playlist items from YouTube: {response.text}")
                break

            data = response.json()

            for item in data.get("items", []):
                snippet = item.get("snippet", {})

                track_info = {
                    "title": snippet.get("title", "Unknown Title"),
                    "artist": "YouTube Music",  # YouTube doesn't provide artist info in playlist items
                    "album": snippet.get("channelTitle", "Unknown Album"),
                    "genre": "YouTube",
                    "duration": 0,  # YouTube doesn't provide duration in playlist items
                    "source": "youtube_music",
                    "album_art_url": snippet.get("thumbnails", {}).get("medium", {}).get("url")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    "youtube_id": snippet.get("resourceId", {}).get("videoId"),
                }

                all_tracks.append(track_info)

            # Check if there are more pages
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            params["pageToken"] = next_page_token

        return all_tracks

    except RateLimitError as e:
        print(f"YouTube Music rate limited: {e}")
        return []
    except Exception as e:
        print(f"Error fetching tracks from YouTube Music: {e}")
        return []
