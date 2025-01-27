from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvConfig(BaseSettings):
    # Configurações podem ter valores padrão
    AI_API_KEY: str
    
    # Carrega de .env automaticamente
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8'
    )

# Instância global de configurações
env = EnvConfig()