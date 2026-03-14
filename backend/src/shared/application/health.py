from shared.config.settings import Settings


def build_platform_health(settings: Settings) -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "provider": "IG Labs",
        "streaming": "Lightstreamer",
    }
