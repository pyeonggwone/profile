from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = ""

    # 번역
    source_lang: str = "en"
    target_lang: str = "ko"

    # 경로
    work_dir: Path = Path("work")
    tm_db_path: Path = Path("work/tm.sqlite")
    glossary_path: Path = Path("glossary.csv")

    @property
    def llm_model(self) -> str:
        if self.azure_openai_deployment:
            return f"azure/{self.azure_openai_deployment}"
        return self.openai_model


settings = Settings()
