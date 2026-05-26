from datetime import datetime

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: int | None = None
    explicit_interests: list[str] = Field(default_factory=list)
    inferred_keywords: list[str] = Field(default_factory=list)
    representative_papers: list[dict[str, str]] = Field(default_factory=list)
    research_summary: str = ""
    zotero_paper_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def profile_text(self) -> str:
        sections = [
            self.research_summary,
            "Explicit interests: " + ", ".join(self.explicit_interests),
            "Inferred keywords: " + ", ".join(self.inferred_keywords),
        ]
        return "\n".join(section for section in sections if section.strip())
