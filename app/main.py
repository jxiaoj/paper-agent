import argparse
import sys
from pathlib import Path

from config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_health_check() -> None:
    settings = get_settings()
    database_path = Path(settings.database_path)

    print("Local-first Personalized Academic Paper Recommendation Agent")
    print("Startup health check: OK")
    print(f"Database path: {database_path}")
    print(f"LLM base URL: {settings.llm_api_base_url}")
    print(f"LLM model: {settings.llm_model_name}")
    print(f"LLM credentials configured: {settings.has_llm_credentials}")
    print(f"Zotero credentials configured: {settings.has_zotero_credentials}")
    print(f"Interest keywords: {', '.join(settings.user_interest_keywords) or '(none configured)'}")
    print(f"arXiv categories: {', '.join(settings.arxiv_categories)}")


def run_db_smoke_test() -> None:
    from memory.sqlite_store import SQLiteStore
    from models.paper import Paper, PaperSource
    from models.recommendation import Feedback, FeedbackType, LocalRanking, Recommendation, RecommendationCard
    from models.user_profile import UserProfile

    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.init_schema()

    paper = store.save_candidate_paper(
        Paper(
            title="SQLite Smoke Test Paper",
            abstract="A tiny local-first storage smoke test.",
            authors=["Ada Lovelace", "Grace Hopper"],
            year=2026,
            tags=["agent", "recommendation"],
            categories=["cs.AI"],
            primary_category="cs.AI",
            source=PaperSource.ARXIV,
            external_id="module-1-smoke-test",
            url="https://example.com/paper",
        )
    )
    recommendation = store.save_recommendation(
        Recommendation(
            paper_id=paper.id,
            local_score=0.91,
            llm_score=0.88,
            rank=1,
            reason="Useful smoke-test recommendation.",
            card=RecommendationCard(
                title=paper.title,
                authors=paper.authors,
                arxiv_url=None,
                one_sentence_summary="A local SQLite smoke test.",
                why_recommended="It verifies the module 1 persistence path.",
                related_user_interests=["AI agents"],
                reading_priority="high",
            ),
        )
    )
    local_ranking = store.save_local_ranking(
        LocalRanking(
            paper_id=paper.id,
            local_score=0.91,
            rank=1,
            reason="Smoke-test local ranking.",
        )
    )
    feedback = store.save_feedback(
        Feedback(
            recommendation_id=recommendation.id,
            paper_id=paper.id,
            feedback_type=FeedbackType.LIKE,
            note="Smoke test feedback.",
        )
    )
    profile = store.save_user_profile(
        UserProfile(
            explicit_interests=["AI agents", "paper recommendation"],
            inferred_keywords=["local-first workflows"],
            representative_papers=[
                {
                    "title": paper.title,
                    "year": str(paper.year or ""),
                    "source": paper.source.value,
                    "external_id": paper.external_id or "",
                }
            ],
            research_summary="Smoke-test profile for module 1.",
            zotero_paper_count=0,
        )
    )

    print("SQLite smoke test: OK")
    print(f"Database path: {settings.database_path}")
    print(f"Saved paper id: {paper.id}")
    print(f"Saved recommendation id: {recommendation.id}")
    print(f"Saved local ranking id: {local_ranking.id}")
    print(f"Saved feedback id: {feedback.id}")
    print(f"Saved user profile id: {profile.id}")
    print(f"Candidate paper count sample: {len(store.get_candidate_papers(limit=5))}")
    print(f"User library paper count sample: {len(store.get_user_library_papers(limit=5))}")
    print(f"Recommendation count sample: {len(store.list_recommendations(limit=5))}")
    print(f"Local ranking count sample: {len(store.list_local_rankings(limit=5))}")
    print(f"Feedback count sample: {len(store.list_feedback(limit=5))}")
    latest_profile = store.get_latest_user_profile()
    print(f"Latest profile summary: {latest_profile.research_summary if latest_profile else '(none)'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-first paper recommendation agent")
    parser.add_argument(
        "--db-smoke-test",
        action="store_true",
        help="Initialize SQLite and verify basic paper/recommendation/feedback/profile read-write.",
    )
    args = parser.parse_args()

    if args.db_smoke_test:
        run_db_smoke_test()
    else:
        run_health_check()


if __name__ == "__main__":
    main()
