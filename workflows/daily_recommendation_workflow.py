import argparse
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.profile_agent import build_and_save_profile
from agents.ranker_agent import run_local_ranking
from app.config import get_settings
from connectors.arxiv_connector import save_arxiv_papers
from connectors.zotero_connector import ZoteroConfigError, save_zotero_papers
from llm.client import FinalRecommendation, run_llm_reranking
from memory.sqlite_store import SQLiteStore
from models.paper import PaperSource
from models.recommendation import RankingRun
from models.user_profile import UserProfile


@dataclass
class WorkflowContext:
    store: SQLiteStore
    profile: UserProfile | None = None
    ranking_run: RankingRun | None = None
    recommendations: list[FinalRecommendation] | None = None
    rerank_source: str = ""


@dataclass
class StepResult:
    name: str
    status: str
    message: str
    elapsed_seconds: float


class WorkflowStop(RuntimeError):
    """Raised when the workflow cannot continue safely."""


def run_daily_recommendation_workflow(args: argparse.Namespace) -> list[FinalRecommendation]:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    context = WorkflowContext(store=store)
    results: list[StepResult] = []

    print("Daily Recommendation Workflow")
    print(f"Database: {settings.database_path}")
    print(f"Ranking mode: {args.ranking_mode}")
    print(f"Profile mode: {args.profile_mode}")
    print(f"Zotero analysis scope: {settings.zotero_analysis_scope}")
    if settings.zotero_analysis_scope == "selected":
        print(f"Selected Zotero collections: {', '.join(settings.zotero_selected_collections) or '(none)'}")
    print(f"Final top K: {args.final_top_k}")
    print(f"Dry run: {args.dry_run}")

    steps: list[tuple[str, Callable[[], str]]] = [
        ("Initialize SQLite", lambda: _initialize_sqlite(context)),
        ("Sync Zotero library", lambda: _sync_zotero(context, args.zotero_max_items, args.skip_zotero)),
        ("Build user profile", lambda: _build_profile(context, args)),
        ("Collect arXiv candidates", lambda: _collect_arxiv(context, args)),
        ("Run local rough ranking", lambda: _run_local_ranking(context, args)),
        ("Run LLM reranking", lambda: _run_llm_reranking(context, args)),
    ]

    for index, (name, action) in enumerate(steps, start=1):
        results.append(_run_step(index, len(steps), name, action))

    _print_recommendations(context.recommendations or [])
    _print_summary(results)
    return context.recommendations or []


def _run_step(
    index: int,
    total: int,
    name: str,
    action: Callable[[], str],
) -> StepResult:
    start = time.perf_counter()
    print(f"\n[{index}/{total}] {name}: START")
    try:
        message = action()
    except WorkflowStop as exc:
        elapsed = time.perf_counter() - start
        print(f"[{index}/{total}] {name}: STOP ({elapsed:.1f}s)")
        print(f"  {exc}")
        raise
    except Exception as exc:
        elapsed = time.perf_counter() - start
        print(f"[{index}/{total}] {name}: FAILED ({elapsed:.1f}s)")
        print(f"  {exc}")
        raise WorkflowStop(f"Step '{name}' failed unexpectedly.") from exc

    elapsed = time.perf_counter() - start
    status = "SKIPPED" if message.startswith("Skipped") else "OK"
    print(f"[{index}/{total}] {name}: {status} ({elapsed:.1f}s)")
    print(f"  {message}")
    return StepResult(name=name, status=status, message=message, elapsed_seconds=elapsed)


def _initialize_sqlite(context: WorkflowContext) -> str:
    context.store.init_schema()
    library_count = _count_rows(context.store, "user_library_papers")
    candidate_count = _count_rows(context.store, "candidate_papers")
    recommendation_count = _count_rows(context.store, "recommendations")
    return (
        f"Schema ready. library_papers={library_count}, "
        f"candidate_papers={candidate_count}, recommendations={recommendation_count}."
    )


def _sync_zotero(context: WorkflowContext, max_items: int, skip: bool) -> str:
    if skip:
        return f"Skipped Zotero sync. Existing Zotero papers: {_count_zotero_papers(context.store)}."
    try:
        papers = save_zotero_papers(max_items=max_items)
        collection_count = len(context.store.list_zotero_collections())
        return f"Fetched and saved {len(papers)} Zotero papers. Synced {collection_count} Zotero collections."
    except ZoteroConfigError as exc:
        existing_count = _count_zotero_papers(context.store)
        if existing_count > 0:
            return f"Skipped remote Zotero sync after configuration error; using {existing_count} local papers. {exc}"
        raise WorkflowStop(f"Zotero credentials are required because no local Zotero papers exist. {exc}") from exc
    except Exception as exc:
        existing_count = _count_zotero_papers(context.store)
        if existing_count > 0:
            return f"Remote Zotero sync failed; continuing with {existing_count} local papers. {exc}"
        raise WorkflowStop(f"Zotero sync failed and no local Zotero papers exist. {exc}") from exc


def _build_profile(context: WorkflowContext, args: argparse.Namespace) -> str:
    profile = build_and_save_profile(
        max_papers=args.profile_max_papers,
        top_keywords=args.top_keywords,
        representative_count=args.representative_count,
        profile_mode=args.profile_mode,
    )
    context.profile = profile
    keyword_preview = ", ".join(profile.inferred_keywords[:5]) or "(none)"
    return (
        f"Saved profile id={profile.id}; zotero_paper_count={profile.zotero_paper_count}; "
        f"top_keywords={keyword_preview}."
    )


def _collect_arxiv(context: WorkflowContext, args: argparse.Namespace) -> str:
    if args.skip_arxiv:
        return f"Skipped arXiv collection. Existing arXiv candidates: {_count_arxiv_candidates(context.store)}."
    try:
        papers = save_arxiv_papers(
            categories=args.categories,
            lookback_days=args.lookback_days,
            max_results=args.arxiv_max_results,
            request_delay_seconds=args.arxiv_request_delay_seconds,
            num_retries=args.arxiv_retries,
        )
        return (
            f"Fetched and saved {len(papers)} arXiv candidates. "
            f"categories={', '.join(args.categories)}, lookback_days={args.lookback_days}."
        )
    except Exception as exc:
        existing_count = _count_arxiv_candidates(context.store)
        if existing_count > 0:
            return f"arXiv collection failed; continuing with {existing_count} local candidates. {exc}"
        raise WorkflowStop(f"arXiv collection failed and no local candidates exist. {exc}") from exc


def _run_local_ranking(context: WorkflowContext, args: argparse.Namespace) -> str:
    ranked, backend, ranking_run = run_local_ranking(
        candidate_limit=args.candidate_limit,
        library_limit=args.library_limit,
        top_n=args.local_top_n,
        ranking_mode=args.ranking_mode,
        include_recommended=args.include_recommended,
        save_local_rankings=True,
        embedding_backend=args.embedding_backend,
    )
    if ranking_run is None:
        raise WorkflowStop("Local ranking did not create a ranking run.")
    if not ranked:
        raise WorkflowStop("Local ranking produced no candidates.")
    context.ranking_run = ranking_run
    top_title = ranked[0].paper.title if ranked else "(none)"
    return (
        f"Saved ranking_run_id={ranking_run.id}; method={ranking_run.ranking_method}; "
        f"backend={backend}; ranked={len(ranked)}; top='{top_title}'."
    )


def _run_llm_reranking(context: WorkflowContext, args: argparse.Namespace) -> str:
    if context.ranking_run is None or context.ranking_run.id is None:
        raise WorkflowStop("No ranking run is available for LLM reranking.")
    recommendations, source, ranking_run, error_reason = run_llm_reranking(
        ranking_run_id=context.ranking_run.id,
        final_top_k=args.final_top_k,
        save_recommendations=not args.dry_run,
    )
    context.recommendations = recommendations
    context.rerank_source = source
    message = (
        f"Reranked run_id={ranking_run.id}; source={source}; "
        f"recommendations={len(recommendations)}; saved={not args.dry_run}."
    )
    if error_reason:
        message += f" Fallback reason: {error_reason}"
    return message


def _count_rows(store: SQLiteStore, table_name: str) -> int:
    with store.connect() as connection:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _count_zotero_papers(store: SQLiteStore) -> int:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM user_library_papers WHERE source = ?",
            (PaperSource.ZOTERO.value,),
        ).fetchone()
    return int(row["count"])


def _count_arxiv_candidates(store: SQLiteStore) -> int:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM candidate_papers WHERE source = ?",
            (PaperSource.ARXIV.value,),
        ).fetchone()
    return int(row["count"])


def _print_recommendations(recommendations: list[FinalRecommendation]) -> None:
    print("\nTop Recommendations")
    if not recommendations:
        print("No recommendations generated.")
        return
    for index, item in enumerate(recommendations, start=1):
        score = f"{item.llm_score:.3f}" if item.llm_score is not None else "fallback"
        print(f"{index}. {item.card.title} [score={score}, priority={item.card.reading_priority}]")
        print(f"   Summary: {item.card.one_sentence_summary}")
        print(f"   Why: {item.card.why_recommended}")


def _print_summary(results: list[StepResult]) -> None:
    print("\nWorkflow Summary")
    for result in results:
        print(f"- {result.name}: {result.status} ({result.elapsed_seconds:.1f}s) - {result.message}")


def _parse_categories(value: str) -> list[str]:
    return [category.strip() for category in value.split(",") if category.strip()]


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the full daily academic paper recommendation workflow.")
    parser.add_argument("--zotero-max-items", type=int, default=settings.zotero_max_items, help="Maximum Zotero items to sync.")
    parser.add_argument("--skip-zotero", action="store_true", help="Reuse local Zotero data without remote sync.")
    parser.add_argument(
        "--profile-max-papers",
        type=int,
        default=settings.profile_max_papers,
        help="Maximum Zotero papers used for profile.",
    )
    parser.add_argument("--top-keywords", type=int, default=settings.profile_top_keywords, help="Number of profile keywords to keep.")
    parser.add_argument(
        "--representative-count",
        type=int,
        default=settings.profile_representative_count,
        help="Representative papers kept in profile.",
    )
    parser.add_argument(
        "--profile-mode",
        choices=["local", "hybrid", "llm"],
        default=settings.profile_mode,
        help="Profile construction mode.",
    )
    parser.add_argument(
        "--categories",
        type=_parse_categories,
        default=settings.arxiv_categories,
        help="Comma-separated arXiv categories.",
    )
    parser.add_argument("--lookback-days", type=int, default=settings.arxiv_lookback_days)
    parser.add_argument("--arxiv-max-results", type=int, default=settings.arxiv_max_results)
    parser.add_argument("--arxiv-request-delay-seconds", type=float, default=settings.arxiv_request_delay_seconds)
    parser.add_argument("--arxiv-retries", type=int, default=settings.arxiv_num_retries)
    parser.add_argument("--skip-arxiv", action="store_true", help="Reuse local arXiv candidates without remote sync.")
    parser.add_argument(
        "--ranking-mode",
        choices=["profile", "library"],
        default=settings.ranking_mode,
        help="Local rough-ranking strategy.",
    )
    parser.add_argument("--candidate-limit", type=int, default=settings.candidate_limit)
    parser.add_argument("--library-limit", type=int, default=settings.library_limit)
    parser.add_argument("--local-top-n", type=int, default=settings.local_top_k)
    parser.add_argument("--final-top-k", type=int, default=settings.final_top_k)
    parser.add_argument(
        "--include-recommended",
        action="store_true",
        help="In profile mode, allow candidates already present in recommendation history.",
    )
    parser.add_argument(
        "--embedding-backend",
        choices=["auto", "sentence-transformers", "hashing"],
        default=settings.embedding_backend,
        help="Embedding backend for local rough ranking.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not save final recommendations.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run_daily_recommendation_workflow(args)
    except WorkflowStop as exc:
        print(f"\nDaily Recommendation Workflow: STOPPED\n{exc}")
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("\nDaily Recommendation Workflow: INTERRUPTED")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
