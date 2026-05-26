import argparse
import re
from typing import Any

from app.config import get_settings
from memory.sqlite_store import SQLiteStore
from models.paper import Paper, PaperSource


class ZoteroConfigError(ValueError):
    """Raised when Zotero settings are missing or invalid."""


class ZoteroConnector:
    def __init__(
        self,
        user_id: str,
        api_key: str,
        library_type: str = "user",
    ) -> None:
        if not user_id.strip() or not api_key.strip():
            raise ZoteroConfigError(
                "Missing Zotero credentials. Set ZOTERO_USER_ID and ZOTERO_API_KEY in your local .env file."
            )
        self.user_id = user_id.strip()
        self.api_key = api_key.strip()
        self.library_type = library_type.strip() or "user"

    def fetch_papers(self, max_items: int = 50) -> list[Paper]:
        try:
            from pyzotero import zotero
        except ImportError as exc:
            raise RuntimeError(
                "pyzotero is not installed. Run `pip install -r requirements.txt` inside your virtual environment."
            ) from exc

        client = zotero.Zotero(self.user_id, self.library_type, self.api_key)
        raw_items = client.top(limit=max_items)
        return [paper for item in raw_items if (paper := item_to_paper(item)) is not None]


def item_to_paper(item: dict[str, Any]) -> Paper | None:
    data = item.get("data", {})
    if data.get("itemType") in {"attachment", "note"}:
        return None

    title = _clean_text(data.get("title", ""))
    if not title:
        return None

    abstract = _clean_text(data.get("abstractNote", "")) or None
    tags = [_clean_text(tag.get("tag", "")) for tag in data.get("tags", []) if _clean_text(tag.get("tag", ""))]
    collections = [_clean_text(collection) for collection in data.get("collections", []) if _clean_text(collection)]
    authors = _extract_authors(data.get("creators", []))
    year = _extract_year(data.get("date", ""))
    url = data.get("url") or item.get("links", {}).get("alternate", {}).get("href")

    return Paper(
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        tags=tags,
        collections=collections,
        item_type=data.get("itemType"),
        date_added=data.get("dateAdded"),
        date_modified=data.get("dateModified"),
        source=PaperSource.ZOTERO,
        external_id=data.get("key") or item.get("key"),
        url=url or None,
    )


def save_zotero_papers(max_items: int = 50) -> list[Paper]:
    settings = get_settings()
    connector = ZoteroConnector(
        user_id=settings.zotero_user_id,
        api_key=settings.zotero_api_key,
        library_type=settings.zotero_library_type,
    )
    store = SQLiteStore(settings.database_path)
    store.init_schema()

    papers = connector.fetch_papers(max_items=max_items)
    return [store.save_user_library_paper(paper) for paper in papers]


def _extract_authors(creators: list[dict[str, Any]]) -> list[str]:
    authors: list[str] = []
    for creator in creators:
        creator_type = creator.get("creatorType", "")
        if creator_type and creator_type not in {"author", "editor", "contributor"}:
            continue

        if creator.get("name"):
            authors.append(_clean_text(creator["name"]))
            continue

        full_name = " ".join(
            part for part in [_clean_text(creator.get("firstName", "")), _clean_text(creator.get("lastName", ""))] if part
        )
        if full_name:
            authors.append(full_name)
    return authors


def _extract_year(date_value: str | None) -> int | None:
    if not date_value:
        return None
    match = re.search(r"(19|20)\d{2}", date_value)
    return int(match.group(0)) if match else None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Zotero items and save them as local papers.")
    parser.add_argument("--max-items", type=int, default=50, help="Maximum number of Zotero items to fetch.")
    parser.add_argument("--preview", type=int, default=5, help="Number of saved paper titles to print.")
    args = parser.parse_args()

    try:
        papers = save_zotero_papers(max_items=args.max_items)
    except ZoteroConfigError as exc:
        print(f"Zotero connector configuration error: {exc}")
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"Zotero connector failed: {exc}")
        raise SystemExit(1) from exc

    print(f"Fetched and saved {len(papers)} Zotero papers.")
    for index, paper in enumerate(papers[: args.preview], start=1):
        year = f" ({paper.year})" if paper.year else ""
        print(f"{index}. {paper.title}{year}")


if __name__ == "__main__":
    main()
