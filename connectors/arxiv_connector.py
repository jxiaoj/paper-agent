import argparse
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import get_settings
from memory.sqlite_store import SQLiteStore
from models.paper import Paper, PaperSource


class ArxivConnector:
    def __init__(
        self,
        categories: list[str],
        lookback_days: int = 3,
        max_results: int = 50,
        request_delay_seconds: float = 3.0,
        num_retries: int = 1,
    ) -> None:
        self.categories = [category.strip() for category in categories if category.strip()]
        if not self.categories:
            raise ValueError("At least one arXiv category is required, for example cs.AI or cs.CL.")
        self.lookback_days = max(0, lookback_days)
        self.max_results = max(1, max_results)
        self.request_delay_seconds = max(3.0, request_delay_seconds)
        self.num_retries = max(0, num_retries)

    def fetch_papers(self) -> list[Paper]:
        try:
            import arxiv
        except ImportError as exc:
            raise RuntimeError(
                "arxiv is not installed. Run `pip install -r requirements.txt` inside your virtual environment."
            ) from exc

        query = " OR ".join(f"cat:{category}" for category in self.categories)
        search = arxiv.Search(
            query=query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        client = arxiv.Client(
            page_size=min(self.max_results, 100),
            delay_seconds=self.request_delay_seconds,
            num_retries=self.num_retries,
        )
        cutoff = datetime.now(UTC) - timedelta(days=self.lookback_days)

        papers: list[Paper] = []
        try:
            for result in client.results(search):
                published = _ensure_aware_datetime(result.published)
                if self.lookback_days and published < cutoff:
                    continue
                papers.append(result_to_paper(result))
        except arxiv.HTTPError as exc:
            if exc.status == 429:
                raise RuntimeError(
                    "arXiv API rate limit reached (HTTP 429). Wait a few minutes and retry with a small "
                    "`--max-results` value; avoid running repeated collector requests in quick succession."
                ) from exc
            raise
        return papers


def result_to_paper(result: Any) -> Paper:
    published = _ensure_aware_datetime(result.published)
    arxiv_id = _extract_arxiv_id(result)
    authors = [_clean_text(author.name) for author in getattr(result, "authors", []) if _clean_text(author.name)]
    categories = [_clean_text(category) for category in getattr(result, "categories", []) if _clean_text(category)]
    updated = _ensure_aware_datetime(getattr(result, "updated", published))

    return Paper(
        title=_clean_text(result.title),
        abstract=_clean_text(result.summary) or None,
        authors=authors,
        year=published.year,
        published_date=published.date(),
        updated_date=updated.date(),
        categories=categories,
        primary_category=_clean_text(getattr(result, "primary_category", "")) or (categories[0] if categories else None),
        comment=_clean_text(getattr(result, "comment", "")) or None,
        doi=_clean_text(getattr(result, "doi", "")) or None,
        source=PaperSource.ARXIV,
        external_id=arxiv_id,
        url=getattr(result, "entry_id", None) or None,
    )


def save_arxiv_papers(
    categories: list[str] | None = None,
    lookback_days: int | None = None,
    max_results: int | None = None,
    request_delay_seconds: float | None = None,
    num_retries: int | None = None,
) -> list[Paper]:
    settings = get_settings()
    connector = ArxivConnector(
        categories=categories or settings.arxiv_categories,
        lookback_days=settings.arxiv_lookback_days if lookback_days is None else lookback_days,
        max_results=settings.arxiv_max_results if max_results is None else max_results,
        request_delay_seconds=(
            settings.arxiv_request_delay_seconds if request_delay_seconds is None else request_delay_seconds
        ),
        num_retries=settings.arxiv_num_retries if num_retries is None else num_retries,
    )
    store = SQLiteStore(settings.database_path)
    store.init_schema()

    papers = connector.fetch_papers()
    return [store.save_candidate_paper(paper) for paper in papers]


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _extract_arxiv_id(result: Any) -> str | None:
    get_short_id = getattr(result, "get_short_id", None)
    if callable(get_short_id):
        return get_short_id()

    entry_id = str(getattr(result, "entry_id", "") or "")
    match = re.search(r"abs/([^/?#]+)", entry_id)
    return match.group(1) if match else entry_id or None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Fetch recent arXiv papers and save them locally.")
    parser.add_argument(
        "--categories",
        default=",".join(settings.arxiv_categories),
        help="Comma-separated arXiv categories, for example cs.AI,cs.CL,cs.LG.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=settings.arxiv_lookback_days,
        help="Only keep papers submitted within the last N days. Use 0 to disable local date filtering.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=settings.arxiv_max_results,
        help="Maximum arXiv API results to request before local filtering.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=settings.arxiv_request_delay_seconds,
        help="Minimum delay between paginated requests or retries. Values below 3 are raised to 3.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=settings.arxiv_num_retries,
        help="Number of retries for transient arXiv API failures.",
    )
    parser.add_argument("--preview", type=int, default=5, help="Number of saved paper titles to print.")
    args = parser.parse_args()

    categories = [category.strip() for category in args.categories.split(",") if category.strip()]
    try:
        papers = save_arxiv_papers(
            categories=categories,
            lookback_days=args.lookback_days,
            max_results=args.max_results,
            request_delay_seconds=args.request_delay_seconds,
            num_retries=args.retries,
        )
    except Exception as exc:
        print(f"arXiv connector failed: {exc}")
        raise SystemExit(1) from exc

    print(f"Fetched and saved {len(papers)} arXiv papers.")
    print(f"Categories: {', '.join(categories)}")
    print(f"Lookback days: {args.lookback_days}")
    print(f"Requested API results: {args.max_results}")
    for index, paper in enumerate(papers[: args.preview], start=1):
        date_text = f" [{paper.published_date}]" if paper.published_date else ""
        print(f"{index}. {paper.title}{date_text}")


if __name__ == "__main__":
    main()
