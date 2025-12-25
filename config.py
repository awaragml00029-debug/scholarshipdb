"""Configuration management for the scholarship scraper."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite:///./scholarships.db",
        description="Database connection URL"
    )

    # Scraper
    scraper_headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    scraper_timeout: int = Field(
        default=30000,
        description="Page load timeout in milliseconds"
    )
    scraper_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    scraper_delay_min: int = Field(
        default=2,
        description="Minimum delay between requests in seconds"
    )
    scraper_delay_max: int = Field(
        default=5,
        description="Maximum delay between requests in seconds"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: str = Field(
        default="scraper.log",
        description="Log file path"
    )

    # Target
    base_url: str = Field(
        default="https://scholarshipdb.net",
        description="Base URL for the scholarship database"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
