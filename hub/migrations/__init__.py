from hub.migrations.audit import apply as apply_audit
from hub.migrations.auth import apply as apply_auth
from hub.migrations.cache_lru import apply as apply_cache_lru
from hub.migrations.calendar import apply as apply_calendar
from hub.migrations.casting import apply as apply_casting
from hub.migrations.chores import apply as apply_chores
from hub.migrations.core import apply as apply_core
from hub.migrations.iot import apply as apply_iot
from hub.migrations.music import apply as apply_music
from hub.migrations.news import apply as apply_news
from hub.migrations.performance_indexes import apply as apply_performance_indexes
from hub.migrations.photos import apply as apply_photos
from hub.migrations.plugins import apply as apply_plugins
from hub.migrations.recipes import apply as apply_recipes
from hub.migrations.weather import apply as apply_weather
from hub.migrations.webhooks import apply as apply_webhooks

MIGRATIONS = [
    ("core", apply_core),
    ("calendar", apply_calendar),
    ("auth", apply_auth),
    ("audit", apply_audit),
    ("recipes", apply_recipes),
    ("webhooks", apply_webhooks),
    ("weather", apply_weather),
    ("plugins", apply_plugins),
    ("casting", apply_casting),
    ("photos", apply_photos),
    ("music", apply_music),
    ("chores", apply_chores),
    ("news", apply_news),
    ("iot", apply_iot),
    ("cache_lru", apply_cache_lru),
    ("performance_indexes", apply_performance_indexes),
]
