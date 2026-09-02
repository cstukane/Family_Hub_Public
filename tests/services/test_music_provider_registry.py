from hub.services.music_providers.providers import registry


def test_registry_lists_spotify_with_model_config(app):
    with app.app_context():
        providers = registry.list_providers()
        ids = {provider.id for provider in providers}
        assert "spotify" in ids


def test_registry_lists_optional_providers_when_enabled_in_dict_config(app):
    app.config["CONFIG"] = {
        "music": {
            "spotify": {"enabled": True},
            "providers": {
                "radio_browser": {"enabled": True},
                "somafm": {"enabled": True},
                "podcast_index": {"enabled": True},
            },
        }
    }

    with app.app_context():
        providers = registry.list_providers()
        ids = {provider.id for provider in providers}

    assert "spotify" in ids
    assert "radio_browser" in ids
    assert "somafm" in ids
    assert "podcast_index" in ids


def test_registry_excludes_optional_providers_when_disabled(app):
    app.config["CONFIG"] = {
        "music": {
            "spotify": {"enabled": True},
            "providers": {
                "radio_browser": {"enabled": False},
                "somafm": {"enabled": False},
                "podcast_index": {"enabled": False},
            },
        }
    }

    with app.app_context():
        providers = registry.list_providers()
        ids = {provider.id for provider in providers}

    assert "spotify" in ids
    assert "radio_browser" not in ids
    assert "somafm" not in ids
    assert "podcast_index" not in ids
