"""Configuration management for FollowChat backend.

This module loads configuration from environment variables or .env file.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # If python-dotenv is not installed, we'll just use environment variables
    load_dotenv = lambda: None


# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # LLM Configuration
    API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "1.0"))

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Get API key from environment."""
        return cls.API_KEY

    @classmethod
    def get_base_url(cls) -> Optional[str]:
        """Get base URL from environment."""
        return cls.BASE_URL

    @classmethod
    def get_model_name(cls) -> str:
        """Get model name from environment."""
        return cls.MODEL_NAME

    @classmethod
    def get_temperature(cls) -> float:
        """Get temperature from environment."""
        return cls.TEMPERATURE

