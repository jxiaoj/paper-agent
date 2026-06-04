import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_CONFIG_PATH = Path("project_config.toml")
PROJECT_CONFIG_ALIASES = {
    "database_path": "DATABASE_PATH",
    "embedding_model_name": "EMBEDDING_MODEL_NAME",
    "local_top_k": "LOCAL_TOP_K",
    "final_top_k": "FINAL_TOP_K",
    "profile_mode": "PROFILE_MODE",
    "profile_max_papers": "PROFILE_MAX_PAPERS",
    "profile_top_keywords": "PROFILE_TOP_KEYWORDS",
    "profile_representative_count": "PROFILE_REPRESENTATIVE_COUNT",
    "zotero_max_items": "ZOTERO_MAX_ITEMS",
    "ranking_mode": "RANKING_MODE",
    "embedding_backend": "EMBEDDING_BACKEND",
    "candidate_limit": "CANDIDATE_LIMIT",
    "library_limit": "LIBRARY_LIMIT",
}


def load_project_config(path: Path = PROJECT_CONFIG_PATH) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("rb") as file:
        raw_config = tomllib.load(file)
    return {
        alias: raw_config[key]
        for key, alias in PROJECT_CONFIG_ALIASES.items()
        if key in raw_config
    }


class Settings(BaseSettings):
    """Runtime settings loaded from .env plus internal project_config.toml defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_API_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model_name: str = Field(default="gpt-4o-mini", alias="LLM_MODEL_NAME")

    zotero_user_id: str = Field(default="", alias="ZOTERO_USER_ID")
    zotero_api_key: str = Field(default="", alias="ZOTERO_API_KEY")
    zotero_library_type: str = Field(default="user", alias="ZOTERO_LIBRARY_TYPE")
    zotero_analysis_scope: str = Field(default="all", alias="ZOTERO_ANALYSIS_SCOPE")
    zotero_selected_collections: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        alias="ZOTERO_SELECTED_COLLECTIONS",
    )

    database_path: Path = Field(default=Path("data/local.db"), alias="DATABASE_PATH")
    user_interest_keywords: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        alias="USER_INTEREST_KEYWORDS",
    )
    arxiv_categories: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["cs.AI", "cs.CL", "cs.LG"],
        alias="ARXIV_CATEGORIES",
    )
    arxiv_lookback_days: int = Field(default=3, alias="ARXIV_LOOKBACK_DAYS")
    arxiv_max_results: int = Field(default=50, alias="ARXIV_MAX_RESULTS")
    arxiv_request_delay_seconds: float = Field(default=3.0, alias="ARXIV_REQUEST_DELAY_SECONDS")
    arxiv_num_retries: int = Field(default=1, alias="ARXIV_NUM_RETRIES")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_NAME",
    )
    local_top_k: int = Field(default=20, alias="LOCAL_TOP_K")
    final_top_k: int = Field(default=5, alias="FINAL_TOP_K")
    profile_mode: str = Field(default="hybrid", alias="PROFILE_MODE")
    profile_max_papers: int = Field(default=200, alias="PROFILE_MAX_PAPERS")
    profile_top_keywords: int = Field(default=12, alias="PROFILE_TOP_KEYWORDS")
    profile_representative_count: int = Field(default=5, alias="PROFILE_REPRESENTATIVE_COUNT")
    zotero_max_items: int = Field(default=100, alias="ZOTERO_MAX_ITEMS")
    ranking_mode: str = Field(default="library", alias="RANKING_MODE")
    embedding_backend: str = Field(default="auto", alias="EMBEDDING_BACKEND")
    candidate_limit: int = Field(default=200, alias="CANDIDATE_LIMIT")
    library_limit: int = Field(default=500, alias="LIBRARY_LIMIT")

    @field_validator("user_interest_keywords", "arxiv_categories", "zotero_selected_collections", mode="before")
    @classmethod
    def parse_csv_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value.startswith("[") and stripped_value.endswith("]"):
                import json

                return [str(item).strip() for item in json.loads(stripped_value) if str(item).strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("Expected a comma-separated string or list.")

    @field_validator("zotero_analysis_scope")
    @classmethod
    def validate_zotero_analysis_scope(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"all", "selected"}:
            raise ValueError("ZOTERO_ANALYSIS_SCOPE must be 'all' or 'selected'.")
        return normalized

    @field_validator("profile_mode")
    @classmethod
    def validate_profile_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "hybrid", "llm"}:
            raise ValueError("profile_mode must be 'local', 'hybrid', or 'llm'.")
        return normalized

    @field_validator("ranking_mode")
    @classmethod
    def validate_ranking_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"library", "profile"}:
            raise ValueError("ranking_mode must be 'library' or 'profile'.")
        return normalized

    @field_validator("embedding_backend")
    @classmethod
    def validate_embedding_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "sentence-transformers", "hashing"}:
            raise ValueError("embedding_backend must be 'auto', 'sentence-transformers', or 'hashing'.")
        return normalized

    @property
    def has_llm_credentials(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def has_zotero_credentials(self) -> bool:
        return bool(self.zotero_user_id.strip() and self.zotero_api_key.strip())

    @property
    def active_zotero_collection_keys(self) -> list[str] | None:
        if self.zotero_analysis_scope == "all":
            return None
        return self.zotero_selected_collections


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(**load_project_config())
