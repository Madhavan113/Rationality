import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/market_data")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Service settings
    service_name: str = "service"
    service_host: str = "0.0.0.0"
    service_port: int = 8000
    
    # Email settings (for alerts service)
    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "1025"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "alerts@example.com")
    
    # Polymarket API settings
    polymarket_api_url: str = os.getenv("POLYMARKET_API_URL", "https://api.polymarket.com")
    polymarket_ws_url: str = os.getenv("POLYMARKET_WS_URL", "wss://api.polymarket.com/ws")
    
    # Aggregation settings
    aggregation_interval: int = int(os.getenv("AGGREGATION_INTERVAL", "1"))  # seconds
    
    class Config:
        env_file = ".env"

def get_settings():
    return Settings() 