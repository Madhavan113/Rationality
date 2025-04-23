import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Settings(BaseSettings):
    # Supabase settings
    supabase_db_url: str = os.getenv("SUPABASE_DB_URL")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
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
        # Keep env_file for potential overrides, but primary loading is via load_dotenv()
        env_file = ".env"

def get_settings():
    settings = Settings()
    if not settings.supabase_db_url:
        raise ValueError("SUPABASE_DB_URL environment variable not set.")
    # Add checks for other Supabase keys if necessary
    return settings