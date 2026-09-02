"""Service for managing music streaming and queue management"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Union

from flask import current_app

from hub.adapters.music_adapter import get_tracks_from_local, get_tracks_from_spotify
from hub.db import get_db
from hub.integrations import spotify_auth
from hub.models import MusicQueue, MusicTrack, Playlist


def _parse_datetime(dt_value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse datetime value from database, handling both string and datetime objects.

    Args:
        dt_value: Datetime value from database (string, datetime object, or None)

    Returns:
        Parsed datetime object or None
    """
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return dt_value

    if isinstance(dt_value, str):
        try:
            return datetime.fromisoformat(dt_value)
        except (ValueError, TypeError):
            # If parsing fails, return None
            return None

    return None


def _coerce_mapping(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


class MusicService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_tracks(
        self, limit: int = 50, offset: int = 0, playlist_id: Optional[int] = None, genre: Optional[str] = None
    ) -> List[MusicTrack]:
        """Get music tracks with optional filtering"""
        try:
            db = get_db()

            # Build query based on filters
            base_query = """
                SELECT id, title, artist, album, genre, duration, source, album_art_url, created_at, updated_at
                FROM music_tracks
                WHERE 1=1
            """
            params = []

            if playlist_id is not None:
                # Get track IDs from playlist
                playlist_tracks_query = """
                    SELECT track_id FROM playlist_tracks WHERE playlist_id = ?
                """
                playlist_track_rows = db.execute(playlist_tracks_query, (playlist_id,)).fetchall()
                if playlist_track_rows:
                    track_ids = [row[0] for row in playlist_track_rows]
                    if track_ids:
                        placeholders = ",".join("?" * len(track_ids))
                        base_query += f" AND id IN ({placeholders})"
                        params.extend(track_ids)
                    else:
                        # If playlist is empty, return empty list
                        return []

            if genre is not None:
                base_query += " AND genre = ?"
                params.append(genre)

            query = base_query + " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = db.execute(query, params).fetchall()

            tracks = []
            for row in rows:
                track = MusicTrack(
                    id=row["id"],
                    title=row["title"],
                    artist=row["artist"],
                    album=row["album"],
                    genre=row["genre"],
                    duration=row["duration"],
                    source=row["source"],
                    album_art_url=row["album_art_url"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                tracks.append(track)

            return tracks
        except Exception as e:
            self.logger.error(f"Error fetching tracks: {e}")
            return []

    def get_track_by_id(self, track_id: int) -> Optional[MusicTrack]:
        """Get a specific track by ID"""
        try:
            db = get_db()

            query = """
                SELECT id, title, artist, album, genre, duration, source, album_art_url, created_at, updated_at
                FROM music_tracks
                WHERE id = ?
            """

            row = db.execute(query, (track_id,)).fetchone()
            if not row:
                return None

            track = MusicTrack(
                id=row["id"],
                title=row["title"],
                artist=row["artist"],
                album=row["album"],
                genre=row["genre"],
                duration=row["duration"],
                source=row["source"],
                album_art_url=row["album_art_url"],
                created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            )

            return track
        except Exception as e:
            self.logger.error(f"Error fetching track {track_id}: {e}")
            return None

    def create_track(
        self,
        title: str,
        artist: str,
        album: str,
        genre: Optional[str] = None,
        duration: Optional[int] = None,
        source: str = "local",
        album_art_url: Optional[str] = None,
    ) -> Optional[MusicTrack]:
        """Create a new music track"""
        try:
            db = get_db()

            query = """
                INSERT INTO music_tracks (title, artist, album, genre, duration, source, album_art_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            result = db.execute(query, (title, artist, album, genre, duration, source, album_art_url))
            db.commit()

            # Return the created track
            return self.get_track_by_id(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating track: {e}")
            return None

    def update_track(
        self,
        track_id: int,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        duration: Optional[int] = None,
        album_art_url: Optional[str] = None,
    ) -> Optional[MusicTrack]:
        """Update an existing track"""
        try:
            db = get_db()

            # Prepare update query and parameters
            update_fields = []
            params = []

            if title is not None:
                update_fields.append("title = ?")
                params.append(title)

            if artist is not None:
                update_fields.append("artist = ?")
                params.append(artist)

            if album is not None:
                update_fields.append("album = ?")
                params.append(album)

            if genre is not None:
                update_fields.append("genre = ?")
                params.append(genre)

            if duration is not None:
                update_fields.append("duration = ?")
                params.append(duration)

            if album_art_url is not None:
                update_fields.append("album_art_url = ?")
                params.append(album_art_url)

            if not update_fields:
                return self.get_track_by_id(track_id)

            query = f"UPDATE music_tracks SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608
            params.append(track_id)

            db.execute(query, params)
            db.commit()

            return self.get_track_by_id(track_id)
        except Exception as e:
            self.logger.error(f"Error updating track {track_id}: {e}")
            return None

    def delete_track(self, track_id: int) -> bool:
        """Delete a track by ID"""
        try:
            db = get_db()

            # Remove from any playlists first
            remove_from_playlist_query = "DELETE FROM playlist_tracks WHERE track_id = ?"
            db.execute(remove_from_playlist_query, (track_id,))

            # Then delete the track
            query = "DELETE FROM music_tracks WHERE id = ?"
            result = db.execute(query, (track_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting track {track_id}: {e}")
            return False

    def get_playlists(self) -> List[Playlist]:
        """Get all playlists"""
        try:
            db = get_db()

            query = """
                SELECT id, name, description, created_at, updated_at
                FROM playlists
                ORDER BY created_at DESC
            """

            rows = db.execute(query).fetchall()

            playlists = []
            for row in rows:
                playlist = Playlist(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )

                # Get track count for the playlist
                count_query = "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?"
                count_row = db.execute(count_query, (playlist.id,)).fetchone()
                playlist.track_count = count_row[0] if count_row else 0

                playlists.append(playlist)

            return playlists
        except Exception as e:
            self.logger.error(f"Error fetching playlists: {e}")
            return []

    def get_playlist_by_id(self, playlist_id: int) -> Optional[Playlist]:
        """Get a specific playlist by ID"""
        try:
            db = get_db()

            query = """
                SELECT id, name, description, created_at, updated_at
                FROM playlists
                WHERE id = ?
            """

            row = db.execute(query, (playlist_id,)).fetchone()
            if not row:
                return None

            playlist = Playlist(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            )

            # Get track count for the playlist
            count_query = "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?"
            count_row = db.execute(count_query, (playlist.id,)).fetchone()
            playlist.track_count = count_row[0] if count_row else 0

            return playlist
        except Exception as e:
            self.logger.error(f"Error fetching playlist {playlist_id}: {e}")
            return None

    def create_playlist(self, name: str, description: str = "") -> Optional[Playlist]:
        """Create a new playlist"""
        try:
            db = get_db()

            query = "INSERT INTO playlists (name, description) VALUES (?, ?)"
            result = db.execute(query, (name, description))
            db.commit()

            # Return the created playlist
            return self.get_playlist_by_id(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating playlist: {e}")
            return None

    def update_playlist(
        self, playlist_id: int, name: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[Playlist]:
        """Update an existing playlist"""
        try:
            db = get_db()

            update_fields = []
            params = []

            if name is not None:
                update_fields.append("name = ?")
                params.append(name)

            if description is not None:
                update_fields.append("description = ?")
                params.append(description)

            if not update_fields:
                return self.get_playlist_by_id(playlist_id)

            query = f"UPDATE playlists SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608
            params.append(playlist_id)

            db.execute(query, params)
            db.commit()

            return self.get_playlist_by_id(playlist_id)
        except Exception as e:
            self.logger.error(f"Error updating playlist {playlist_id}: {e}")
            return None

    def delete_playlist(self, playlist_id: int) -> bool:
        """Delete a playlist by ID"""
        try:
            db = get_db()

            # First delete all playlist-track associations
            delete_associations_query = "DELETE FROM playlist_tracks WHERE playlist_id = ?"
            db.execute(delete_associations_query, (playlist_id,))

            # Then delete the playlist
            query = "DELETE FROM playlists WHERE id = ?"
            result = db.execute(query, (playlist_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting playlist {playlist_id}: {e}")
            return False

    def add_track_to_playlist(self, playlist_id: int, track_id: int) -> bool:
        """Add a track to a playlist"""
        try:
            db = get_db()

            # Check if track exists
            track = self.get_track_by_id(track_id)
            if not track:
                return False

            # Check if playlist exists
            playlist = self.get_playlist_by_id(playlist_id)
            if not playlist:
                return False

            # Check if track is already in playlist
            check_query = "SELECT 1 FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?"
            existing = db.execute(check_query, (playlist_id, track_id)).fetchone()
            if existing:
                return True  # Track already in playlist

            # Add track to playlist
            query = "INSERT INTO playlist_tracks (playlist_id, track_id) VALUES (?, ?)"
            db.execute(query, (playlist_id, track_id))
            db.commit()

            return True
        except Exception as e:
            self.logger.error(f"Error adding track {track_id} to playlist {playlist_id}: {e}")
            return False

    def remove_track_from_playlist(self, playlist_id: int, track_id: int) -> bool:
        """Remove a track from a playlist"""
        try:
            db = get_db()

            query = "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?"
            result = db.execute(query, (playlist_id, track_id))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error removing track {track_id} from playlist {playlist_id}: {e}")
            return False

    def get_tracks_in_playlist(self, playlist_id: int) -> List[MusicTrack]:
        """Get all tracks in a playlist"""
        try:
            db = get_db()

            # Get track IDs from playlist
            query = """
                SELECT mt.id, mt.title, mt.artist, mt.album, mt.genre, mt.duration,
                       mt.source, mt.album_art_url, mt.created_at, mt.updated_at
                FROM music_tracks mt
                JOIN playlist_tracks pt ON mt.id = pt.track_id
                WHERE pt.playlist_id = ?
                ORDER BY pt.id  -- This maintains the order they were added
            """

            rows = db.execute(query, (playlist_id,)).fetchall()

            tracks = []
            for row in rows:
                track = MusicTrack(
                    id=row["id"],
                    title=row["title"],
                    artist=row["artist"],
                    album=row["album"],
                    genre=row["genre"],
                    duration=row["duration"],
                    source=row["source"],
                    album_art_url=row["album_art_url"],
                    created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                    updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
                )
                tracks.append(track)

            return tracks
        except Exception as e:
            self.logger.error(f"Error fetching tracks in playlist {playlist_id}: {e}")
            return []

    def create_queue(self, playlist_id: Optional[int] = None) -> Optional[MusicQueue]:
        """Create a new music queue"""
        try:
            db = get_db()

            query = "INSERT INTO music_queues (playlist_id) VALUES (?)"
            result = db.execute(query, (playlist_id,))
            db.commit()

            # Return the created queue
            return self.get_queue_by_id(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating queue: {e}")
            return None

    def get_queue_by_id(self, queue_id: int) -> Optional[MusicQueue]:
        """Get a music queue by ID"""
        try:
            db = get_db()

            query = """
                SELECT id, playlist_id, queue_items, current_item_index, is_playing, volume, created_at, updated_at
                FROM music_queues
                WHERE id = ?
            """

            row = db.execute(query, (queue_id,)).fetchone()
            if not row:
                return None

            # Parse queue items from JSON string
            import json

            queue_items = []
            if row["queue_items"]:
                try:
                    queue_items = json.loads(row["queue_items"])
                except Exception:
                    queue_items = []

            queue = MusicQueue(
                id=row["id"],
                playlist_id=row["playlist_id"],
                queue_items=queue_items,
                current_item_index=row["current_item_index"],
                is_playing=bool(row["is_playing"]),
                volume=row["volume"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

            return queue
        except Exception as e:
            self.logger.error(f"Error fetching queue {queue_id}: {e}")
            return None

    def get_queue_by_playlist_id(self, playlist_id: int) -> Optional[MusicQueue]:
        """Get a music queue by playlist ID"""
        try:
            db = get_db()

            query = """
                SELECT id, playlist_id, queue_items, current_item_index, is_playing, volume, created_at, updated_at
                FROM music_queues
                WHERE playlist_id = ?
            """

            row = db.execute(query, (playlist_id,)).fetchone()
            if not row:
                return None

            # Parse queue items from JSON string
            import json

            queue_items = []
            if row["queue_items"]:
                try:
                    queue_items = json.loads(row["queue_items"])
                except Exception:
                    queue_items = []

            queue = MusicQueue(
                id=row["id"],
                playlist_id=row["playlist_id"],
                queue_items=queue_items,
                current_item_index=row["current_item_index"],
                is_playing=bool(row["is_playing"]),
                volume=row["volume"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

            return queue
        except Exception as e:
            self.logger.error(f"Error fetching queue for playlist {playlist_id}: {e}")
            return None

    def update_queue(
        self,
        queue_id: int,
        queue_items: Optional[List[dict]] = None,
        current_item_index: Optional[int] = None,
        is_playing: Optional[bool] = None,
        volume: Optional[int] = None,
    ) -> Optional[MusicQueue]:
        """Update a music queue"""
        try:
            db = get_db()

            # Prepare update query and parameters
            update_fields = []
            params = []

            if queue_items is not None:
                import json

                update_fields.append("queue_items = ?")
                params.append(json.dumps(queue_items))

            if current_item_index is not None:
                update_fields.append("current_item_index = ?")
                params.append(current_item_index)

            if is_playing is not None:
                update_fields.append("is_playing = ?")
                params.append(int(is_playing))

            if volume is not None:
                update_fields.append("volume = ?")
                params.append(volume)

            if not update_fields:
                return self.get_queue_by_id(queue_id)

            query = f"UPDATE music_queues SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608
            params.append(queue_id)

            db.execute(query, params)
            db.commit()

            return self.get_queue_by_id(queue_id)
        except Exception as e:
            self.logger.error(f"Error updating queue {queue_id}: {e}")
            return None

    def add_track_to_queue(self, queue_id: int, track_id: int) -> bool:
        """Add a track to a queue"""
        try:
            queue = self.get_queue_by_id(queue_id)
            if not queue:
                return False

            # Get the track
            track = self.get_track_by_id(track_id)
            if not track:
                return False

            # Add to queue items
            new_queue_items = queue.queue_items if queue.queue_items else []
            new_queue_items.append(
                {"id": track.id, "title": track.title, "artist": track.artist, "duration": track.duration}
            )

            return bool(self.update_queue(queue_id, queue_items=new_queue_items))
        except Exception as e:
            self.logger.error(f"Error adding track {track_id} to queue {queue_id}: {e}")
            return False

    def play_queue(self, queue_id: int) -> bool:
        """Set queue to playing state"""
        try:
            queue = self.get_queue_by_id(queue_id)
            if not queue:
                return False

            return bool(self.update_queue(queue_id, is_playing=True))
        except Exception as e:
            self.logger.error(f"Error playing queue {queue_id}: {e}")
            return False

    def pause_queue(self, queue_id: int) -> bool:
        """Set queue to paused state"""
        try:
            queue = self.get_queue_by_id(queue_id)
            if not queue:
                return False

            return bool(self.update_queue(queue_id, is_playing=False))
        except Exception as e:
            self.logger.error(f"Error pausing queue {queue_id}: {e}")
            return False

    def sync_tracks_from_sources(self) -> bool:
        """Sync music tracks from all configured sources (local, Spotify, etc.)"""
        try:
            config = current_app.config.get("CONFIG")
            if not config:
                return False

            # Get music sync configuration
            music_config = _coerce_mapping(getattr(config, "music", {}))
            local_music_path = music_config.get("local_path", os.path.join(current_app.instance_path, "music"))
            spotify_config = _coerce_mapping(music_config.get("spotify"))
            spotify_enabled = bool(spotify_config.get("enabled", False))
            spotify_track_sync_enabled = bool(spotify_config.get("sync_saved_tracks", False))

            # Sync from local source
            if os.path.exists(local_music_path):
                local_tracks = get_tracks_from_local(local_music_path)
                for track_info in local_tracks:
                    # Check if track already exists (by title and artist)
                    existing_track = self.get_track_by_title_and_artist(track_info["title"], track_info["artist"])
                    if not existing_track:
                        self.create_track(
                            title=track_info["title"],
                            artist=track_info["artist"],
                            album=track_info.get("album", ""),
                            genre=track_info.get("genre"),
                            duration=track_info.get("duration"),
                            source="local",
                            album_art_url=track_info.get("album_art_url"),
                        )

            # Sync from Spotify if enabled
            if spotify_enabled:
                if spotify_track_sync_enabled:
                    access_token = spotify_auth.get_valid_access_token(spotify_config)

                    if access_token:
                        spotify_tracks = get_tracks_from_spotify(access_token)
                        for track_info in spotify_tracks:
                            existing_track = self.get_track_by_title_and_artist(
                                track_info["title"], track_info["artist"]
                            )
                            if not existing_track:
                                self.create_track(
                                    title=track_info["title"],
                                    artist=track_info["artist"],
                                    album=track_info.get("album", ""),
                                    genre=track_info.get("genre"),
                                    duration=track_info.get("duration"),
                                    source="spotify",
                                    album_art_url=track_info.get("album_art_url"),
                                )
                    else:
                        self.logger.info(
                            "Spotify is enabled but not connected. Skip syncing Spotify tracks until OAuth completes."
                        )
                else:
                    self.logger.info(
                        "Spotify track sync is disabled (sync_saved_tracks=false); skipping saved/playlist track import."
                    )

            return True
        except Exception as e:
            self.logger.error(f"Error syncing tracks: {e}")
            return False

    def get_track_by_title_and_artist(self, title: str, artist: str) -> Optional[MusicTrack]:
        """Get a track by title and artist"""
        try:
            db = get_db()

            query = """
                SELECT id, title, artist, album, genre, duration, source, album_art_url, created_at, updated_at
                FROM music_tracks
                WHERE title = ? AND artist = ?
            """

            row = db.execute(query, (title, artist)).fetchone()
            if not row:
                return None

            track = MusicTrack(
                id=row["id"],
                title=row["title"],
                artist=row["artist"],
                album=row["album"],
                genre=row["genre"],
                duration=row["duration"],
                source=row["source"],
                album_art_url=row["album_art_url"],
                created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            )

            return track
        except Exception as e:
            self.logger.error(f"Error fetching track by title {title} and artist {artist}: {e}")
            return None

    def get_recent_tracks(self, limit: int = 10) -> List[MusicTrack]:
        """Get recently added tracks"""
        try:
            db = get_db()

            query = """
                SELECT id, title, artist, album, genre, duration, source, album_art_url, created_at, updated_at
                FROM music_tracks
                ORDER BY created_at DESC
                LIMIT ?
            """

            rows = db.execute(query, (limit,)).fetchall()

            tracks = []
            for row in rows:
                track = MusicTrack(
                    id=row["id"],
                    title=row["title"],
                    artist=row["artist"],
                    album=row["album"],
                    genre=row["genre"],
                    duration=row["duration"],
                    source=row["source"],
                    album_art_url=row["album_art_url"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                tracks.append(track)

            return tracks
        except Exception as e:
            self.logger.error(f"Error fetching recent tracks: {e}")
            return []


class MusicPlaybackController:
    """Handles the state and control of music playback."""

    def __init__(self):
        self.current_queue = None
        self.current_track_index = 0
        self.is_playing = False
        self.current_time = 0  # in seconds
        self.volume = 70  # 0-100
        self._liked_tracks = set()  # Set of track IDs that are liked

    def load_queue(self, queue_id: int = None, playlist_id: int = None) -> bool:
        """Load a queue or create one from a playlist."""
        from . import music_service

        if queue_id:
            self.current_queue = music_service.get_queue_by_id(queue_id)
        elif playlist_id:
            # Create/load queue for this playlist
            existing_queue = music_service.get_queue_by_playlist_id(playlist_id)
            if existing_queue:
                self.current_queue = existing_queue
            else:
                # Create a new queue from the playlist
                playlist_tracks = music_service.get_tracks_in_playlist(playlist_id)
                if not playlist_tracks:
                    return False

                # Create new queue
                new_queue = music_service.create_queue(playlist_id)
                if not new_queue:
                    return False

                # Add tracks to queue
                for track in playlist_tracks:
                    music_service.add_track_to_queue(new_queue.id, track.id)

                self.current_queue = music_service.get_queue_by_id(new_queue.id)

        if self.current_queue:
            self.current_track_index = 0
            return True
        return False

    def get_current_track(self):
        """Get the currently playing track."""
        if not self.current_queue or not self.current_queue.queue_items:
            return None

        if 0 <= self.current_track_index < len(self.current_queue.queue_items):
            track_id = self.current_queue.queue_items[self.current_track_index]["id"]
            from . import music_service

            return music_service.get_track_by_id(track_id)
        return None

    def play(self) -> bool:
        """Start playback."""
        if self.current_queue:
            self.is_playing = True
            return True
        return False

    def pause(self) -> bool:
        """Pause playback."""
        self.is_playing = False
        return True

    def next_track(self):
        """Skip to the next track."""
        if not self.current_queue or not self.current_queue.queue_items:
            return None

        self.current_track_index = (self.current_track_index + 1) % len(self.current_queue.queue_items)
        return self.get_current_track()

    def previous_track(self):
        """Go back to the previous track."""
        if not self.current_queue or not self.current_queue.queue_items:
            return None

        self.current_track_index = (self.current_track_index - 1) % len(self.current_queue.queue_items)
        return self.get_current_track()

    def seek_to(self, time_seconds: int):
        """Seek to a specific time in the current track."""
        self.current_time = max(0, time_seconds)
        return self.current_time

    def toggle_like_track(self, track_id: int) -> bool:
        """Toggle the like status of a track."""
        if track_id in self._liked_tracks:
            self._liked_tracks.remove(track_id)
            return False
        else:
            self._liked_tracks.add(track_id)
            return True

    def is_track_liked(self, track_id: int) -> bool:
        """Check if a track is liked."""
        return track_id in self._liked_tracks

    def get_playback_state(self):
        """Get the current playback state."""
        current_track = self.get_current_track()
        if not current_track:
            return {
                "track": None,
                "is_playing": self.is_playing,
                "current_time": self.current_time,
                "duration": 0,
                "volume": self.volume,
            }

        track_dict = current_track.to_dict()
        return {
            "track": track_dict,
            "is_playing": self.is_playing,
            "current_time": self.current_time,
            "duration": track_dict.get("duration", 0),
            "volume": self.volume,
            "is_liked": self.is_track_liked(track_dict["id"]),
        }


# Global instances
music_service = MusicService()
music_controller = MusicPlaybackController()
