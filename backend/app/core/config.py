from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://jansahay:jansahay@localhost:5432/jansahay"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    admin_full_name: str = "JanSahay Admin"
    admin_email: str = "admin@jansahay.dev"
    admin_password: str = "change-admin-password"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "jansahay_documents"
    embedding_model: str = "gemini-embedding-001"

    # Neo4j / GraphRAG
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Document upload settings
    document_upload_dir: str = "data/documents"
    max_upload_size_mb: int = 20

    # Voice settings
    stt_provider: str = "gemini"
    tts_provider: str = "gtts"
    max_audio_size_mb: int = 10
    voice_temp_dir: str = "data/voice_tmp"

    @property
    def max_audio_size_bytes(self) -> int:
        return self.max_audio_size_mb * 1024 * 1024

    @property
    def voice_temp_path(self) -> Path:
        return Path(self.voice_temp_dir)

    @property
    def document_upload_path(self) -> Path:
        return Path(self.document_upload_dir)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def neo4j_configured(self) -> bool:
        """True when all three required Neo4j settings are non-empty."""
        return bool(
            self.neo4j_uri.strip()
            and self.neo4j_username.strip()
            and self.neo4j_password.strip()
        )


settings = Settings()
