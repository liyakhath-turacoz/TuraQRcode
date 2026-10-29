from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / '.env', ROOT.parent / 'backend.env'), extra='ignore')
    database_url: str = ''
    secret_key: str = ''
    supabase_url: str = 'https://azwpcjgbbpruxyinqezt.supabase.co'
    supabase_publishable_key: str = ''
    public_base_url: str = 'http://127.0.0.1:8000'
    frontend_url: str = 'http://127.0.0.1:5173'
    cors_origins: str = 'http://127.0.0.1:5173,http://127.0.0.1:5174'
    cookie_secure: bool = False
    session_hours: int = 24
    initial_admin_email: str = 'Admin@turacoz.com'
    initial_admin_password: str = ''
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_from: str = ''
    smtp_starttls: bool = True

    @property
    def origins(self):
        return [v.strip().rstrip('/') for v in self.cors_origins.split(',') if v.strip()]


settings = Settings()
