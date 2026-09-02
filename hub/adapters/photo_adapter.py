"""Photo adapters for different photo sources"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from hub.utils.http import RateLimitError, rate_limited_get, rate_limited_post

logger = logging.getLogger(__name__)


def get_photos_from_local(photo_path: str) -> List[Dict[str, Any]]:
    """
    Get photos from local directory.

    Args:
        photo_path: Path to the directory containing photos

    Returns:
        List of photo information dictionaries
    """
    photos = []

    # Define supported image extensions
    supported_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}

    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(photo_path):
        for file in files:
            # Get file extension
            _, ext = os.path.splitext(file.lower())

            # Check if it's a supported image format
            if ext in supported_extensions:
                file_path = os.path.join(root, file)

                try:
                    # Get file creation/modification time
                    stat = os.stat(file_path)
                    date_taken = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

                    # Extract basic info
                    photo_info = {
                        "filename": os.path.relpath(file_path, photo_path),  # Store relative path
                        "title": os.path.splitext(file)[0],  # Use filename without extension
                        "description": f"Photo from local directory: {file}",
                        "date_taken": date_taken,
                        "source": "local",
                        "album_id": None,  # Will be assigned when importing
                        "tags": [],  # Will be assigned during import or later
                    }

                    photos.append(photo_info)
                except Exception:
                    logger.exception("Error processing photo %s", file_path)

    return photos


def get_photos_from_google(client_id: str, client_secret: str, refresh_token: str) -> List[Dict[str, Any]]:
    """
    Get photos from Google Photos.

    Args:
        client_id: Google API client ID
        client_secret: Google API client secret
        refresh_token: Google API refresh token

    Returns:
        List of photo information dictionaries
    """

    try:
        # Step 1: Get access token using refresh token
        token_url = "https://oauth2.googleapis.com/token"  # nosec B105
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        token_response = rate_limited_post(token_url, data=token_data, service_name="google_photos")
        if token_response.status_code != 200:
            logger.error("Failed to refresh Google Photos access token: %s", token_response.text)
            return []

        access_token = token_response.json()["access_token"]

        # Step 2: Get photos from Google Photos
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get all media items from Google Photos
        media_items_url = "https://photoslibrary.googleapis.com/v1/mediaItems"
        params = {
            "pageSize": 100,
        }

        all_photos = []

        # Paginate through all media items
        while True:
            response = rate_limited_get(media_items_url, headers=headers, params=params, service_name="google_photos")
            if response.status_code != 200:
                logger.error("Failed to fetch Google Photos media items: %s", response.text)
                break

            data = response.json()
            media_items = data.get("mediaItems", [])

            for item in media_items:
                # Only process photos (not videos)
                if item.get("mimeType", "").startswith("image/"):
                    filename = item.get("filename", "untitled.jpg")
                    creation_time_str = item.get("mediaMetadata", {}).get("creationTime")

                    date_taken = None
                    if creation_time_str:
                        try:
                            date_taken = datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
                        except Exception:
                            date_taken = None

                    photo_info = {
                        "filename": filename,
                        "title": item.get("description", ""),
                        "description": item.get("description", ""),
                        "date_taken": date_taken,
                        "source": "google_photos",
                        "album_id": None,  # Will be assigned when importing
                        "tags": [],
                        "download_url": item.get("baseUrl", "") + "=d",  # Download URL
                    }

                    all_photos.append(photo_info)

            # Check if there are more pages
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            params["pageToken"] = next_page_token

        return all_photos

    except RateLimitError as e:
        logger.warning("Google Photos rate limited: %s", e)
        return []
    except Exception:
        logger.exception("Error fetching photos from Google Photos")
        return []


def get_albums_from_google(client_id: str, client_secret: str, refresh_token: str) -> List[Dict[str, Any]]:
    """
    Get albums from Google Photos.

    Args:
        client_id: Google API client ID
        client_secret: Google API client secret
        refresh_token: Google API refresh token

    Returns:
        List of album information dictionaries
    """
    albums = []

    try:
        # Step 1: Get access token using refresh token
        token_url = "https://oauth2.googleapis.com/token"  # nosec B105
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        token_response = rate_limited_post(token_url, data=token_data, service_name="google_photos")
        if token_response.status_code != 200:
            logger.error("Failed to refresh Google Photos access token: %s", token_response.text)
            return []

        access_token = token_response.json()["access_token"]

        # Step 2: Get albums from Google Photos
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get all albums from Google Photos
        albums_url = "https://photoslibrary.googleapis.com/v1/albums"
        params = {
            "pageSize": 50,
        }

        # Paginate through all albums
        while True:
            response = rate_limited_get(albums_url, headers=headers, params=params, service_name="google_photos")
            if response.status_code != 200:
                logger.error("Failed to fetch Google Photos albums: %s", response.text)
                break

            data = response.json()
            album_items = data.get("albums", [])

            for item in album_items:
                album_info = {
                    "id": item.get("id"),
                    "title": item.get("title", "Untitled Album"),
                    "description": item.get("description", ""),
                    "total_media_items": item.get("totalMediaItems", 0),
                }

                albums.append(album_info)

            # Check if there are more pages
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            params["pageToken"] = next_page_token

        return albums

    except RateLimitError as e:
        logger.warning("Google Photos rate limited: %s", e)
        return []
    except Exception:
        logger.exception("Error fetching albums from Google Photos")
        return []


def get_photos_from_album_google(
    client_id: str, client_secret: str, refresh_token: str, album_id: str
) -> List[Dict[str, Any]]:
    """
    Get photos from a specific Google Photos album.

    Args:
        client_id: Google API client ID
        client_secret: Google API client secret
        refresh_token: Google API refresh token
        album_id: ID of the album to fetch photos from

    Returns:
        List of photo information dictionaries
    """

    try:
        # Step 1: Get access token using refresh token
        token_url = "https://oauth2.googleapis.com/token"  # nosec B105
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        token_response = rate_limited_post(token_url, data=token_data, service_name="google_photos")
        if token_response.status_code != 200:
            logger.error("Failed to refresh Google Photos access token: %s", token_response.text)
            return []

        access_token = token_response.json()["access_token"]

        # Step 2: Get photos from the specific album
        headers = {"Authorization": f"Bearer {access_token}"}

        album_media_items_url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
        payload = {
            "albumId": album_id,
            "pageSize": 100,
        }

        all_photos = []

        # Paginate through all media items in album
        page_token = None
        while True:
            if page_token:
                payload["pageToken"] = page_token

            response = rate_limited_post(
                album_media_items_url, headers=headers, json=payload, service_name="google_photos"
            )
            if response.status_code != 200:
                logger.error("Failed to fetch Google Photos album items: %s", response.text)
                break

            data = response.json()
            media_items = data.get("mediaItems", [])

            for item in media_items:
                # Only process photos (not videos)
                if item.get("mimeType", "").startswith("image/"):
                    filename = item.get("filename", "untitled.jpg")
                    creation_time_str = item.get("mediaMetadata", {}).get("creationTime")

                    date_taken = None
                    if creation_time_str:
                        try:
                            date_taken = datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
                        except Exception:
                            date_taken = None

                    photo_info = {
                        "filename": filename,
                        "title": item.get("description", ""),
                        "description": item.get("description", ""),
                        "date_taken": date_taken,
                        "source": "google_photos",
                        "album_id": album_id,
                        "tags": [],
                        "download_url": item.get("baseUrl", "") + "=d",  # Download URL
                    }

                    all_photos.append(photo_info)

            # Check if there are more pages
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            page_token = next_page_token

        return all_photos

    except RateLimitError as e:
        logger.warning("Google Photos rate limited: %s", e)
        return []
    except Exception:
        logger.exception("Error fetching photos from Google Photos album %s", album_id)
        return []


def get_photos_from_cloudinary(cloud_name: str, api_key: str, api_secret: str) -> List[Dict[str, Any]]:
    """
    Get photos from Cloudinary.

    Args:
        cloud_name: Cloudinary cloud name
        api_key: Cloudinary API key
        api_secret: Cloudinary API secret

    Returns:
        List of photo information dictionaries
    """
    photos = []

    try:
        # Configure Cloudinary
        import cloudinary
        from cloudinary import api

        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

        # Get all resources from Cloudinary
        result = api.resources(type="upload", resource_type="image", max_results=500)

        for resource in result.get("resources", []):
            date_taken_str = resource.get("created_at", "")

            date_taken = None
            if date_taken_str:
                try:
                    # Convert the timestamp string to datetime object
                    date_taken = datetime.fromisoformat(date_taken_str.replace("Z", "+00:00"))
                except Exception:
                    date_taken = None

            photo_info = {
                "filename": resource.get("public_id", "unknown.jpg"),
                "title": resource.get("public_id", "Unknown"),
                "description": resource.get("context", {}).get("custom", {}).get("caption", ""),
                "date_taken": date_taken,
                "source": "cloudinary",
                "album_id": None,
                "tags": resource.get("tags", []),
                "url": resource.get("secure_url", ""),
            }

            photos.append(photo_info)

        return photos

    except Exception:
        logger.exception("Error fetching photos from Cloudinary")
        return []


def get_photos_from_flickr(api_key: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Get photos from Flickr.

    Args:
        api_key: Flickr API key
        user_id: Flickr user ID

    Returns:
        List of photo information dictionaries
    """

    try:
        # Using requests to call Flickr API
        url = "https://api.flickr.com/services/rest/"
        params = {
            "method": "flickr.people.getPhotos",
            "api_key": api_key,
            "user_id": user_id,
            "format": "json",
            "nojsoncallback": 1,
            "per_page": 100,
            "page": 1,
        }

        all_photos = []

        while True:
            response = rate_limited_get(url, params=params, service_name="flickr")
            if response.status_code != 200:
                logger.error("Failed to fetch photos from Flickr: %s", response.text)
                break

            data = response.json()

            if data.get("stat") != "ok":
                logger.error("Flickr API error: %s", data)
                break

            for photo in data.get("photos", {}).get("photo", []):
                # Build photo URL
                # Format: https://farm{farm-id}.staticflickr.com/{server-id}/{id}_{secret}.jpg
                photo_url = f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}.jpg"

                # The API doesn't directly provide the taken date, only uploaded date
                # We could use flickr.photos.getInfo for more details but it would be inefficient for many photos
                photo_info = {
                    "filename": f"{photo['title']}.jpg",
                    "title": photo["title"],
                    "description": photo.get("description", {}).get("_content", ""),
                    "date_taken": None,  # Not available from this API call
                    "source": "flickr",
                    "album_id": None,
                    "tags": photo.get("tags", "").split(),
                    "url": photo_url,
                }

                all_photos.append(photo_info)

            # Check if we've fetched all photos
            photos_info = data.get("photos", {})
            page = photos_info.get("page", 1)
            pages = photos_info.get("pages", 1)

            if page >= pages:
                break

            params["page"] = page + 1

        return all_photos

    except RateLimitError as e:
        logger.warning("Flickr rate limited: %s", e)
        return []
    except Exception:
        logger.exception("Error fetching photos from Flickr")
        return []
