from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la API pública STOP Carabineros."""

    app_name: str = "API Pública STOP Carabineros"
    app_description: str = (
        "API REST pública construida con FastAPI para consultar estadísticas delictuales, "
        "catálogos territoriales y capas geográficas del Sistema Táctico de Operación Policial "
        "(STOP) de Carabineros de Chile (https://stop.carabineros.cl/)."
    )
    app_version: str = "1.0.0"
    stop_base_url: str = "https://stop.carabineros.cl"
    http_timeout_seconds: float = 25.0
    cache_ttl_catalogs_seconds: int = 3600  # 1 hora
    cache_ttl_stats_seconds: int = 900      # 15 minutos
    cache_ttl_geo_seconds: int = 600        # 10 minutos
    cors_allow_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_prefix="STOP_API_", env_file=".env", extra="ignore")


settings = Settings()
