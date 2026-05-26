from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class FeedbackType(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"
    SAVE = "save"
    NOT_RELEVANT = "not_relevant"
    ALREADY_READ = "already_read"


class RecommendationCard(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    arxiv_url: HttpUrl | None = None
    one_sentence_summary: str = ""
    why_recommended: str = ""
    related_user_interests: list[str] = Field(default_factory=list)
    reading_priority: str = "medium"


class RerankedPaper(BaseModel):
    external_id: str
    rerank_score: float = Field(ge=0.0, le=1.0)
    one_sentence_summary: str
    why_recommended: str
    related_user_interests: list[str] = Field(default_factory=list)
    reading_priority: str = "medium"


class RerankResponse(BaseModel):
    selected_papers: list[RerankedPaper] = Field(default_factory=list)


class LocalRanking(BaseModel):
    id: int | None = None
    paper_id: int | None = None
    ranking_date: date = Field(default_factory=date.today)
    ranking_method: str = "profile"
    local_score: float
    rank: int
    reason: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Recommendation(BaseModel):
    id: int | None = None
    paper_id: int | None = None
    recommendation_date: date = Field(default_factory=date.today)
    local_score: float | None = None
    llm_score: float | None = None
    rank: int | None = None
    reason: str = ""
    card: RecommendationCard | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Feedback(BaseModel):
    id: int | None = None
    recommendation_id: int | None = None
    paper_id: int | None = None
    feedback_type: FeedbackType
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
