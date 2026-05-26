import argparse
import json
import re
from dataclasses import dataclass

from agents.ranker_agent import RankedCandidate, run_local_ranking
from app.config import Settings, get_settings
from llm.prompts import build_rerank_messages
from memory.sqlite_store import SQLiteStore
from models.recommendation import Recommendation, RecommendationCard, RerankResponse
from models.user_profile import UserProfile


@dataclass
class FinalRecommendation:
    candidate: RankedCandidate
    card: RecommendationCard
    llm_score: float | None
    source: str


class OpenAICompatibleClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.has_llm_credentials:
            raise ValueError("LLM_API_KEY is not configured.")
        from openai import OpenAI

        self.model_name = settings.llm_model_name
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base_url,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()


class LLMReranker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rerank(
        self,
        profile: UserProfile,
        ranked_candidates: list[RankedCandidate],
        top_k: int,
    ) -> tuple[list[FinalRecommendation], str]:
        limited_candidates = ranked_candidates[: max(top_k, len(ranked_candidates))]
        if not self.settings.has_llm_credentials:
            return _fallback_recommendations(profile, limited_candidates, top_k), "local_fallback_no_credentials"

        try:
            client = OpenAICompatibleClient(self.settings)
            raw_response = client.complete(build_rerank_messages(profile, limited_candidates, top_k))
            parsed = _parse_rerank_response(raw_response)
            recommendations = _map_llm_selections(parsed, limited_candidates, top_k)
            if not recommendations:
                raise ValueError("LLM returned no usable candidate selections.")
            if len(recommendations) < top_k:
                selected_ids = {item.candidate.paper.external_id for item in recommendations}
                remaining = [
                    item for item in limited_candidates if item.paper.external_id not in selected_ids
                ]
                recommendations.extend(
                    _fallback_recommendations(profile, remaining, top_k - len(recommendations))
                )
            return recommendations[:top_k], "llm"
        except Exception:
            return _fallback_recommendations(profile, limited_candidates, top_k), "local_fallback_llm_error"


def run_llm_reranking(
    local_top_n: int | None = None,
    final_top_k: int | None = None,
    candidate_limit: int = 200,
    include_recommended: bool = True,
    save_recommendations: bool = True,
) -> tuple[list[FinalRecommendation], str, str]:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.init_schema()
    profile = store.get_latest_user_profile()
    if profile is None:
        raise RuntimeError("No user profile found. Run Profile Agent first.")

    ranked, embedding_backend = run_local_ranking(
        candidate_limit=candidate_limit,
        top_n=local_top_n or settings.local_top_k,
        include_recommended=include_recommended,
        save_local_rankings=False,
    )
    reranker = LLMReranker(settings)
    final_recommendations, rerank_source = reranker.rerank(
        profile=profile,
        ranked_candidates=ranked,
        top_k=final_top_k or settings.final_top_k,
    )

    if save_recommendations:
        for rank, item in enumerate(final_recommendations, start=1):
            store.save_recommendation(
                Recommendation(
                    paper_id=item.candidate.paper.id,
                    local_score=item.candidate.local_score,
                    llm_score=item.llm_score,
                    rank=rank,
                    reason=item.card.why_recommended,
                    card=item.card,
                )
            )
    return final_recommendations, rerank_source, embedding_backend


def _parse_rerank_response(content: str) -> RerankResponse:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(0)
    return RerankResponse.model_validate(json.loads(stripped))


def _map_llm_selections(
    response: RerankResponse,
    ranked_candidates: list[RankedCandidate],
    top_k: int,
) -> list[FinalRecommendation]:
    candidates_by_external_id = {
        item.paper.external_id: item for item in ranked_candidates if item.paper.external_id
    }
    final: list[FinalRecommendation] = []
    seen: set[str] = set()
    for selected in response.selected_papers:
        if selected.external_id in seen or selected.external_id not in candidates_by_external_id:
            continue
        candidate = candidates_by_external_id[selected.external_id]
        final.append(
            FinalRecommendation(
                candidate=candidate,
                llm_score=selected.rerank_score,
                source="llm",
                card=RecommendationCard(
                    title=candidate.paper.title,
                    authors=candidate.paper.authors,
                    arxiv_url=candidate.paper.url,
                    one_sentence_summary=selected.one_sentence_summary,
                    why_recommended=selected.why_recommended,
                    related_user_interests=selected.related_user_interests,
                    reading_priority=selected.reading_priority,
                ),
            )
        )
        seen.add(selected.external_id)
        if len(final) >= top_k:
            break
    return final


def _fallback_recommendations(
    profile: UserProfile,
    ranked_candidates: list[RankedCandidate],
    top_k: int,
) -> list[FinalRecommendation]:
    profile_keywords = set(keyword.lower() for keyword in profile.inferred_keywords)
    final: list[FinalRecommendation] = []
    for candidate in ranked_candidates[:top_k]:
        paper_text = f"{candidate.paper.title} {candidate.paper.abstract or ''}".lower()
        related = [
            keyword for keyword in profile.inferred_keywords if keyword.lower() in paper_text
        ][:5]
        if not related:
            related = [keyword for keyword in profile.explicit_interests if keyword.lower() in paper_text][:5]
        if not related and profile_keywords:
            related = profile.inferred_keywords[:2]
        summary = _first_sentence(candidate.paper.abstract) or candidate.paper.title
        final.append(
            FinalRecommendation(
                candidate=candidate,
                llm_score=None,
                source="local_fallback",
                card=RecommendationCard(
                    title=candidate.paper.title,
                    authors=candidate.paper.authors,
                    arxiv_url=candidate.paper.url,
                    one_sentence_summary=summary,
                    why_recommended=(
                        "Selected by local semantic similarity and keyword matching "
                        f"(local score {candidate.local_score:.3f})."
                    ),
                    related_user_interests=related,
                    reading_priority="medium",
                ),
            )
        )
    return final


def _first_sentence(text: str | None) -> str:
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", text).strip()
    match = re.match(r"(.+?[.!?])(?:\s|$)", collapsed)
    sentence = match.group(1) if match else collapsed
    return sentence[:260]


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Rerank local paper candidates with an OpenAI-compatible LLM.")
    parser.add_argument("--local-top-n", type=int, default=settings.local_top_k, help="Candidate count sent to reranking.")
    parser.add_argument("--top-k", type=int, default=settings.final_top_k, help="Final recommendation count.")
    parser.add_argument("--candidate-limit", type=int, default=200, help="Maximum stored candidates to consider.")
    parser.add_argument(
        "--exclude-recommended",
        action="store_true",
        help="Filter papers already present in recommendation history before reranking.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not save final recommendations.")
    args = parser.parse_args()

    recommendations, source, embedding_backend = run_llm_reranking(
        local_top_n=args.local_top_n,
        final_top_k=args.top_k,
        candidate_limit=args.candidate_limit,
        include_recommended=not args.exclude_recommended,
        save_recommendations=not args.dry_run,
    )
    print("LLM Reranker: OK")
    print(f"Rerank source: {source}")
    print(f"Embedding backend: {embedding_backend}")
    print(f"Final recommendations: {len(recommendations)}")
    print(f"Saved recommendations: {not args.dry_run}")
    for index, item in enumerate(recommendations, start=1):
        score = f"{item.llm_score:.3f}" if item.llm_score is not None else "fallback"
        print(f"{index}. {item.card.title} [rerank_score={score}, priority={item.card.reading_priority}]")
        print(f"   Summary: {item.card.one_sentence_summary}")
        print(f"   Why: {item.card.why_recommended}")


if __name__ == "__main__":
    main()
