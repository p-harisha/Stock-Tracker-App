from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SW_")

    database_url: str = "sqlite:///./sector_watchlist.db"
    kite_api_key: str = ""
    kite_api_secret: str = ""
    # Where Kite sends you back after login; must match the redirect URL in your Kite developer app.
    frontend_url: str = "http://localhost:5173"


settings = Settings()
