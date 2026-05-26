import json
import sqlite3
from pathlib import Path
from typing import Any

from models.paper import Paper, PaperSource
from models.recommendation import Feedback, FeedbackType, LocalRanking, Recommendation
from models.user_profile import UserProfile


class SQLiteStore:
    """Small sqlite3-based persistence layer for the local-first MVP."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_library_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    authors_json TEXT NOT NULL DEFAULT '[]',
                    year INTEGER,
                    published_at TEXT,
                    url TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    collections_json TEXT NOT NULL DEFAULT '[]',
                    item_type TEXT,
                    date_added TEXT,
                    date_modified TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source, external_id)
                );

                CREATE TABLE IF NOT EXISTS candidate_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    authors_json TEXT NOT NULL DEFAULT '[]',
                    year INTEGER,
                    published_at TEXT,
                    updated_at TEXT,
                    url TEXT,
                    categories_json TEXT NOT NULL DEFAULT '[]',
                    primary_category TEXT,
                    comment TEXT,
                    doi TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source, external_id)
                );

                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER,
                    recommendation_date TEXT NOT NULL,
                    local_score REAL,
                    llm_score REAL,
                    rank INTEGER,
                    reason TEXT NOT NULL DEFAULT '',
                    card_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(paper_id) REFERENCES candidate_papers(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS local_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER,
                    ranking_date TEXT NOT NULL,
                    local_score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(paper_id) REFERENCES candidate_papers(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id INTEGER,
                    paper_id INTEGER,
                    feedback_type TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL,
                    FOREIGN KEY(paper_id) REFERENCES candidate_papers(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explicit_interests_json TEXT NOT NULL DEFAULT '[]',
                    inferred_keywords_json TEXT NOT NULL DEFAULT '[]',
                    representative_papers_json TEXT NOT NULL DEFAULT '[]',
                    research_summary TEXT NOT NULL DEFAULT '',
                    zotero_paper_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_user_library_source_external_id
                    ON user_library_papers(source, external_id);
                CREATE INDEX IF NOT EXISTS idx_candidate_source_external_id
                    ON candidate_papers(source, external_id);
                CREATE INDEX IF NOT EXISTS idx_candidate_published_at
                    ON candidate_papers(published_at);
                CREATE INDEX IF NOT EXISTS idx_recommendations_date
                    ON recommendations(recommendation_date);
                CREATE INDEX IF NOT EXISTS idx_local_rankings_date
                    ON local_rankings(ranking_date);
                CREATE INDEX IF NOT EXISTS idx_feedback_paper_id
                    ON feedback(paper_id);
                """
            )
            self._migrate_user_profile_schema(connection)
            self._migrate_legacy_papers(connection)
            self._migrate_recommendation_tables(connection)
            self._migrate_rough_recommendations(connection)

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if column_name not in {column["name"] for column in columns}:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    def save_user_library_paper(self, paper: Paper) -> Paper:
        payload = paper.model_dump(mode="json")
        with self.connect() as connection:
            existing_id = self._get_existing_id(connection, "user_library_papers", paper)
            if existing_id:
                paper = paper.model_copy(update={"id": existing_id})
                self._update_user_library_paper(connection, paper)
                return paper

            cursor = connection.execute(
                """
                INSERT INTO user_library_papers (
                    source, external_id, title, abstract, authors_json, year, published_at,
                    url, tags_json, collections_json, item_type, date_added,
                    date_modified, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["source"],
                    payload["external_id"],
                    payload["title"],
                    payload["abstract"],
                    _to_json(payload["authors"]),
                    payload["year"],
                    payload["published_date"],
                    payload["url"],
                    _to_json(payload["tags"]),
                    _to_json(payload["collections"]),
                    payload["item_type"],
                    payload["date_added"],
                    payload["date_modified"],
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
            return paper.model_copy(update={"id": cursor.lastrowid})

    def save_candidate_paper(self, paper: Paper) -> Paper:
        payload = paper.model_dump(mode="json")
        with self.connect() as connection:
            existing_id = self._get_existing_id(connection, "candidate_papers", paper)
            if existing_id:
                paper = paper.model_copy(update={"id": existing_id})
                self._update_candidate_paper(connection, paper)
                return paper

            cursor = connection.execute(
                """
                INSERT INTO candidate_papers (
                    source, external_id, title, abstract, authors_json, year, published_at,
                    updated_at, url, categories_json, primary_category, comment, doi, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["source"],
                    payload["external_id"],
                    payload["title"],
                    payload["abstract"],
                    _to_json(payload["authors"]),
                    payload["year"],
                    payload["published_date"],
                    payload["updated_date"] or _date_part(payload["updated_at"]),
                    payload["url"],
                    _to_json(payload["categories"]),
                    payload["primary_category"],
                    payload["comment"],
                    payload["doi"],
                    payload["created_at"],
                ),
            )
            return paper.model_copy(update={"id": cursor.lastrowid})

    def get_user_library_papers(
        self,
        source: PaperSource | None = None,
        limit: int = 50,
    ) -> list[Paper]:
        query = "SELECT * FROM user_library_papers"
        params: list[Any] = []
        if source:
            query += " WHERE source = ?"
            params.append(source.value)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_user_library_paper_from_row(row) for row in rows]

    def get_candidate_papers(
        self,
        source: PaperSource | None = None,
        limit: int = 50,
    ) -> list[Paper]:
        query = "SELECT * FROM candidate_papers"
        params: list[Any] = []
        if source:
            query += " WHERE source = ?"
            params.append(source.value)
        query += " ORDER BY published_at DESC, created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_candidate_paper_from_row(row) for row in rows]

    def get_candidate_paper_by_external_id(self, source: PaperSource | str, external_id: str) -> Paper | None:
        source_value = source.value if isinstance(source, PaperSource) else source
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM candidate_papers WHERE source = ? AND external_id = ?",
                (source_value, external_id),
            ).fetchone()
        return _candidate_paper_from_row(row) if row else None

    # Backward-compatible wrappers for early module smoke tests.
    def save_paper(self, paper: Paper) -> Paper:
        if paper.source == PaperSource.ARXIV:
            return self.save_candidate_paper(paper)
        return self.save_user_library_paper(paper)

    def get_paper(self, paper_id: int) -> Paper | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM candidate_papers WHERE id = ?", (paper_id,)).fetchone()
            if row:
                return _candidate_paper_from_row(row)
            row = connection.execute("SELECT * FROM user_library_papers WHERE id = ?", (paper_id,)).fetchone()
        return _user_library_paper_from_row(row) if row else None

    def list_papers(self, source: PaperSource | None = None, limit: int = 50) -> list[Paper]:
        if source == PaperSource.ARXIV:
            return self.get_candidate_papers(source=source, limit=limit)
        if source == PaperSource.ZOTERO:
            return self.get_user_library_papers(source=source, limit=limit)
        return self.get_candidate_papers(limit=limit) + self.get_user_library_papers(limit=limit)

    def save_recommendation(self, recommendation: Recommendation) -> Recommendation:
        payload = recommendation.model_dump(mode="json")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO recommendations (
                    paper_id, recommendation_date, local_score, llm_score, rank,
                    reason, card_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["paper_id"],
                    payload["recommendation_date"],
                    payload["local_score"],
                    payload["llm_score"],
                    payload["rank"],
                    payload["reason"],
                    _to_json(payload["card"]) if payload["card"] else None,
                    payload["created_at"],
                ),
            )
            return recommendation.model_copy(update={"id": cursor.lastrowid})

    def list_recommendations(self, limit: int = 20) -> list[Recommendation]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM recommendations ORDER BY recommendation_date DESC, rank ASC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_recommendation_from_row(row) for row in rows]

    def save_local_ranking(self, ranking: LocalRanking) -> LocalRanking:
        payload = ranking.model_dump(mode="json")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO local_rankings (
                    paper_id, ranking_date, local_score, rank, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["paper_id"],
                    payload["ranking_date"],
                    payload["local_score"],
                    payload["rank"],
                    payload["reason"],
                    payload["created_at"],
                ),
            )
            return ranking.model_copy(update={"id": cursor.lastrowid})

    def list_local_rankings(self, limit: int = 20) -> list[LocalRanking]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM local_rankings ORDER BY ranking_date DESC, created_at DESC, rank ASC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_local_ranking_from_row(row) for row in rows]

    def save_feedback(self, feedback: Feedback) -> Feedback:
        payload = feedback.model_dump(mode="json")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO feedback (
                    recommendation_id, paper_id, feedback_type, note, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["recommendation_id"],
                    payload["paper_id"],
                    payload["feedback_type"],
                    payload["note"],
                    payload["created_at"],
                ),
            )
            return feedback.model_copy(update={"id": cursor.lastrowid})

    def list_feedback(self, limit: int = 50) -> list[Feedback]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM feedback ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_feedback_from_row(row) for row in rows]

    def get_recommended_candidate_keys(self) -> set[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT candidate_papers.source, candidate_papers.external_id
                FROM recommendations
                JOIN candidate_papers ON candidate_papers.id = recommendations.paper_id
                WHERE candidate_papers.external_id IS NOT NULL
                """
            ).fetchall()
        return {_candidate_key(row["source"], row["external_id"]) for row in rows}

    def get_feedback_candidate_keys(self, feedback_types: set[FeedbackType]) -> set[str]:
        if not feedback_types:
            return set()
        placeholders = ",".join("?" for _ in feedback_types)
        params = [feedback_type.value for feedback_type in feedback_types]
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT candidate_papers.source, candidate_papers.external_id
                FROM feedback
                JOIN candidate_papers ON candidate_papers.id = feedback.paper_id
                WHERE feedback.feedback_type IN ({placeholders})
                    AND candidate_papers.external_id IS NOT NULL
                """,
                params,
            ).fetchall()
        return {_candidate_key(row["source"], row["external_id"]) for row in rows}

    def save_user_profile(self, profile: UserProfile) -> UserProfile:
        payload = profile.model_dump(mode="json")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO user_profile (
                    explicit_interests_json, inferred_keywords_json,
                    representative_papers_json, research_summary,
                    zotero_paper_count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _to_json(payload["explicit_interests"]),
                    _to_json(payload["inferred_keywords"]),
                    _to_json(payload["representative_papers"]),
                    payload["research_summary"],
                    payload["zotero_paper_count"],
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
            return profile.model_copy(update={"id": cursor.lastrowid})

    def get_latest_user_profile(self) -> UserProfile | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM user_profile ORDER BY updated_at DESC, id DESC LIMIT 1"
            ).fetchone()
        return _profile_from_row(row) if row else None

    def _get_existing_id(self, connection: sqlite3.Connection, table_name: str, paper: Paper) -> int | None:
        if not paper.external_id:
            return None
        row = connection.execute(
            f"SELECT id FROM {table_name} WHERE source = ? AND external_id = ?",
            (paper.source.value, paper.external_id),
        ).fetchone()
        return int(row["id"]) if row else None

    def _update_user_library_paper(self, connection: sqlite3.Connection, paper: Paper) -> None:
        payload = paper.model_dump(mode="json")
        connection.execute(
            """
            UPDATE user_library_papers
            SET title = ?, abstract = ?, authors_json = ?, year = ?, published_at = ?,
                url = ?, tags_json = ?, collections_json = ?, item_type = ?,
                date_added = ?, date_modified = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload["title"],
                payload["abstract"],
                _to_json(payload["authors"]),
                payload["year"],
                payload["published_date"],
                payload["url"],
                _to_json(payload["tags"]),
                _to_json(payload["collections"]),
                payload["item_type"],
                payload["date_added"],
                payload["date_modified"],
                payload["updated_at"],
                paper.id,
            ),
        )

    def _update_candidate_paper(self, connection: sqlite3.Connection, paper: Paper) -> None:
        payload = paper.model_dump(mode="json")
        connection.execute(
            """
            UPDATE candidate_papers
            SET title = ?, abstract = ?, authors_json = ?, year = ?, published_at = ?,
                updated_at = ?, url = ?, categories_json = ?, primary_category = ?,
                comment = ?, doi = ?
            WHERE id = ?
            """,
            (
                payload["title"],
                payload["abstract"],
                _to_json(payload["authors"]),
                payload["year"],
                payload["published_date"],
                payload["updated_date"] or _date_part(payload["updated_at"]),
                payload["url"],
                _to_json(payload["categories"]),
                payload["primary_category"],
                payload["comment"],
                payload["doi"],
                paper.id,
            ),
        )

    def _migrate_legacy_papers(self, connection: sqlite3.Connection) -> None:
        if not _table_exists(connection, "papers"):
            return
        self._ensure_legacy_paper_columns(connection)
        rows = connection.execute("SELECT * FROM papers").fetchall()
        for row in rows:
            if row["source"] == PaperSource.ZOTERO.value:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO user_library_papers (
                        id, source, external_id, title, abstract, authors_json, year,
                        published_at, url, tags_json, collections_json, item_type,
                        date_added, date_modified, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["source"],
                        row["external_id"],
                        row["title"],
                        row["abstract"],
                        row["authors_json"],
                        row["year"],
                        row["published_date"],
                        row["url"],
                        row["tags_json"],
                        row["collections_json"],
                        None,
                        None,
                        None,
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
            elif row["source"] == PaperSource.ARXIV.value:
                categories = _from_json(row["categories_json"], [])
                connection.execute(
                    """
                    INSERT OR IGNORE INTO candidate_papers (
                        id, source, external_id, title, abstract, authors_json, year,
                        published_at, updated_at, url, categories_json, primary_category,
                        comment, doi, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["source"],
                        row["external_id"],
                        row["title"],
                        row["abstract"],
                        row["authors_json"],
                        row["year"],
                        row["published_date"],
                        row["updated_at"],
                        row["url"],
                        row["categories_json"],
                        categories[0] if categories else None,
                        None,
                        None,
                        row["created_at"],
                    ),
                )

    def _ensure_legacy_paper_columns(self, connection: sqlite3.Connection) -> None:
        columns = {column["name"] for column in connection.execute("PRAGMA table_info(papers)").fetchall()}
        if "collections_json" not in columns:
            connection.execute("ALTER TABLE papers ADD COLUMN collections_json TEXT NOT NULL DEFAULT '[]'")

    def _migrate_user_profile_schema(self, connection: sqlite3.Connection) -> None:
        expected_columns = [
            "id",
            "explicit_interests_json",
            "inferred_keywords_json",
            "representative_papers_json",
            "research_summary",
            "zotero_paper_count",
            "created_at",
            "updated_at",
        ]
        existing_columns = [column["name"] for column in connection.execute("PRAGMA table_info(user_profile)").fetchall()]
        if existing_columns == expected_columns:
            return

        def value_expr(preferred: str, fallback: str | None = None, default: str = "''") -> str:
            if preferred in existing_columns:
                return preferred
            if fallback and fallback in existing_columns:
                return fallback
            return default

        connection.execute(
            """
            CREATE TABLE user_profile_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                explicit_interests_json TEXT NOT NULL DEFAULT '[]',
                inferred_keywords_json TEXT NOT NULL DEFAULT '[]',
                representative_papers_json TEXT NOT NULL DEFAULT '[]',
                research_summary TEXT NOT NULL DEFAULT '',
                zotero_paper_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            f"""
            INSERT INTO user_profile_new (
                id, explicit_interests_json, inferred_keywords_json,
                representative_papers_json, research_summary, zotero_paper_count,
                created_at, updated_at
            )
            SELECT
                id,
                {value_expr("explicit_interests_json", default="'[]'")},
                {value_expr("inferred_keywords_json", "inferred_interests_json", "'[]'")},
                {value_expr("representative_papers_json", default="'[]'")},
                {value_expr("research_summary", "summary", "''")},
                {value_expr("zotero_paper_count", default="0")},
                {value_expr("created_at")},
                {value_expr("updated_at")}
            FROM user_profile
            """
        )
        connection.execute("DROP TABLE user_profile")
        connection.execute("ALTER TABLE user_profile_new RENAME TO user_profile")

    def _migrate_recommendation_tables(self, connection: sqlite3.Connection) -> None:
        self._migrate_table_with_candidate_fk(
            connection=connection,
            table_name="recommendations",
            legacy_table_name="legacy_recommendations",
            create_sql="""
                CREATE TABLE recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER,
                    recommendation_date TEXT NOT NULL,
                    local_score REAL,
                    llm_score REAL,
                    rank INTEGER,
                    reason TEXT NOT NULL DEFAULT '',
                    card_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(paper_id) REFERENCES candidate_papers(id) ON DELETE SET NULL
                )
            """,
            copy_sql="""
                INSERT INTO recommendations (
                    id, paper_id, recommendation_date, local_score, llm_score, rank,
                    reason, card_json, created_at
                )
                SELECT id,
                    CASE WHEN paper_id IN (SELECT id FROM candidate_papers) THEN paper_id ELSE NULL END,
                    recommendation_date, local_score, llm_score, rank, reason, card_json, created_at
                FROM legacy_recommendations
            """,
        )
        self._migrate_table_with_candidate_fk(
            connection=connection,
            table_name="feedback",
            legacy_table_name="legacy_feedback",
            create_sql="""
                CREATE TABLE feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id INTEGER,
                    paper_id INTEGER,
                    feedback_type TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL,
                    FOREIGN KEY(paper_id) REFERENCES candidate_papers(id) ON DELETE SET NULL
                )
            """,
            copy_sql="""
                INSERT INTO feedback (
                    id, recommendation_id, paper_id, feedback_type, note, created_at
                )
                SELECT id,
                    CASE WHEN recommendation_id IN (SELECT id FROM recommendations) THEN recommendation_id ELSE NULL END,
                    CASE WHEN paper_id IN (SELECT id FROM candidate_papers) THEN paper_id ELSE NULL END,
                    feedback_type, note, created_at
                FROM legacy_feedback
            """,
        )

    def _migrate_rough_recommendations(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO local_rankings (
                paper_id, ranking_date, local_score, rank, reason, created_at
            )
            SELECT
                paper_id, recommendation_date, local_score, rank, reason, created_at
            FROM recommendations
            WHERE llm_score IS NULL
                AND card_json IS NULL
                AND local_score IS NOT NULL
                AND rank IS NOT NULL
            """
        )
        connection.execute(
            """
            DELETE FROM recommendations
            WHERE llm_score IS NULL
                AND card_json IS NULL
                AND local_score IS NOT NULL
                AND rank IS NOT NULL
            """
        )

    def _migrate_table_with_candidate_fk(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        legacy_table_name: str,
        create_sql: str,
        copy_sql: str,
    ) -> None:
        if not _table_exists(connection, table_name):
            connection.execute(create_sql)
            return
        foreign_tables = {row["table"] for row in connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()}
        if "candidate_papers" in foreign_tables:
            return
        if _table_exists(connection, legacy_table_name):
            return
        connection.execute(f"ALTER TABLE {table_name} RENAME TO {legacy_table_name}")
        connection.execute(create_sql)
        connection.execute(copy_sql)


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _from_json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    return json.loads(value)


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _date_part(value: str | None) -> str | None:
    if not value:
        return None
    return value.split("T", 1)[0]


def _candidate_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def _user_library_paper_from_row(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        title=row["title"],
        abstract=row["abstract"],
        authors=_from_json(row["authors_json"], []),
        year=row["year"],
        published_date=row["published_at"],
        tags=_from_json(row["tags_json"], []),
        collections=_from_json(row["collections_json"], []),
        item_type=row["item_type"],
        date_added=row["date_added"],
        date_modified=row["date_modified"],
        source=row["source"],
        external_id=row["external_id"],
        url=row["url"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _candidate_paper_from_row(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        title=row["title"],
        abstract=row["abstract"],
        authors=_from_json(row["authors_json"], []),
        year=row["year"],
        published_date=row["published_at"],
        updated_date=_date_part(row["updated_at"]),
        categories=_from_json(row["categories_json"], []),
        primary_category=row["primary_category"],
        comment=row["comment"],
        doi=row["doi"],
        source=row["source"],
        external_id=row["external_id"],
        url=row["url"],
        created_at=row["created_at"],
        updated_at=row["created_at"],
    )


def _recommendation_from_row(row: sqlite3.Row) -> Recommendation:
    return Recommendation(
        id=row["id"],
        paper_id=row["paper_id"],
        recommendation_date=row["recommendation_date"],
        local_score=row["local_score"],
        llm_score=row["llm_score"],
        rank=row["rank"],
        reason=row["reason"],
        card=_from_json(row["card_json"], None),
        created_at=row["created_at"],
    )


def _local_ranking_from_row(row: sqlite3.Row) -> LocalRanking:
    return LocalRanking(
        id=row["id"],
        paper_id=row["paper_id"],
        ranking_date=row["ranking_date"],
        local_score=row["local_score"],
        rank=row["rank"],
        reason=row["reason"],
        created_at=row["created_at"],
    )


def _feedback_from_row(row: sqlite3.Row) -> Feedback:
    return Feedback(
        id=row["id"],
        recommendation_id=row["recommendation_id"],
        paper_id=row["paper_id"],
        feedback_type=FeedbackType(row["feedback_type"]),
        note=row["note"],
        created_at=row["created_at"],
    )


def _profile_from_row(row: sqlite3.Row) -> UserProfile:
    return UserProfile(
        id=row["id"],
        explicit_interests=_from_json(row["explicit_interests_json"], []),
        inferred_keywords=_from_json(row["inferred_keywords_json"], []),
        representative_papers=_from_json(row["representative_papers_json"], []),
        research_summary=row["research_summary"],
        zotero_paper_count=row["zotero_paper_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
