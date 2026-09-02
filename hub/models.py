from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Union


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        if hasattr(value, "_to_dict"):
            return value._to_dict()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return _serialize_dataclass(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _serialize_dataclass(obj, exclude: Optional[Set[str]] = None, list_defaults: Optional[Set[str]] = None) -> Dict:
    data: Dict[str, Union[str, int, float, bool, None, List, Dict]] = {}
    for field in fields(obj):
        if exclude and field.name in exclude:
            continue
        value = getattr(obj, field.name)
        if list_defaults and field.name in list_defaults and value is None:
            value = []
        data[field.name] = _serialize_value(value)
    return data


class SerializableDataclass:
    def _to_dict(
        self,
        *,
        exclude: Optional[Set[str]] = None,
        list_defaults: Optional[Set[str]] = None,
        extra: Optional[Dict] = None,
    ) -> Dict:
        data = _serialize_dataclass(self, exclude=exclude, list_defaults=list_defaults)
        if extra:
            data.update(extra)
        return data


@dataclass
class CalendarEvent(SerializableDataclass):
    id: Optional[int] = None
    title: str = ""
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    location: Optional[str] = None
    source: str = "local"
    description: Optional[str] = None
    all_day: bool = False
    visibility: Optional[str] = None
    color: Optional[str] = None
    calendar_id: Optional[str] = None
    guests: Optional[List[str]] = None
    reminders: Optional[List[Union[str, int]]] = None
    owner: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[int, str, None, List[Union[str, int]]]]:
        return self._to_dict(list_defaults={"guests", "reminders"})


@dataclass
class Timer(SerializableDataclass):
    id: Optional[int] = None
    label: str = ""
    ends_at: Optional[datetime] = None
    active: bool = True

    def to_dict(self) -> Dict[str, Union[int, str, bool, None]]:
        return self._to_dict(extra={"time_remaining": self.time_remaining})

    @property
    def time_remaining(self) -> Optional[int]:
        """Get time remaining in seconds."""
        if self.ends_at and self.active:
            now = datetime.now(timezone.utc)
            if self.ends_at > now:
                return int((self.ends_at - now).total_seconds())
            return 0
        return None


@dataclass
class CurrentWeather(SerializableDataclass):
    temperature: float = 0.0
    feels_like: float = 0.0
    condition: str = ""
    humidity: int = 0
    wind_speed: float = 0.0
    location: str = "Unknown"
    timestamp: datetime = None
    severe_weather_indicators: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.severe_weather_indicators is None:
            self.severe_weather_indicators = []

    def to_dict(self) -> Dict[str, Union[float, str, int, List[str]]]:
        return self._to_dict(list_defaults={"severe_weather_indicators"})


@dataclass
class HourlyForecast(SerializableDataclass):
    time: datetime = None
    temperature: float = 0.0
    condition: str = ""

    def to_dict(self) -> Dict[str, Union[str, float, None]]:
        return self._to_dict()


@dataclass
class DailyForecast(SerializableDataclass):
    date: datetime = None
    high: float = 0.0
    low: float = 0.0
    condition: str = ""

    def to_dict(self) -> Dict[str, Union[str, float, None]]:
        return self._to_dict()


@dataclass
class Team(SerializableDataclass):
    id: str = ""
    name: str = ""
    abbreviation: str = ""
    logo_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[str, None]]:
        return self._to_dict()


@dataclass
class Game(SerializableDataclass):
    home_team: Team
    away_team: Team
    id: str = ""
    home_score: int = 0
    away_score: int = 0
    status: str = "scheduled"  # scheduled, in_progress, final
    start_time: Optional[datetime] = None
    quarter: Optional[str] = None  # quarter/period for ongoing games
    time_remaining: Optional[str] = None  # time remaining in quarter/period
    venue: Optional[str] = None
    broadcast: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[str, int, None]]:
        return self._to_dict()


@dataclass
class SportsData(SerializableDataclass):
    games: List[Game]
    last_updated: datetime = None
    source: str = "default"

    def __post_init__(self) -> None:
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[List[Dict], str]]:
        return self._to_dict()


@dataclass
class CastingDevice(SerializableDataclass):
    id: Optional[int] = None
    name: str = ""
    device_id: Optional[str] = None
    device_type: str = ""  # google_cast, roku, alexa, etc.
    ip_address: Optional[str] = None
    port: Optional[int] = None
    friendly_name: Optional[str] = None
    is_active: bool = True
    last_seen: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Union[int, str, bool, None]]:
        return self._to_dict()


@dataclass
class MediaQueue(SerializableDataclass):
    id: Optional[int] = None
    device_id: str = ""
    queue_items: Optional[List[Dict]] = None  # List of media items
    current_item_index: int = 0
    is_playing: bool = False
    volume: int = 50

    def __post_init__(self) -> None:
        if self.queue_items is None:
            self.queue_items = []

    def to_dict(self) -> Dict[str, Union[int, str, List[Dict], bool]]:
        return self._to_dict()


@dataclass
class CastingGroup(SerializableDataclass):
    id: Optional[int] = None
    name: str = ""
    devices: Optional[List[str]] = None  # List of device IDs
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.devices is None:
            self.devices = []

    def to_dict(self) -> Dict[str, Union[int, str, List[str], bool]]:
        return self._to_dict()


@dataclass
class Photo(SerializableDataclass):
    id: Optional[int] = None
    filename: str = ""
    title: str = ""
    description: Optional[str] = None
    date_taken: Optional[datetime] = None
    source: str = "local"  # local, google_photos, etc.
    tags: Optional[List[str]] = None
    album_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[int, str, List[str], None]]:
        return self._to_dict()


@dataclass
class Album(SerializableDataclass):
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    photo_count: int = 0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[int, str, None]]:
        return self._to_dict()


@dataclass
class MusicTrack(SerializableDataclass):
    id: Optional[int] = None
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    source: str = "local"  # local, spotify, etc.
    album_art_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[int, str, int, None]]:
        return self._to_dict()


@dataclass
class Playlist(SerializableDataclass):
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    track_count: int = 0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[int, str, None]]:
        return self._to_dict()


@dataclass
class MusicQueue(SerializableDataclass):
    id: Optional[int] = None
    playlist_id: Optional[int] = None
    queue_items: Optional[List[Dict]] = None  # List of track IDs or track objects
    current_item_index: int = 0
    is_playing: bool = False
    volume: int = 50
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.queue_items is None:
            self.queue_items = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Union[int, str, List[Dict], bool]]:
        return self._to_dict()
