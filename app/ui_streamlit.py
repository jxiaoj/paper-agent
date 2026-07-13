import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.profile_agent import build_and_save_profile
from app.config import get_settings
from connectors.zotero_connector import ZoteroConfigError, save_zotero_collections
from memory.sqlite_store import SQLiteStore
from models.paper import ZoteroCollection
from models.recommendation import Feedback, FeedbackType, Recommendation, RecommendationCard
from workflows.daily_recommendation_workflow import run_daily_recommendation_workflow


ENV_PATH = Path(".env")


def main() -> None:
    st.set_page_config(
        page_title="Paper Agent",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Paper Agent")

    page = st.sidebar.radio(
        "导航",
        ["配置", "用户画像", "运行推荐", "今日推荐"],
        label_visibility="collapsed",
    )

    if page == "配置":
        render_config_page()
    elif page == "用户画像":
        render_profile_page()
    elif page == "运行推荐":
        render_workflow_page()
    else:
        render_recommendations_page()


def render_config_page() -> None:
    st.subheader("配置")
    settings = get_settings()
    env_values = read_env_file(ENV_PATH)
    store = get_store()
    store.init_schema()
    collections = store.list_zotero_collections()
    collection_counts = store.count_zotero_papers_by_collection()

    if st.button("刷新 Zotero 文件夹列表"):
        with st.spinner("正在同步 Zotero 文件夹..."):
            try:
                collections = save_zotero_collections()
            except ZoteroConfigError as exc:
                st.error(f"Zotero 配置错误：{exc}")
            except Exception as exc:
                st.error(f"同步 Zotero 文件夹失败：{exc}")
            else:
                get_settings.cache_clear()
                st.success(f"已同步 {len(collections)} 个 Zotero 文件夹。")
                st.rerun()

    with st.container():
        col_llm, col_zotero = st.columns(2)
        with col_llm:
            st.markdown("#### LLM")
            llm_base_url = st.text_input(
                "LLM Base URL",
                value=env_values.get("LLM_API_BASE_URL", settings.llm_api_base_url),
            )
            llm_model = st.text_input(
                "LLM Model",
                value=env_values.get("LLM_MODEL_NAME", settings.llm_model_name),
            )
            llm_api_key = st.text_input(
                "LLM API Key",
                value="",
                type="password",
                placeholder="留空则保留已有密钥" if settings.has_llm_credentials else "请输入 LLM API Key",
            )

        with col_zotero:
            st.markdown("#### Zotero")
            zotero_user_id = st.text_input(
                "Zotero User ID",
                value=env_values.get("ZOTERO_USER_ID", settings.zotero_user_id),
            )
            zotero_api_key = st.text_input(
                "Zotero API Key",
                value="",
                type="password",
                placeholder="留空则保留已有密钥" if settings.has_zotero_credentials else "请输入 Zotero API Key",
            )
            zotero_library_type = st.selectbox(
                "Zotero Library Type",
                ["user", "group"],
                index=0 if env_values.get("ZOTERO_LIBRARY_TYPE", settings.zotero_library_type) != "group" else 1,
            )
            zotero_scope = st.selectbox(
                "Zotero 分析范围",
                ["all", "selected"],
                format_func=lambda value: "使用全部 Zotero 文献" if value == "all" else "只使用选中文件夹",
                index=0 if env_values.get("ZOTERO_ANALYSIS_SCOPE", settings.zotero_analysis_scope) != "selected" else 1,
            )
            selected_collection_keys: list[str] = []
            if zotero_scope == "selected":
                if not collections:
                    st.warning("还没有 Zotero 文件夹列表。请先点击上方“刷新 Zotero 文件夹列表”。")
                collection_options = build_collection_options(collections, collection_counts)
                selected_labels = st.multiselect(
                    "选择 Zotero 文件夹",
                    options=list(collection_options.keys()),
                    default=[
                        label
                        for label, key in collection_options.items()
                        if key in settings.zotero_selected_collections
                    ],
                )
                selected_collection_keys = [collection_options[label] for label in selected_labels]

        col_interest, col_arxiv = st.columns(2)
        with col_interest:
            st.markdown("#### 研究兴趣")
            interests = st.text_area(
                "研究兴趣",
                value=env_values.get("USER_INTEREST_KEYWORDS", ",".join(settings.user_interest_keywords)),
                height=90,
                help="逗号分隔，例如 large language models,AI agents,model distillation",
            )
        with col_arxiv:
            st.markdown("#### 数据源")
            categories = st.text_input(
                "arXiv Categories",
                value=env_values.get("ARXIV_CATEGORIES", ",".join(settings.arxiv_categories)),
            )
            lookback_days = st.number_input(
                "arXiv Lookback Days",
                min_value=0,
                value=int(env_values.get("ARXIV_LOOKBACK_DAYS", settings.arxiv_lookback_days)),
            )
            max_results = st.number_input(
                "arXiv Max Results",
                min_value=1,
                value=int(env_values.get("ARXIV_MAX_RESULTS", settings.arxiv_max_results)),
            )

        submitted = st.button("保存配置", type="primary")

    if submitted:
        if zotero_scope == "selected" and not selected_collection_keys:
            st.error("请选择至少一个 Zotero 文件夹，或切换为使用全部 Zotero 文献。")
            return
        updates = {
            "LLM_API_BASE_URL": llm_base_url.strip(),
            "LLM_MODEL_NAME": llm_model.strip(),
            "ZOTERO_USER_ID": zotero_user_id.strip(),
            "ZOTERO_LIBRARY_TYPE": zotero_library_type,
            "ZOTERO_ANALYSIS_SCOPE": zotero_scope,
            "ZOTERO_SELECTED_COLLECTIONS": ",".join(selected_collection_keys),
            "USER_INTEREST_KEYWORDS": compact_csv(interests),
            "ARXIV_CATEGORIES": compact_csv(categories),
            "ARXIV_LOOKBACK_DAYS": str(int(lookback_days)),
            "ARXIV_MAX_RESULTS": str(int(max_results)),
        }
        if llm_api_key.strip():
            updates["LLM_API_KEY"] = llm_api_key.strip()
        if zotero_api_key.strip():
            updates["ZOTERO_API_KEY"] = zotero_api_key.strip()
        write_env_file(ENV_PATH, updates)
        get_settings.cache_clear()
        st.success("配置已保存。")


def render_profile_page() -> None:
    st.subheader("用户画像")
    settings = get_settings()
    store = get_store()
    store.init_schema()

    profile = store.get_latest_user_profile()
    if profile is None:
        st.info("还没有用户画像。可以先同步 Zotero，然后在这里构建画像。")
    else:
        col_meta, col_summary = st.columns([1, 2])
        with col_meta:
            st.metric("画像 ID", profile.id or 0)
            st.metric("Zotero 文献数", profile.zotero_paper_count)
            st.write("显式兴趣")
            st.write(", ".join(profile.explicit_interests) or "未配置")
        with col_summary:
            st.write("研究总结")
            st.write(profile.research_summary or "暂无总结")
            st.write("推断关键词")
            st.write(", ".join(profile.inferred_keywords) or "暂无关键词")

        st.write("代表性论文")
        for paper in profile.representative_papers:
            year = f" ({paper.get('year')})" if paper.get("year") else ""
            st.write(f"- {paper.get('title', '(untitled)')}{year}")

    st.divider()
    submitted = st.button("重新构建用户画像", type="primary")

    if submitted:
        with st.spinner("正在构建用户画像..."):
            profile = build_and_save_profile(
                max_papers=settings.profile_max_papers,
                top_keywords=settings.profile_top_keywords,
                representative_count=settings.profile_representative_count,
                profile_mode=settings.profile_mode,
            )
        st.success(f"已保存用户画像：id={profile.id}")
        st.rerun()


def render_workflow_page() -> None:
    st.subheader("运行推荐")
    settings = get_settings()

    with st.form("workflow_form"):
        col_sync, col_option = st.columns(2)
        with col_sync:
            skip_zotero = st.checkbox("跳过 Zotero 同步", value=False)
            skip_arxiv = st.checkbox("跳过 arXiv 拉取", value=False)
        with col_option:
            dry_run = st.checkbox("Dry Run，不保存最终推荐", value=False)

        submitted = st.form_submit_button("运行完整推荐 workflow", type="primary")

    if submitted:
        args = argparse.Namespace(
            zotero_max_items=settings.zotero_max_items,
            skip_zotero=skip_zotero,
            profile_max_papers=settings.profile_max_papers,
            top_keywords=settings.profile_top_keywords,
            representative_count=settings.profile_representative_count,
            profile_mode=settings.profile_mode,
            categories=settings.arxiv_categories,
            lookback_days=settings.arxiv_lookback_days,
            arxiv_max_results=settings.arxiv_max_results,
            arxiv_request_delay_seconds=settings.arxiv_request_delay_seconds,
            arxiv_retries=settings.arxiv_num_retries,
            skip_arxiv=skip_arxiv,
            ranking_mode=settings.ranking_mode,
            candidate_limit=settings.candidate_limit,
            library_limit=settings.library_limit,
            local_top_n=settings.local_top_k,
            final_top_k=settings.final_top_k,
            include_recommended=False,
            embedding_backend=settings.embedding_backend,
            dry_run=dry_run,
        )
        log_buffer = io.StringIO()
        with st.spinner("正在运行推荐 workflow..."):
            try:
                with contextlib.redirect_stdout(log_buffer):
                    recommendations = run_daily_recommendation_workflow(args)
            except Exception as exc:
                st.session_state["workflow_log"] = log_buffer.getvalue()
                st.error(f"Workflow 运行失败：{exc}")
            else:
                st.session_state["workflow_log"] = log_buffer.getvalue()
                st.success(f"Workflow 完成，生成 {len(recommendations)} 条推荐。")
                render_recommendation_cards(recommendations, show_feedback=False)

    if st.session_state.get("workflow_log"):
        with st.expander("Workflow 日志", expanded=True):
            st.code(st.session_state["workflow_log"], language="text")


def render_recommendations_page() -> None:
    st.subheader("今日推荐")
    store = get_store()
    store.init_schema()

    runs = store.list_recommendation_runs(limit=50)
    if not runs:
        st.info("还没有最终推荐。请先在运行推荐页执行 workflow。")
        return

    run_labels = [
        (
            f"Run {run.id} | {run.ranking_method} | {run.result_count} rough results | "
            f"{run.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        for run in runs
    ]
    selected_label = st.selectbox("推荐批次", run_labels, index=0)
    selected_run = runs[run_labels.index(selected_label)]
    recommendations = store.list_recommendations_for_run(selected_run.id, limit=100)

    st.caption(
        f"当前只展示 Run {selected_run.id} 的最终推荐；卡片标题编号是页面顺序，"
        "Original Rank 是该批次保存时的原始推荐排名。"
    )
    render_saved_recommendations(store, recommendations)


def render_recommendation_cards(
    recommendations: list[Any],
    show_feedback: bool,
    store: SQLiteStore | None = None,
) -> None:
    for index, item in enumerate(recommendations, start=1):
        recommendation = getattr(item, "card", None)
        card = recommendation if isinstance(recommendation, RecommendationCard) else None
        candidate = getattr(item, "candidate", None)
        paper = getattr(candidate, "paper", None)
        local_score = getattr(candidate, "local_score", None)
        llm_score = getattr(item, "llm_score", None)
        with st.container(border=True):
            render_card_content(
                title=card.title if card else getattr(paper, "title", "(untitled)"),
                authors=card.authors if card else getattr(paper, "authors", []),
                summary=card.one_sentence_summary if card else "",
                why=card.why_recommended if card else "",
                priority=card.reading_priority if card else "medium",
                url=str(card.arxiv_url) if card and card.arxiv_url else str(getattr(paper, "url", "") or ""),
                local_score=local_score,
                llm_score=llm_score,
                rank=index,
                ranking_run_id=None,
            )


def render_saved_recommendations(store: SQLiteStore, recommendations: list[Recommendation]) -> None:
    for display_rank, recommendation in enumerate(recommendations, start=1):
        card = coerce_card(recommendation.card)
        paper = store.get_candidate_paper(recommendation.paper_id) if recommendation.paper_id else None
        with st.container(border=True):
            render_card_content(
                title=card.title if card else (paper.title if paper else "(untitled)"),
                authors=card.authors if card else (paper.authors if paper else []),
                summary=card.one_sentence_summary if card else "",
                why=card.why_recommended if card else recommendation.reason,
                priority=card.reading_priority if card else "medium",
                url=str(card.arxiv_url) if card and card.arxiv_url else str(paper.url if paper and paper.url else ""),
                local_score=recommendation.local_score,
                llm_score=recommendation.llm_score,
                rank=display_rank,
                ranking_run_id=recommendation.ranking_run_id,
                original_rank=recommendation.rank,
            )
            render_feedback_controls(store, recommendation)


def render_card_content(
    title: str,
    authors: list[str],
    summary: str,
    why: str,
    priority: str,
    url: str,
    local_score: float | None,
    llm_score: float | None,
    rank: int | None,
    ranking_run_id: int | None,
    original_rank: int | None = None,
) -> None:
    heading = f"{rank}. {title}" if rank else title
    st.markdown(f"### {heading}")
    if authors:
        st.caption(", ".join(authors[:8]))
    cols = st.columns(5)
    cols[0].metric("Priority", priority)
    cols[1].metric("Local Score", f"{local_score:.3f}" if local_score is not None else "-")
    cols[2].metric("LLM Score", f"{llm_score:.3f}" if llm_score is not None else "-")
    cols[3].metric("Run ID", ranking_run_id if ranking_run_id is not None else "-")
    cols[4].metric("Original Rank", original_rank if original_rank is not None else "-")
    if summary:
        st.write(summary)
    if why:
        st.write(why)
    if url:
        st.link_button("打开论文链接", url)


def render_feedback_controls(store: SQLiteStore, recommendation: Recommendation) -> None:
    note_key = f"feedback_note_{recommendation.id}"
    note = st.text_input("反馈备注", key=note_key, placeholder="可选")
    labels = [
        ("Like", FeedbackType.LIKE),
        ("Dislike", FeedbackType.DISLIKE),
        ("Save", FeedbackType.SAVE),
    ]
    cols = st.columns(len(labels))
    for column, (label, feedback_type) in zip(cols, labels, strict=True):
        if column.button(label, key=f"feedback_{recommendation.id}_{feedback_type.value}"):
            store.save_feedback(
                Feedback(
                    recommendation_id=recommendation.id,
                    paper_id=recommendation.paper_id,
                    feedback_type=feedback_type,
                    note=note,
                )
            )
            st.success(f"已记录反馈：{feedback_type.value}")


def coerce_card(value: Any) -> RecommendationCard | None:
    if value is None:
        return None
    if isinstance(value, RecommendationCard):
        return value
    if isinstance(value, dict):
        return RecommendationCard.model_validate(value)
    return None


def get_store() -> SQLiteStore:
    return SQLiteStore(get_settings().database_path)


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = unquote_env_value(value.strip())
    return values


def write_env_file(path: Path, updates: dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    output: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            output.append(f"{key}={quote_env_value(updates[key])}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={quote_env_value(value)}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def quote_env_value(value: str) -> str:
    if any(char.isspace() for char in value) or "#" in value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def compact_csv(value: str) -> str:
    return ",".join(item.strip() for item in value.split(",") if item.strip())


def build_collection_options(
    collections: list[ZoteroCollection],
    counts: dict[str, int],
) -> dict[str, str]:
    by_key = {collection.collection_key: collection for collection in collections}

    def path_for(collection: ZoteroCollection) -> str:
        names = [collection.name]
        parent_key = collection.parent_key
        seen = {collection.collection_key}
        while parent_key and parent_key in by_key and parent_key not in seen:
            parent = by_key[parent_key]
            names.append(parent.name)
            seen.add(parent.collection_key)
            parent_key = parent.parent_key
        return " / ".join(reversed(names))

    options: dict[str, str] = {}
    sorted_collections = sorted(collections, key=lambda item: path_for(item).lower())
    for collection in sorted_collections:
        label = f"{path_for(collection)} ({counts.get(collection.collection_key, 0)} 篇)"
        if label in options:
            label = f"{label} [{collection.collection_key}]"
        options[label] = collection.collection_key
    return options


if __name__ == "__main__":
    main()
