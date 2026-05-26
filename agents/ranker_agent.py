import argparse
import hashlib
import math
from dataclasses import dataclass

from app.config import get_settings
from memory.sqlite_store import SQLiteStore
from memory.vector_store import LocalVectorStore, cosine_similarity
from models.paper import Paper, PaperSource
from models.recommendation import FeedbackType, LocalRanking
from models.user_profile import UserProfile


@dataclass
class RankedCandidate:
    paper: Paper
    local_score: float
    semantic_score: float
    keyword_bonus: float
    rank_reason: str


class RankerAgent:
    def __init__(
        self,
        vector_store: LocalVectorStore,
        top_n: int = 20,
        include_recommended: bool = False,
    ) -> None:
        self.vector_store = vector_store
        self.top_n = top_n
        self.include_recommended = include_recommended

    def rank(
        self,
        profile: UserProfile,
        candidate_papers: list[Paper],
        blocked_candidate_keys: set[str],
    ) -> list[RankedCandidate]:
        profile_text = profile_to_embedding_text(profile)
        profile_vector = self.vector_store.embed_text(profile_text)

        filtered_candidates = [
            paper for paper in candidate_papers if self.include_recommended or _paper_key(paper) not in blocked_candidate_keys
        ]
        if not filtered_candidates:
            return []

        candidate_texts = [candidate_to_embedding_text(paper) for paper in filtered_candidates]
        candidate_vectors = self.vector_store.embed_texts(candidate_texts)

        ranked: list[RankedCandidate] = []
        for paper, vector in zip(filtered_candidates, candidate_vectors, strict=True):
            semantic_score = cosine_similarity(profile_vector, vector)
            keyword_bonus, matched_keywords = _keyword_bonus(profile, paper)
            local_score = semantic_score + keyword_bonus
            reason_parts = [
                f"semantic={semantic_score:.3f}",
                f"keyword_bonus={keyword_bonus:.3f}",
            ]
            if matched_keywords:
                reason_parts.append("matched=" + ", ".join(matched_keywords[:5]))
            ranked.append(
                RankedCandidate(
                    paper=paper,
                    local_score=local_score,
                    semantic_score=semantic_score,
                    keyword_bonus=keyword_bonus,
                    rank_reason="; ".join(reason_parts),
                )
            )

        ranked.sort(key=lambda item: item.local_score, reverse=True)
        return ranked[: self.top_n]


class LibraryContentRanker:
    def __init__(self, store: SQLiteStore, vector_store: LocalVectorStore, top_n: int = 20) -> None:
        self.store = store
        self.vector_store = vector_store
        self.top_n = top_n

    def rank(self, library_papers: list[Paper], candidate_papers: list[Paper]) -> list[RankedCandidate]:
        if not library_papers or not candidate_papers:
            return []

        weights = time_decay_weights(len(library_papers))
        library_vectors = self._cached_embeddings(library_papers, scope="zotero")
        candidate_vectors = self._cached_embeddings(candidate_papers, scope="arxiv")
        ranked: list[RankedCandidate] = []

        for candidate, candidate_vector in zip(candidate_papers, candidate_vectors, strict=True):
            similarities = [
                cosine_similarity(candidate_vector, library_vector) for library_vector in library_vectors
            ]
            score = sum(similarity * weight for similarity, weight in zip(similarities, weights, strict=True))
            top_index = max(range(len(similarities)), key=similarities.__getitem__)
            top_paper = library_papers[top_index]
            ranked.append(
                RankedCandidate(
                    paper=candidate,
                    local_score=score,
                    semantic_score=score,
                    keyword_bonus=0.0,
                    rank_reason=(
                        f"library_weighted_abstract_similarity={score:.3f}; "
                        f"closest_zotero_paper={top_paper.title}"
                    ),
                )
            )

        ranked.sort(key=lambda item: item.local_score, reverse=True)
        return ranked[: self.top_n]

    def _cached_embeddings(self, papers: list[Paper], scope: str) -> list[list[float]]:
        vectors: list[list[float] | None] = [None] * len(papers)
        missing_indexes: list[int] = []
        missing_texts: list[str] = []
        model_name = self.vector_store.cache_model_name

        for index, paper in enumerate(papers):
            if paper.id is None or not paper.abstract:
                continue
            content_hash = _content_hash(paper.abstract)
            if scope == "zotero":
                vector = self.store.get_user_zotero_paper_embedding(paper.id, model_name, content_hash)
            else:
                vector = self.store.get_arxiv_paper_embedding(paper.id, model_name, content_hash)
            if vector is not None:
                vectors[index] = vector
            else:
                missing_indexes.append(index)
                missing_texts.append(paper.abstract)

        if missing_texts:
            generated = self.vector_store.embed_texts(missing_texts)
            for index, vector in zip(missing_indexes, generated, strict=True):
                paper = papers[index]
                content_hash = _content_hash(paper.abstract or "")
                if scope == "zotero":
                    self.store.save_user_zotero_paper_embedding(paper.id, model_name, content_hash, vector)
                else:
                    self.store.save_arxiv_paper_embedding(paper.id, model_name, content_hash, vector)
                vectors[index] = vector

        return [vector for vector in vectors if vector is not None]


def run_local_ranking(
    candidate_limit: int = 200,
    library_limit: int = 500,
    top_n: int | None = None,
    ranking_mode: str = "profile",
    include_recommended: bool = False,
    save_local_rankings: bool = True,
    embedding_backend: str = "auto",
) -> tuple[list[RankedCandidate], str]:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.init_schema()

    vector_store = LocalVectorStore(
        model_name=settings.embedding_model_name,
        backend=embedding_backend,
    )
    if ranking_mode == "library":
        library_papers = store.get_zotero_papers_with_abstract_by_date_added(limit=library_limit)
        candidate_papers = store.get_arxiv_candidates_with_abstract(limit=candidate_limit)
        if not library_papers:
            raise RuntimeError("No Zotero papers with abstracts found for library content ranking.")
        if not candidate_papers:
            raise RuntimeError("No arXiv candidate papers with abstracts found for library content ranking.")
        ranker = LibraryContentRanker(store=store, vector_store=vector_store, top_n=top_n or settings.local_top_k)
        ranked = ranker.rank(library_papers=library_papers, candidate_papers=candidate_papers)
    else:
        profile = store.get_latest_user_profile()
        if profile is None:
            raise RuntimeError("No user profile found. Run `python -m agents.profile_agent --profile-mode hybrid` first.")

        candidate_papers = store.get_candidate_papers(limit=candidate_limit)
        if not candidate_papers:
            raise RuntimeError("No candidate papers found. Run `python -m connectors.arxiv_connector` first.")

        blocked_keys = set()
        if not include_recommended:
            blocked_keys.update(store.get_recommended_candidate_keys())
        blocked_keys.update(
            store.get_feedback_candidate_keys({FeedbackType.DISLIKE, FeedbackType.NOT_RELEVANT})
        )
        ranker = RankerAgent(
            vector_store=vector_store,
            top_n=top_n or settings.local_top_k,
            include_recommended=include_recommended,
        )
        ranked = ranker.rank(
            profile=profile,
            candidate_papers=candidate_papers,
            blocked_candidate_keys=blocked_keys,
        )

    if save_local_rankings:
        for index, item in enumerate(ranked, start=1):
            store.save_local_ranking(
                LocalRanking(
                    paper_id=item.paper.id,
                    ranking_method=ranking_mode,
                    local_score=item.local_score,
                    rank=index,
                    reason=item.rank_reason,
                )
            )

    return ranked, vector_store.active_backend


def time_decay_weights(corpus_size: int) -> list[float]:
    if corpus_size <= 0:
        return []
    raw_weights = [1.0 / (1.0 + math.log10(index + 1)) for index in range(corpus_size)]
    total = sum(raw_weights)
    return [weight / total for weight in raw_weights]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def profile_to_embedding_text(profile: UserProfile) -> str:
    representative_titles = [
        paper.get("title", "") for paper in profile.representative_papers if paper.get("title")
    ]
    sections = [
        "Research summary:\n" + profile.research_summary,
        "Explicit interests:\n" + ", ".join(profile.explicit_interests),
        "Inferred keywords:\n" + ", ".join(profile.inferred_keywords),
        "Representative papers:\n" + "\n".join(representative_titles),
    ]
    return "\n\n".join(section for section in sections if section.strip())


def candidate_to_embedding_text(paper: Paper) -> str:
    sections = [
        paper.title,
        paper.abstract or "",
        "Categories: " + ", ".join(paper.categories),
        "Primary category: " + (paper.primary_category or ""),
    ]
    return "\n".join(section for section in sections if section.strip())


def _keyword_bonus(profile: UserProfile, paper: Paper) -> tuple[float, list[str]]:
    text = candidate_to_embedding_text(paper).lower()
    matched: list[str] = []
    bonus = 0.0

    for interest in profile.explicit_interests:
        normalized = interest.lower().strip()
        if normalized and normalized in text:
            bonus += 0.08
            matched.append(interest)

    for keyword in profile.inferred_keywords:
        normalized = keyword.lower().strip()
        if normalized and normalized in text:
            bonus += 0.03
            matched.append(keyword)

    return min(bonus, 0.45), matched


def _paper_key(paper: Paper) -> str:
    if not paper.external_id:
        return ""
    return f"{paper.source.value}:{paper.external_id}"


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run local embedding-based rough ranking over candidate papers.")
    parser.add_argument("--candidate-limit", type=int, default=200, help="Maximum candidate papers to rank.")
    parser.add_argument("--library-limit", type=int, default=500, help="Maximum Zotero papers considered in library mode.")
    parser.add_argument("--top-n", type=int, default=settings.local_top_k, help="Number of local recommendations to keep.")
    parser.add_argument(
        "--ranking-mode",
        choices=["profile", "library"],
        default="profile",
        help="Rank by the user profile or by time-weighted Zotero abstract similarities.",
    )
    parser.add_argument(
        "--include-recommended",
        action="store_true",
        help="Do not filter papers already present in recommendations.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Rank papers without saving recommendations.")
    parser.add_argument(
        "--embedding-backend",
        choices=["auto", "sentence-transformers", "hashing"],
        default="auto",
        help="Embedding backend. auto tries sentence-transformers and falls back to local hashing.",
    )
    parser.add_argument(
        "--preview-profile-text",
        action="store_true",
        help="Print the profile embedding text and exit.",
    )
    args = parser.parse_args()

    if args.preview_profile_text:
        store = SQLiteStore(settings.database_path)
        store.init_schema()
        profile = store.get_latest_user_profile()
        if profile is None:
            raise SystemExit("No user profile found.")
        print(profile_to_embedding_text(profile))
        return

    ranked, backend = run_local_ranking(
        candidate_limit=args.candidate_limit,
        library_limit=args.library_limit,
        top_n=args.top_n,
        ranking_mode=args.ranking_mode,
        include_recommended=args.include_recommended,
        save_local_rankings=not args.dry_run,
        embedding_backend=args.embedding_backend,
    )

    print("Ranker Agent: OK")
    print(f"Embedding backend: {backend}")
    print(f"Ranking mode: {args.ranking_mode}")
    print(f"Ranked candidates: {len(ranked)}")
    print(f"Saved local rankings: {not args.dry_run}")
    for index, item in enumerate(ranked, start=1):
        print(
            f"{index}. {item.paper.title} "
            f"[local_score={item.local_score:.3f}, semantic={item.semantic_score:.3f}, bonus={item.keyword_bonus:.3f}]"
        )


if __name__ == "__main__":
    main()
