import json

from agents.ranker_agent import RankedCandidate
from models.user_profile import UserProfile


RERANK_SYSTEM_PROMPT = """You are an academic paper recommendation reranker.
Select the papers that best match the compact user research profile.
Return strict JSON only. Do not add Markdown fences or explanatory text.
Use only candidate external_id values supplied in the request."""


def build_rerank_messages(
    profile: UserProfile,
    ranked_candidates: list[RankedCandidate],
    top_k: int,
) -> list[dict[str, str]]:
    payload = {
        "task": f"Select and explain the best {top_k} papers for this user.",
        "privacy_note": "This is a compressed local profile, not the user's full Zotero library.",
        "user_profile": {
            "research_summary": profile.research_summary,
            "explicit_interests": profile.explicit_interests,
            "inferred_keywords": profile.inferred_keywords,
        },
        "candidates": [
            {
                "external_id": item.paper.external_id,
                "title": item.paper.title,
                "authors": item.paper.authors[:8],
                "abstract": (item.paper.abstract or "")[:1500],
                "categories": item.paper.categories,
                "published_date": item.paper.published_date.isoformat() if item.paper.published_date else None,
                "url": str(item.paper.url) if item.paper.url else None,
                "local_score": round(item.local_score, 4),
            }
            for item in ranked_candidates
        ],
        "output_schema": {
            "selected_papers": [
                {
                    "external_id": "must exactly match a candidate external_id",
                    "rerank_score": "number from 0 to 1",
                    "one_sentence_summary": "one concise sentence",
                    "why_recommended": "specific explanation tied to user interests",
                    "related_user_interests": ["research interest phrase"],
                    "reading_priority": "high, medium, or low",
                }
            ]
        },
        "constraints": [
            f"Return at most {top_k} selected_papers.",
            "Do not recommend papers not present in candidates.",
            "Ground reasons in candidate metadata and the compressed user profile.",
        ],
    }
    return [
        {"role": "system", "content": RERANK_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
