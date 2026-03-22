from pydantic_settings import BaseSettings, SettingsConfigDict


class ERPScriptGeneratorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    OPENAI_API_KEY: str | None = None

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "nirbaan-erp-federated"

    PIPER_MODEL_PATH: str = "backend/app/ERPScriptGenerator/voices/en_US-lessac-medium.onnx"
    PIPER_OUTPUT_DIR: str = "backend/media/imaginal_audio"

    LANGGRAPH_CHECKPOINT_DB_URL: str | None = None

    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str | None = None
    R2_ENDPOINT_URL: str | None = None
    R2_PRESIGNED_URL_EXPIRY: int = 3600

    @property
    def checkpoint_db_url(self) -> str:
        return self.LANGGRAPH_CHECKPOINT_DB_URL or self.DATABASE_URL

    @property
    def has_r2_config(self) -> bool:
        return all([
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_BUCKET_NAME,
            self.R2_ENDPOINT_URL,
        ])


settings = ERPScriptGeneratorSettings()