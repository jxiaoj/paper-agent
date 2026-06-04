import argparse
import json
import re
from collections import Counter
from typing import Any

from app.config import get_settings
from memory.sqlite_store import SQLiteStore
from models.paper import Paper, PaperSource
from models.user_profile import UserProfile


STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "among",
    "and",
    "are",
    "based",
    "been",
    "between",
    "both",
    "can",
    "data",
    "deep",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "its",
    "large",
    "learning",
    "model",
    "models",
    "more",
    "new",
    "not",
    "our",
    "paper",
    "papers",
    "propose",
    "proposed",
    "results",
    "show",
    "such",
    "that",
    "the",
    "their",
    "these",
    "this",
    "through",
    "using",
    "via",
    "was",
    "we",
    "with",
}


class ProfileAgent:
    def __init__(
        self,
        explicit_interests: list[str],
        top_keywords: int = 12,
        representative_count: int = 5,
    ) -> None:
        self.explicit_interests = [interest.strip() for interest in explicit_interests if interest.strip()]
        self.top_keywords = top_keywords
        self.representative_count = representative_count

    def build_profile(self, library_papers: list[Paper], profile_mode: str = "local") -> UserProfile:
        tag_counts = self._count_tags(library_papers)
        keyword_counts = self._count_text_keywords(library_papers)
        local_keywords = self._merge_keywords(tag_counts, keyword_counts)
        representative_papers = self._select_representative_papers(library_papers, local_keywords)
        local_summary = self._build_rule_based_summary(
            library_papers=library_papers,
            inferred_keywords=local_keywords,
            representative_papers=representative_papers,
        )

        inferred_keywords = local_keywords
        research_summary = local_summary
        if profile_mode in {"llm", "hybrid"}:
            llm_profile = self._try_llm_profile(
                library_papers=library_papers,
                local_keywords=local_keywords,
                representative_papers=representative_papers,
                fallback_summary=local_summary,
            )
            if llm_profile:
                inferred_keywords = _dedupe_keep_order(
                    llm_profile.get("inferred_keywords", []) + ([] if profile_mode == "llm" else local_keywords)
                )[: self.top_keywords]
                research_summary = llm_profile.get("research_summary") or local_summary

        return UserProfile(
            explicit_interests=self.explicit_interests,
            inferred_keywords=inferred_keywords,
            representative_papers=representative_papers,
            research_summary=research_summary,
            zotero_paper_count=len(library_papers),
        )

    def _count_tags(self, papers: list[Paper]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for paper in papers:
            counter.update(_normalize_keyword(tag) for tag in paper.tags if _normalize_keyword(tag))
        return counter

    def _count_text_keywords(self, papers: list[Paper]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for paper in papers:
            text = f"{paper.title} {paper.abstract or ''}"
            tokens = [
                token
                for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
                if token not in STOPWORDS and len(token) >= 3
            ]
            counter.update(tokens)
            counter.update(_extract_phrases(text))
        return counter

    def _merge_keywords(self, tag_counts: Counter[str], keyword_counts: Counter[str]) -> list[str]:
        weighted: Counter[str] = Counter()
        for keyword, count in keyword_counts.items():
            weighted[keyword] += count
        for tag, count in tag_counts.items():
            weighted[tag] += count * 3
        for interest in self.explicit_interests:
            normalized = _normalize_keyword(interest)
            if normalized:
                weighted[normalized] += 5
        return [keyword for keyword, _ in weighted.most_common(self.top_keywords)]

    def _select_representative_papers(
        self,
        papers: list[Paper],
        inferred_keywords: list[str],
    ) -> list[dict[str, str]]:
        scored: list[tuple[float, Paper]] = []
        signals = [signal.lower() for signal in self.explicit_interests + inferred_keywords if signal]
        for paper in papers:
            text = paper.searchable_text.lower()
            score = sum(1.0 for signal in signals if signal in text)
            score += min(len(paper.tags), 5) * 0.25
            if paper.abstract:
                score += 0.5
            if paper.year:
                score += paper.year / 10000
            scored.append((score, paper))

        scored.sort(key=lambda item: item[0], reverse=True)
        representatives: list[dict[str, str]] = []
        for _, paper in scored[: self.representative_count]:
            representatives.append(
                {
                    "title": paper.title,
                    "year": str(paper.year or ""),
                    "source": paper.source.value,
                    "external_id": paper.external_id or "",
                }
            )
        return representatives

    def _build_rule_based_summary(
        self,
        library_papers: list[Paper],
        inferred_keywords: list[str],
        representative_papers: list[dict[str, str]],
    ) -> str:
        interests = ", ".join(self.explicit_interests) or "not explicitly configured"
        keywords = ", ".join(inferred_keywords[:8]) or "no strong local keywords yet"
        top_titles = "; ".join(paper["title"] for paper in representative_papers[:3]) or "no representative papers yet"
        return (
            f"The user's explicit interests are {interests}. "
            f"Based on {len(library_papers)} Zotero library papers, the strongest local research signals are {keywords}. "
            f"Representative papers include: {top_titles}."
        )

    def _try_llm_profile(
        self,
        library_papers: list[Paper],
        local_keywords: list[str],
        representative_papers: list[dict[str, str]],
        fallback_summary: str,
    ) -> dict[str, Any] | None:
        settings = get_settings()
        if not settings.has_llm_credentials:
            return None
        try:
            from openai import OpenAI
        except ImportError:
            return None

        try:
            client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_base_url)
            response = client.chat.completions.create(
                model=settings.llm_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a research-profile agent. Build a compact academic interest profile from local "
                            "Zotero-derived signals. Return strict JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": "Infer the user's research profile.",
                                "output_schema": {
                                    "inferred_keywords": "array of 8-12 concise research keywords or phrases",
                                    "research_summary": "3 concise sentences describing the user's research interests",
                                },
                                "constraints": [
                                    "Use only the provided local signals.",
                                    "Do not invent publications, affiliations, or private facts.",
                                    "Prefer research topics over generic words.",
                                    "Return valid JSON with exactly inferred_keywords and research_summary.",
                                ],
                                "explicit_interests": self.explicit_interests,
                                "local_rule_keywords": local_keywords,
                                "representative_papers": self._llm_paper_context(library_papers, representative_papers),
                                "fallback_summary": fallback_summary,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            return _parse_llm_profile_json(content or "")
        except Exception:
            return None

    def _llm_paper_context(
        self,
        library_papers: list[Paper],
        representative_papers: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        by_external_id = {paper.external_id: paper for paper in library_papers if paper.external_id}
        context: list[dict[str, Any]] = []
        for representative in representative_papers:
            paper = by_external_id.get(representative.get("external_id", ""))
            if not paper:
                continue
            context.append(
                {
                    "title": paper.title,
                    "year": paper.year,
                    "tags": paper.tags[:8],
                    "abstract_snippet": (paper.abstract or "")[:700],
                }
            )
        return context


def build_and_save_profile(
    max_papers: int = 200,
    top_keywords: int = 12,
    representative_count: int = 5,
    profile_mode: str = "local",
) -> UserProfile:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.init_schema()
    collection_keys = settings.active_zotero_collection_keys
    if collection_keys == []:
        raise RuntimeError("ZOTERO_ANALYSIS_SCOPE=selected but ZOTERO_SELECTED_COLLECTIONS is empty.")
    if collection_keys is not None:
        collection_keys = store.expand_zotero_collection_keys(collection_keys)
    papers = store.get_user_library_papers(
        source=PaperSource.ZOTERO,
        limit=max_papers,
        collection_keys=collection_keys,
    )
    if collection_keys is not None and not papers:
        raise RuntimeError("Selected Zotero collections contain no papers for profile building.")

    agent = ProfileAgent(
        explicit_interests=settings.user_interest_keywords,
        top_keywords=top_keywords,
        representative_count=representative_count,
    )
    profile = agent.build_profile(papers, profile_mode=profile_mode)
    return store.save_user_profile(profile)


def _extract_phrases(text: str) -> list[str]:
    lowered = text.lower()
    phrases = []
    for pattern in [
        r"large language models?",
        r"instruction[- ]following",
        r"chain[- ]of[- ]thought",
        r"retrieval[- ]augmented generation",
        r"ai agents?",
        r"language agents?",
        r"knowledge fusion",
        r"model distillation",
        r"human alignment",
    ]:
        if re.search(pattern, lowered):
            phrases.append(pattern.replace("?", "").replace(r"[- ]", " ").replace("\\", ""))
    return phrases


def _normalize_keyword(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.lower()).strip()
    return normalized if normalized and normalized not in STOPWORDS else ""


def _parse_llm_profile_json(content: str) -> dict[str, Any] | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(0)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    keywords = payload.get("inferred_keywords")
    summary = payload.get("research_summary")
    if not isinstance(keywords, list) or not isinstance(summary, str):
        return None
    normalized_keywords = [_normalize_keyword(str(keyword)) for keyword in keywords]
    return {
        "inferred_keywords": [keyword for keyword in normalized_keywords if keyword],
        "research_summary": summary.strip(),
    }


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = _normalize_keyword(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local research profile from Zotero library papers.")
    parser.add_argument("--max-papers", type=int, default=200, help="Maximum Zotero library papers to profile.")
    parser.add_argument("--top-keywords", type=int, default=12, help="Number of inferred keywords to keep.")
    parser.add_argument(
        "--representative-count",
        type=int,
        default=5,
        help="Number of representative library papers to keep in the profile.",
    )
    parser.add_argument(
        "--profile-mode",
        choices=["local", "llm", "hybrid"],
        default="local",
        help="Use local rules only, LLM-structured profile only, or a hybrid LLM plus local fallback profile.",
    )
    parser.add_argument(
        "--use-llm-summary",
        action="store_true",
        help="Deprecated alias for --profile-mode hybrid.",
    )
    args = parser.parse_args()

    profile = build_and_save_profile(
        max_papers=args.max_papers,
        top_keywords=args.top_keywords,
        representative_count=args.representative_count,
        profile_mode="hybrid" if args.use_llm_summary else args.profile_mode,
    )

    print("Profile Agent: OK")
    print(f"Saved profile id: {profile.id}")
    print(f"Zotero papers analyzed: {profile.zotero_paper_count}")
    print(f"Profile mode: {'hybrid' if args.use_llm_summary else args.profile_mode}")
    print(f"Explicit interests: {', '.join(profile.explicit_interests) or '(none configured)'}")
    print(f"Inferred keywords: {', '.join(profile.inferred_keywords) or '(none)'}")
    print("Representative papers:")
    for index, paper in enumerate(profile.representative_papers, start=1):
        year = f" ({paper['year']})" if paper.get("year") else ""
        print(f"{index}. {paper['title']}{year}")
    print(f"Research summary: {profile.research_summary}")


if __name__ == "__main__":
    main()
