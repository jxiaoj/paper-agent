from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class PaperSource(StrEnum):
    ZOTERO = "zotero"
    ARXIV = "arxiv"
    MANUAL = "manual"


class Paper(BaseModel):
    id: int | None = None
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    published_date: date | None = None
    updated_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    comment: str | None = None
    doi: str | None = None
    item_type: str | None = None
    date_added: datetime | None = None
    date_modified: datetime | None = None
    source: PaperSource
    external_id: str | None = None
    url: HttpUrl | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.abstract or "",
            " ".join(self.tags),
            " ".join(self.collections),
            " ".join(self.categories),
        ]
        return "\n".join(part for part in parts if part.strip())


class ZoteroCollection(BaseModel):
    id: int | None = None
    collection_key: str
    name: str
    parent_key: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
