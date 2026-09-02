"""Service for managing photos, albums, and slideshow functionality"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Union

from flask import current_app

from hub.adapters.photo_adapter import get_photos_from_google, get_photos_from_local
from hub.db import get_db
from hub.models import Album, Photo


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


class PhotoService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_photos(
        self, limit: int = 50, offset: int = 0, album_id: Optional[int] = None, tags: Optional[List[str]] = None
    ) -> List[Photo]:
        """Get photos with optional filtering by album or tags"""
        try:
            db = get_db()

            # Build query based on filters
            base_query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE 1=1
            """
            params = []

            if album_id is not None:
                base_query += " AND album_id = ?"
                params.append(album_id)

            query = base_query + " ORDER BY date_taken DESC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = db.execute(query, params).fetchall()

            photos = []
            for row in rows:
                # Parse tags from JSON string if they exist
                tags_list = []
                if row["tags"]:
                    import json

                    try:
                        tags_list = json.loads(row["tags"])
                    except Exception:
                        tags_list = []

                photo = Photo(
                    id=row["id"],
                    filename=row["filename"],
                    title=row["title"],
                    description=row["description"],
                    date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                    source=row["source"],
                    tags=tags_list,
                    album_id=row["album_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                photos.append(photo)

            return photos
        except Exception as e:
            self.logger.error(f"Error fetching photos: {e}")
            return []

    def get_photo_by_id(self, photo_id: int) -> Optional[Photo]:
        """Get a specific photo by ID"""
        try:
            db = get_db()

            query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE id = ?
            """

            row = db.execute(query, (photo_id,)).fetchone()
            if not row:
                return None

            # Parse tags from JSON string
            tags_list = []
            if row["tags"]:
                import json

                try:
                    tags_list = json.loads(row["tags"])
                except Exception:
                    tags_list = []

            photo = Photo(
                id=row["id"],
                filename=row["filename"],
                title=row["title"],
                description=row["description"],
                date_taken=_parse_datetime(row["date_taken"]),
                source=row["source"],
                tags=tags_list,
                album_id=row["album_id"],
                created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            )

            return photo
        except Exception as e:
            self.logger.error(f"Error fetching photo {photo_id}: {e}")
            return None

    def create_photo(
        self,
        filename: str,
        title: str = "",
        description: str = "",
        date_taken: Optional[datetime] = None,
        source: str = "local",
        tags: Optional[List[str]] = None,
        album_id: Optional[int] = None,
    ) -> Optional[Photo]:
        """Create a new photo record"""
        try:
            db = get_db()

            # Convert tags to JSON string
            import json

            tags_json = json.dumps(tags or [])

            query = """
                INSERT INTO photos (filename, title, description, date_taken, source, tags, album_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            result = db.execute(
                query,
                (
                    filename,
                    title,
                    description,
                    date_taken.isoformat() if date_taken else None,
                    source,
                    tags_json,
                    album_id,
                ),
            )
            db.commit()

            # Return the created photo
            return self.get_photo_by_id(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating photo: {e}")
            return None

    def update_photo(
        self,
        photo_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        album_id: Optional[int] = None,
    ) -> Optional[Photo]:
        """Update an existing photo"""
        try:
            db = get_db()

            # Prepare update query and parameters
            update_fields = []
            params = []

            if title is not None:
                update_fields.append("title = ?")
                params.append(title)

            if description is not None:
                update_fields.append("description = ?")
                params.append(description)

            if tags is not None:
                import json

                update_fields.append("tags = ?")
                params.append(json.dumps(tags))

            if album_id is not None:
                update_fields.append("album_id = ?")
                params.append(album_id)

            if not update_fields:
                return self.get_photo_by_id(photo_id)

            query = f"UPDATE photos SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608
            params.append(photo_id)

            db.execute(query, params)
            db.commit()

            return self.get_photo_by_id(photo_id)
        except Exception as e:
            self.logger.error(f"Error updating photo {photo_id}: {e}")
            return None

    def delete_photo(self, photo_id: int) -> bool:
        """Delete a photo by ID"""
        try:
            db = get_db()

            query = "DELETE FROM photos WHERE id = ?"
            result = db.execute(query, (photo_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting photo {photo_id}: {e}")
            return False

    def get_albums(self) -> List[Album]:
        """Get all albums"""
        try:
            db = get_db()

            query = """
                SELECT id, name, description, created_at, updated_at
                FROM albums
                ORDER BY created_at DESC
            """

            rows = db.execute(query).fetchall()

            albums = []
            for row in rows:
                album = Album(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )

                # Get photo count for the album
                count_query = "SELECT COUNT(*) FROM photos WHERE album_id = ?"
                count_row = db.execute(count_query, (album.id,)).fetchone()
                album.photo_count = count_row[0] if count_row else 0

                albums.append(album)

            return albums
        except Exception as e:
            self.logger.error(f"Error fetching albums: {e}")
            return []

    def get_album_by_id(self, album_id: int) -> Optional[Album]:
        """Get a specific album by ID"""
        try:
            db = get_db()

            query = """
                SELECT id, name, description, created_at, updated_at
                FROM albums
                WHERE id = ?
            """

            row = db.execute(query, (album_id,)).fetchone()
            if not row:
                return None

            album = Album(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_at=_parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                updated_at=_parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            )

            # Get photo count for the album
            count_query = "SELECT COUNT(*) FROM photos WHERE album_id = ?"
            count_row = db.execute(count_query, (album.id,)).fetchone()
            album.photo_count = count_row[0] if count_row else 0

            return album
        except Exception as e:
            self.logger.error(f"Error fetching album {album_id}: {e}")
            return None

    def create_album(self, name: str, description: str = "") -> Optional[Album]:
        """Create a new album"""
        try:
            db = get_db()

            query = "INSERT INTO albums (name, description) VALUES (?, ?)"
            result = db.execute(query, (name, description))
            db.commit()

            # Return the created album
            return self.get_album_by_id(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating album: {e}")
            return None

    def update_album(
        self, album_id: int, name: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[Album]:
        """Update an existing album"""
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
                return self.get_album_by_id(album_id)

            query = f"UPDATE albums SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608
            params.append(album_id)

            db.execute(query, params)
            db.commit()

            return self.get_album_by_id(album_id)
        except Exception as e:
            self.logger.error(f"Error updating album {album_id}: {e}")
            return None

    def delete_album(self, album_id: int) -> bool:
        """Delete an album by ID"""
        try:
            db = get_db()

            # First delete all photos in the album
            delete_photos_query = "DELETE FROM photos WHERE album_id = ?"
            db.execute(delete_photos_query, (album_id,))

            # Then delete the album
            query = "DELETE FROM albums WHERE id = ?"
            result = db.execute(query, (album_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting album {album_id}: {e}")
            return False

    def get_photos_for_slideshow(
        self, album_id: Optional[int] = None, tags: Optional[List[str]] = None, shuffle: bool = True
    ) -> List[Photo]:
        """Get photos for slideshow with optional filters"""
        try:
            db = get_db()

            # Build query based on filters
            base_query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE 1=1
            """
            params = []

            if album_id is not None:
                base_query += " AND album_id = ?"
                params.append(album_id)

            query = base_query
            if shuffle:
                query += " ORDER BY RANDOM()"
            else:
                query += " ORDER BY date_taken DESC, created_at DESC"

            rows = db.execute(query, params).fetchall()

            photos = []
            for row in rows:
                # Parse tags from JSON string
                tags_list = []
                if row["tags"]:
                    import json

                    try:
                        tags_list = json.loads(row["tags"])
                    except Exception:
                        tags_list = []

                photo = Photo(
                    id=row["id"],
                    filename=row["filename"],
                    title=row["title"],
                    description=row["description"],
                    date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                    source=row["source"],
                    tags=tags_list,
                    album_id=row["album_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                photos.append(photo)

            return photos
        except Exception as e:
            self.logger.error(f"Error fetching slideshow photos: {e}")
            return []

    def get_photos_for_slideshow_with_pagination(
        self, album_id: Optional[int] = None, shuffle: bool = True, limit: int = 10, offset: int = 0
    ) -> List[Photo]:
        """Get photos for slideshow with pagination and filtering"""
        try:
            db = get_db()

            # Build query based on filters
            base_query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE 1=1
            """
            params = []

            if album_id is not None:
                base_query += " AND album_id = ?"
                params.append(album_id)

            # Apply ordering and pagination
            query = base_query
            if shuffle:
                query += " ORDER BY RANDOM()"
            else:
                query += " ORDER BY date_taken DESC, created_at DESC"

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = db.execute(query, params).fetchall()

            photos = []
            for row in rows:
                # Parse tags from JSON string
                tags_list = []
                if row["tags"]:
                    import json

                    try:
                        tags_list = json.loads(row["tags"])
                    except Exception:
                        tags_list = []

                photo = Photo(
                    id=row["id"],
                    filename=row["filename"],
                    title=row["title"],
                    description=row["description"],
                    date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                    source=row["source"],
                    tags=tags_list,
                    album_id=row["album_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                photos.append(photo)

            return photos
        except Exception as e:
            self.logger.error(f"Error fetching slideshow photos with pagination: {e}")
            return []

    def sync_photos_from_sources(self) -> bool:
        """Sync photos from all configured sources (local, Google Photos, etc.)"""
        try:
            config = current_app.config.get("CONFIG")
            if not config:
                return False

            # Get photo sync configuration
            photo_config = getattr(config, "photos", {})
            local_photo_path = photo_config.get("local_path", os.path.join(current_app.instance_path, "photos"))
            google_photos_enabled = photo_config.get("google_photos", {}).get("enabled", False)

            # Sync from local source
            if os.path.exists(local_photo_path):
                local_photos = get_photos_from_local(local_photo_path)
                for photo_info in local_photos:
                    # Check if photo already exists (by filename)
                    existing_photo = self.get_photo_by_filename(photo_info["filename"])
                    if not existing_photo:
                        self.create_photo(
                            filename=photo_info["filename"],
                            title=photo_info.get("title", ""),
                            description=photo_info.get("description", ""),
                            date_taken=photo_info.get("date_taken"),
                            source="local",
                            tags=photo_info.get("tags", []),
                            album_id=photo_info.get("album_id"),
                        )

            # Sync from Google Photos if enabled
            if google_photos_enabled:
                # Get Google Photos credentials from config
                google_config = photo_config.get("google_photos", {})
                client_id = google_config.get("client_id")
                client_secret = google_config.get("client_secret")
                refresh_token = google_config.get("refresh_token")

                if client_id and client_secret and refresh_token:
                    google_photos = get_photos_from_google(client_id, client_secret, refresh_token)
                    for photo_info in google_photos:
                        # Check if photo already exists (by filename/source)
                        existing_photo = self.get_photo_by_filename_and_source(photo_info["filename"], "google_photos")
                        if not existing_photo:
                            self.create_photo(
                                filename=photo_info["filename"],
                                title=photo_info.get("title", ""),
                                description=photo_info.get("description", ""),
                                date_taken=photo_info.get("date_taken"),
                                source="google_photos",
                                tags=photo_info.get("tags", []),
                                album_id=photo_info.get("album_id"),
                            )

            return True
        except Exception as e:
            self.logger.error(f"Error syncing photos: {e}")
            return False

    def get_photo_by_filename(self, filename: str) -> Optional[Photo]:
        """Get a photo by filename"""
        try:
            db = get_db()

            query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE filename = ?
            """

            row = db.execute(query, (filename,)).fetchone()
            if not row:
                return None

            # Parse tags from JSON string
            tags_list = []
            if row["tags"]:
                import json

                try:
                    tags_list = json.loads(row["tags"])
                except Exception:
                    tags_list = []

            photo = Photo(
                id=row["id"],
                filename=row["filename"],
                title=row["title"],
                description=row["description"],
                date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                source=row["source"],
                tags=tags_list,
                album_id=row["album_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

            return photo
        except Exception as e:
            self.logger.error(f"Error fetching photo by filename {filename}: {e}")
            return None

    def get_photo_by_filename_and_source(self, filename: str, source: str) -> Optional[Photo]:
        """Get a photo by filename and source"""
        try:
            db = get_db()

            query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                WHERE filename = ? AND source = ?
            """

            row = db.execute(query, (filename, source)).fetchone()
            if not row:
                return None

            # Parse tags from JSON string
            tags_list = []
            if row["tags"]:
                import json

                try:
                    tags_list = json.loads(row["tags"])
                except Exception:
                    tags_list = []

            photo = Photo(
                id=row["id"],
                filename=row["filename"],
                title=row["title"],
                description=row["description"],
                date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                source=row["source"],
                tags=tags_list,
                album_id=row["album_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

            return photo
        except Exception as e:
            self.logger.error(f"Error fetching photo by filename {filename} and source {source}: {e}")
            return None

    def get_recent_photos(self, limit: int = 10) -> List[Photo]:
        """Get recent photos"""
        try:
            db = get_db()

            query = """
                SELECT id, filename, title, description, date_taken, source, tags, album_id, created_at, updated_at
                FROM photos
                ORDER BY created_at DESC
                LIMIT ?
            """

            rows = db.execute(query, (limit,)).fetchall()

            photos = []
            for row in rows:
                # Parse tags from JSON string
                tags_list = []
                if row["tags"]:
                    import json

                    try:
                        tags_list = json.loads(row["tags"])
                    except Exception:
                        tags_list = []

                photo = Photo(
                    id=row["id"],
                    filename=row["filename"],
                    title=row["title"],
                    description=row["description"],
                    date_taken=datetime.fromisoformat(row["date_taken"]) if row["date_taken"] else None,
                    source=row["source"],
                    tags=tags_list,
                    album_id=row["album_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                photos.append(photo)

            return photos
        except Exception as e:
            self.logger.error(f"Error fetching recent photos: {e}")
            return []


# Global instance
photo_service = PhotoService()
