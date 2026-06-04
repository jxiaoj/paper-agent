# 本地优先的个性化学术论文推荐 Agent

这是一个本地优先的个性化论文推荐 Agent。项目从 Zotero 读取用户已有文献，从 arXiv 拉取候选论文，在本地完成用户画像、Embedding 粗排和缓存，并只在最终精排与解释生成阶段调用 OpenAI-compatible LLM。

本文档覆盖当前已完成的模块 1 到模块 7，重点说明每个模块的功能、输入数据、输出数据、运行命令、参数含义和验收方式。

## 运行前准备

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`。常用配置如下：

```env
DATABASE_PATH=data/local.db

ZOTERO_USER_ID=your_zotero_user_id
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_LIBRARY_TYPE=user

ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG
ARXIV_LOOKBACK_DAYS=3
ARXIV_MAX_RESULTS=50
ARXIV_REQUEST_DELAY_SECONDS=3
ARXIV_NUM_RETRIES=1

USER_INTEREST_KEYWORDS=large language models,AI agents,model distillation

LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL_NAME=gpt-4o-mini

EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
LOCAL_TOP_K=20
FINAL_TOP_K=5
```

`.env` 中包含密钥，不要提交到 Git。

## 当前数据库设计

SQLite 数据库默认路径：

```text
data/local.db
```

核心表：

- `user_library_papers`：用户已有文献库，当前主要来自 Zotero。
- `zotero_collections`：Zotero 文件夹元数据，用于 UI 展示可读文件夹名，并通过稳定的 collection key 过滤论文。
- `candidate_papers`：待推荐候选论文，当前主要来自 arXiv。
- `user_profile`：用户研究兴趣画像。
- `ranking_runs`：模块 5 每次粗排运行的批次记录。
- `local_rankings`：模块 5 生成的本地粗排结果，关联 `ranking_runs`。
- `recommendations`：模块 6 或模块 7 保存的最终推荐结果，关联 `candidate_papers` 和 `ranking_runs`。
- `feedback`：用户反馈，关联候选论文。
- `user_zotero_paper_embeddings`：Zotero 摘要 embedding 缓存。
- `arxiv_paper_embeddings`：arXiv 摘要 embedding 缓存。

不要用普通文本编辑器直接阅读 `.db` 文件；SQLite 数据库看起来像乱码是正常的。建议用：

```bash
sqlite3 data/local.db
```

或使用 SQLite GUI 工具查看。

## 模块 1：SQLite 本地存储与烟测

### 功能

初始化本地 SQLite 数据库，创建项目所需的数据表，并验证基本读写链路。

### 需要的数据

不依赖外部数据。只需要 `.env` 中的：

```env
DATABASE_PATH=data/local.db
```

如果不设置，默认使用 `data/local.db`。

### 生成的数据

运行后会创建或更新 SQLite schema，并插入一组烟测数据：

- 一条 `candidate_papers`
- 一条 `ranking_runs`
- 一条 `local_rankings`
- 一条 `recommendations`
- 一条 `feedback`
- 一条 `user_profile`

### 运行命令

```bash
python app/main.py --db-smoke-test
```

### 参数说明

`--db-smoke-test`

- 含义：运行数据库烟测。
- 默认值：不启用。
- 不传该参数时，`python app/main.py` 只做健康检查，不写入烟测数据。

### 验证方法

命令输出中应包含：

```text
SQLite smoke test: OK
Saved paper id: ...
Saved ranking run id: ...
Saved recommendation id: ...
Saved local ranking id: ...
Saved feedback id: ...
Saved user profile id: ...
```

也可以进入 SQLite 检查：

```bash
sqlite3 data/local.db
```

```sql
.tables
SELECT COUNT(*) FROM candidate_papers;
SELECT COUNT(*) FROM recommendations;
SELECT COUNT(*) FROM user_profile;
```

## 模块 2：Zotero Connector

### 功能

从用户 Zotero 文献库读取文献元数据，转换为统一的 `Paper` 模型，并保存到 `user_library_papers`。

当前用途：

- 作为用户已有文献库。
- 供模块 4 构建用户画像。
- 供模块 5 的 `library` 模式计算 Zotero 摘要相似度。

### 需要的数据

`.env` 中需要：

```env
ZOTERO_USER_ID=your_zotero_user_id
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_LIBRARY_TYPE=user
ZOTERO_ANALYSIS_SCOPE=all
ZOTERO_SELECTED_COLLECTIONS=
DATABASE_PATH=data/local.db
```

Zotero 条目中至少需要有标题。附件和笔记会被跳过。

### 生成的数据

写入或更新：

```text
user_library_papers
zotero_collections
```

关键字段包括：

- `source = "zotero"`
- `external_id`
- `title`
- `abstract`
- `authors`
- `year`
- `tags`
- `collections`
- `item_type`
- `date_added`
- `date_modified`

同一个 Zotero 条目通过 `UNIQUE(source, external_id)` 去重更新。

`collections` 保存的是 Zotero collection key，不是文件夹名。`zotero_collections` 保存 collection key 对应的文件夹名和父文件夹 key，供 UI 展示与筛选使用。

### 运行命令

```bash
python -m connectors.zotero_connector --max-items 50
```

### 参数说明

`--max-items`

- 含义：最多从 Zotero 拉取多少条顶层条目。
- 默认值：`50`。
- 注意：最终保存数量可能小于该值，因为附件、笔记、无标题条目会被跳过。

`--preview`

- 含义：命令行中预览打印多少条已保存文献标题。
- 默认值：`5`。

示例：

```bash
python -m connectors.zotero_connector --max-items 100 --preview 10
```

### 验证方法

命令输出应类似：

```text
Fetched and saved 65 Zotero papers.
1. ...
2. ...
```

检查数据库：

```bash
sqlite3 data/local.db
```

```sql
SELECT COUNT(*) FROM user_library_papers WHERE source = 'zotero';
SELECT id, title, date_added FROM user_library_papers WHERE source = 'zotero' ORDER BY id DESC LIMIT 5;
```

## 模块 3：arXiv Collector

### 功能

从 arXiv API 拉取近期候选论文，转换为统一的 `Paper` 模型，并保存到 `candidate_papers`。

当前逻辑是：

1. 按 arXiv category 查询。
2. 按提交时间倒序排序。
3. 最多请求 `max_results` 条。
4. 再按 `lookback_days` 做本地时间过滤。
5. 保存到候选论文表。

它不是个性化推荐筛选；真正的个性化排序在模块 5 完成。

### 需要的数据

`.env` 中常用配置：

```env
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG
ARXIV_LOOKBACK_DAYS=3
ARXIV_MAX_RESULTS=50
ARXIV_REQUEST_DELAY_SECONDS=3
ARXIV_NUM_RETRIES=1
DATABASE_PATH=data/local.db
```

### 生成的数据

写入或更新：

```text
candidate_papers
```

关键字段包括：

- `source = "arxiv"`
- `external_id`
- `title`
- `abstract`
- `authors`
- `year`
- `published_at`
- `updated_at`
- `url`
- `categories`
- `primary_category`
- `comment`
- `doi`

同一篇 arXiv 论文通过 `UNIQUE(source, external_id)` 去重更新。

### 运行命令

```bash
python -m connectors.arxiv_connector \
  --categories cs.AI,cs.CL \
  --lookback-days 3 \
  --max-results 50
```

### 参数说明

`--categories`

- 含义：逗号分隔的 arXiv 类别。
- 默认值：读取 `.env` 中的 `ARXIV_CATEGORIES`。
- 配置默认值：`cs.AI,cs.CL,cs.LG`。

`--lookback-days`

- 含义：只保留最近 N 天提交的论文。
- 默认值：读取 `.env` 中的 `ARXIV_LOOKBACK_DAYS`。
- 配置默认值：`3`。
- 设置为 `0` 时，禁用本地时间过滤。

`--max-results`

- 含义：最多向 arXiv API 请求多少条结果。
- 默认值：读取 `.env` 中的 `ARXIV_MAX_RESULTS`。
- 配置默认值：`50`。

`--request-delay-seconds`

- 含义：分页或重试之间的最小等待时间。
- 默认值：读取 `.env` 中的 `ARXIV_REQUEST_DELAY_SECONDS`。
- 配置默认值：`3.0`。
- 代码中低于 `3.0` 的值会被提升到 `3.0`，以降低限流风险。

`--retries`

- 含义：arXiv API 临时失败时的重试次数。
- 默认值：读取 `.env` 中的 `ARXIV_NUM_RETRIES`。
- 配置默认值：`1`。

`--preview`

- 含义：预览打印多少条已保存论文标题。
- 默认值：`5`。

### 验证方法

命令输出应类似：

```text
Fetched and saved 50 arXiv papers.
Categories: cs.AI, cs.CL
Lookback days: 3
Requested API results: 50
```

检查数据库：

```sql
SELECT COUNT(*) FROM candidate_papers WHERE source = 'arxiv';
SELECT id, title, published_at, primary_category
FROM candidate_papers
WHERE source = 'arxiv'
ORDER BY published_at DESC
LIMIT 5;
```

如果遇到：

```text
HTTP 429
```

说明 arXiv API 限流。建议等待几分钟后重试，或降低 `--max-results`。

## 模块 4：Profile Agent

### 功能

基于用户 Zotero 文献库和用户显式兴趣关键词，构建用户研究兴趣画像。

支持三种模式：

- `local`：纯本地规则。
- `hybrid`：本地规则 + LLM 结构化总结，LLM 失败时回退本地规则。
- `llm`：优先使用 LLM 生成的关键词和总结。

### 需要的数据

需要模块 2 已经写入：

```text
user_library_papers
```

如果 `.env` 中配置：

```env
ZOTERO_ANALYSIS_SCOPE=selected
ZOTERO_SELECTED_COLLECTIONS=collection_key_1,collection_key_2
```

则模块 4 只使用这些 Zotero 文件夹中的论文构建画像；默认 `all` 使用全部 Zotero 文献。
如果选择的是父文件夹，会同时包含其子文件夹中的论文。

建议 `.env` 中配置：

```env
USER_INTEREST_KEYWORDS=large language models,AI agents,model distillation
```

如果使用 `hybrid` 或 `llm`，还需要：

```env
LLM_API_BASE_URL=...
LLM_API_KEY=...
LLM_MODEL_NAME=...
```

### 生成的数据

写入：

```text
user_profile
```

字段包括：

- `explicit_interests_json`：用户显式配置的研究兴趣。
- `inferred_keywords_json`：从 Zotero 文献中推断出的关键词。
- `representative_papers_json`：代表性 Zotero 文献。
- `research_summary`：研究兴趣总结。
- `zotero_paper_count`：本次画像分析使用的 Zotero 文献数。

### 运行命令

```bash
python -m agents.profile_agent --max-papers 200 --profile-mode local
```

使用 LLM 混合模式：

```bash
python -m agents.profile_agent --max-papers 200 --profile-mode hybrid
```

### 参数说明

`--max-papers`

- 含义：最多读取多少篇 Zotero 文献用于画像构建。
- 默认值：`200`。

`--top-keywords`

- 含义：保留多少个推断关键词。
- 默认值：`12`。

`--representative-count`

- 含义：保留多少篇代表性文献。
- 默认值：`5`。

`--profile-mode`

- 可选值：`local`、`hybrid`、`llm`。
- 默认值：`local`。

`--use-llm-summary`

- 含义：旧参数，等价于 `--profile-mode hybrid`。
- 默认值：不启用。

### 验证方法

命令输出应包含：

```text
Profile Agent: OK
Saved profile id: ...
Zotero papers analyzed: ...
Inferred keywords: ...
Research summary: ...
```

检查数据库：

```sql
SELECT id, zotero_paper_count, research_summary, created_at
FROM user_profile
ORDER BY id DESC
LIMIT 3;
```

## 模块 5：Local Embedding Ranker

### 功能

对 `candidate_papers` 中的候选论文做本地粗排，并将粗排批次保存到 `ranking_runs`，将 Top N 结果保存到 `local_rankings`。

支持两种粗排方法：

1. `profile`：基于用户画像文本和候选论文文本的 embedding 相似度，并加关键词 bonus。
2. `library`：基于 Zotero 文献摘要和 arXiv 候选论文摘要的加权相似度。

### 需要的数据

共同需要：

```text
candidate_papers
```

`profile` 模式还需要：

```text
user_profile
```

`library` 模式还需要：

```text
user_library_papers
```

且 `library` 模式只使用摘要不为空的 Zotero 文献和 arXiv 候选论文。

如果 `.env` 中 `ZOTERO_ANALYSIS_SCOPE=selected`，则 `library` 模式只使用选中文件夹中摘要不为空的 Zotero 文献。
如果选择的是父文件夹，会同时包含其子文件夹中的论文。

### 生成的数据

写入：

```text
ranking_runs
local_rankings
```

`library` 模式还会缓存 embedding：

```text
user_zotero_paper_embeddings
arxiv_paper_embeddings
```

### 运行命令

Library 模式，也是模块 5 当前默认模式：

```bash
python -m agents.ranker_agent \
  --ranking-mode library \
  --candidate-limit 200 \
  --library-limit 500 \
  --top-n 20
```

Profile 模式：

```bash
python -m agents.ranker_agent \
  --ranking-mode profile \
  --candidate-limit 200 \
  --top-n 20
```

### 参数说明

`--candidate-limit`

- 含义：最多从 `candidate_papers` 中读取多少篇候选论文参与粗排。
- 默认值：`200`。
- 注意：不是只使用本次 arXiv 刚抓取的论文，而是从数据库候选池中按时间取最新的最多 N 篇。

`--library-limit`

- 含义：`library` 模式中最多使用多少篇 Zotero 文献。
- 默认值：`500`。

`--top-n`

- 含义：保存多少条本地粗排结果。
- 默认值：读取 `.env` 中的 `LOCAL_TOP_K`。
- 配置默认值：`20`。

`--ranking-mode`

- 可选值：`profile`、`library`。
- 默认值：`library`。

`--include-recommended`

- 含义：仅 `profile` 模式使用。启用后，不过滤已经进入 `recommendations` 的论文。
- 默认值：不启用。

`--dry-run`

- 含义：只打印粗排结果，不保存 `ranking_runs` 和 `local_rankings`。
- 默认值：不启用。

`--embedding-backend`

- 可选值：`auto`、`sentence-transformers`、`hashing`。
- 默认值：`auto`。
- `auto` 会优先尝试本地 sentence-transformers 模型，失败时回退到本地 hashing embedding。

`--preview-profile-text`

- 含义：打印 profile 模式用于 embedding 的用户画像文本并退出。
- 默认值：不启用。

### 分数含义

模块 5 输出示例：

```text
1. Vector Policy Optimization ... [local_score=0.355, semantic=0.355, bonus=0.000]
```

含义：

- `semantic`：语义相似度分数。
- `bonus`：关键词命中加分；当前主要用于 `profile` 模式，`library` 模式通常为 `0.000`。
- `local_score`：最终本地粗排分数，当前为 `semantic + bonus`。

### 验证方法

命令输出应包含：

```text
Ranker Agent: OK
Ranking mode: library
Ranked candidates: ...
Saved local rankings: True
Ranking run id: ...
```

检查数据库：

```sql
SELECT id, ranking_method, embedding_model, result_count, created_at
FROM ranking_runs
ORDER BY id DESC
LIMIT 5;

SELECT ranking_run_id, rank, paper_id, local_score, reason
FROM local_rankings
ORDER BY id DESC
LIMIT 10;
```

## 模块 6：LLM Reranking

### 功能

读取模块 5 已保存的某个 `ranking_run`，从该批 `local_rankings` 中取候选论文，让 LLM 做最终精排、摘要和推荐理由生成，并保存到 `recommendations`。

模块 6 不会重新执行模块 5。

### 需要的数据

需要：

```text
ranking_runs
local_rankings
candidate_papers
user_profile
```

如果有 LLM 配置，会调用云端 LLM：

```env
LLM_API_BASE_URL=...
LLM_API_KEY=...
LLM_MODEL_NAME=...
```

如果没有 LLM 配置，或 LLM 调用失败，会 fallback 到本地 Top K。

### 生成的数据

非 `--dry-run` 时写入：

```text
recommendations
```

每条最终推荐会关联：

- `paper_id`
- `ranking_run_id`
- `local_score`
- `llm_score`
- `rank`
- `reason`
- `card_json`

### 运行命令

先运行模块 5，得到 `Ranking run id`：

```bash
python -m agents.ranker_agent --ranking-mode library --candidate-limit 200 --top-n 20
```

再运行模块 6：

```bash
python -m llm.client --ranking-run-id 3 --top-k 5 --dry-run
```

其中 `3` 替换为模块 5 输出的真实 `Ranking run id`。

### 参数说明

`--ranking-run-id`

- 含义：指定要精排的模块 5 粗排批次。
- 默认值：不指定时，读取最新的 `ranking_runs`。

`--top-k`

- 含义：最终输出或保存多少条推荐。
- 默认值：读取 `.env` 中的 `FINAL_TOP_K`。
- 配置默认值：`5`。

`--dry-run`

- 含义：只打印最终推荐，不写入 `recommendations`。
- 默认值：不启用。

### LLM 输入包含什么

模块 6 会发送给 LLM：

- 当前 ranking run 信息：`run_id`、`ranking_method`、`embedding_model`。
- 压缩后的用户画像：`research_summary`、`explicit_interests`、`inferred_keywords`。
- 候选论文元数据：标题、作者、摘要片段、类别、发布时间、URL、local score。

不会发送完整 Zotero 文献库。

### 验证方法

命令输出应包含：

```text
LLM Reranker: OK
Rerank source: llm
Ranking run id: ...
Final recommendations: 5
```

如果是 fallback，`Rerank source` 可能是：

```text
local_fallback_no_credentials
local_fallback_llm_error
```

如果发生 fallback，命令会打印脱敏后的 `Fallback reason`，方便排查 API Key、Base URL、模型名、网络连接或 JSON 解析问题。

检查数据库：

```sql
SELECT id, ranking_run_id, paper_id, rank, local_score, llm_score, reason
FROM recommendations
ORDER BY id DESC
LIMIT 5;
```

## 模块 7：Daily Recommendation Workflow

### 功能

串联完整每日推荐工作流，一条命令执行：

1. 初始化 SQLite。
2. 同步 Zotero 文献。
3. 构建用户画像。
4. 拉取 arXiv 候选论文。
5. 执行模块 5 本地粗排。
6. 执行模块 6 LLM 精排。
7. 输出 Top 推荐并保存到 SQLite。

每一步都被包装成独立 step，日志包含 `START`、`OK`、`SKIPPED`、`STOP` 和耗时，方便分析。

### 需要的数据

完整远程流程需要：

- Zotero 配置。
- arXiv 可访问。
- 用户兴趣关键词。
- LLM 配置，推荐配置但不是强制；LLM 不可用时会 fallback。

如果使用 `--skip-zotero` 和 `--skip-arxiv`，则需要本地数据库中已经存在：

```text
user_library_papers
candidate_papers
```

### 生成的数据

可能写入或更新：

- `user_library_papers`
- `candidate_papers`
- `user_profile`
- `ranking_runs`
- `local_rankings`
- `user_zotero_paper_embeddings`
- `arxiv_paper_embeddings`
- `recommendations`

如果使用 `--dry-run`，最终 `recommendations` 不会写入，但中间的 profile 和 ranking run 仍会保存。

### 运行命令

完整每日 workflow：

```bash
python -m workflows.daily_recommendation_workflow
```

本地缓存验收命令：

```bash
python -m workflows.daily_recommendation_workflow \
  --skip-zotero \
  --skip-arxiv \
  --profile-mode local \
  --ranking-mode library \
  --embedding-backend hashing \
  --local-top-n 5 \
  --final-top-k 3 \
  --dry-run
```

### 参数说明

`--zotero-max-items`

- 含义：最多同步多少条 Zotero 条目。
- 默认值：`100`。

`--skip-zotero`

- 含义：跳过远程 Zotero 同步，复用本地 `user_library_papers`。
- 默认值：不启用。

`--profile-max-papers`

- 含义：最多使用多少篇 Zotero 文献构建用户画像。
- 默认值：`200`。

`--top-keywords`

- 含义：用户画像保留多少个关键词。
- 默认值：`12`。

`--representative-count`

- 含义：用户画像保留多少篇代表性文献。
- 默认值：`5`。

`--profile-mode`

- 可选值：`local`、`hybrid`、`llm`。
- 默认值：`hybrid`。

`--categories`

- 含义：逗号分隔的 arXiv 类别。
- 默认值：读取 `.env` 中的 `ARXIV_CATEGORIES`。
- 配置默认值：`cs.AI,cs.CL,cs.LG`。

`--lookback-days`

- 含义：arXiv 只保留最近 N 天论文。
- 默认值：读取 `.env` 中的 `ARXIV_LOOKBACK_DAYS`。
- 配置默认值：`3`。

`--arxiv-max-results`

- 含义：arXiv API 最多请求多少条结果。
- 默认值：读取 `.env` 中的 `ARXIV_MAX_RESULTS`。
- 配置默认值：`50`。

`--arxiv-request-delay-seconds`

- 含义：arXiv 分页或重试之间等待秒数。
- 默认值：读取 `.env` 中的 `ARXIV_REQUEST_DELAY_SECONDS`。
- 配置默认值：`3.0`。

`--arxiv-retries`

- 含义：arXiv API 临时失败时重试次数。
- 默认值：读取 `.env` 中的 `ARXIV_NUM_RETRIES`。
- 配置默认值：`1`。

`--skip-arxiv`

- 含义：跳过远程 arXiv 拉取，复用本地 `candidate_papers`。
- 默认值：不启用。

`--ranking-mode`

- 可选值：`profile`、`library`。
- 默认值：`library`。

`--candidate-limit`

- 含义：模块 5 最多读取多少篇候选论文参与粗排。
- 默认值：`200`。

`--library-limit`

- 含义：`library` 模式最多使用多少篇 Zotero 文献。
- 默认值：`500`。

`--local-top-n`

- 含义：模块 5 保存多少条粗排结果。
- 默认值：读取 `.env` 中的 `LOCAL_TOP_K`。
- 配置默认值：`20`。

`--final-top-k`

- 含义：模块 6 最终输出或保存多少条推荐。
- 默认值：读取 `.env` 中的 `FINAL_TOP_K`。
- 配置默认值：`5`。

`--include-recommended`

- 含义：`profile` 模式下允许已推荐过的候选论文再次参与粗排。
- 默认值：不启用。

`--embedding-backend`

- 可选值：`auto`、`sentence-transformers`、`hashing`。
- 默认值：`auto`。

`--dry-run`

- 含义：不保存最终 recommendations。
- 默认值：不启用。

### 验证方法

运行后应看到类似日志：

```text
Daily Recommendation Workflow

[1/6] Initialize SQLite: START
[1/6] Initialize SQLite: OK

[2/6] Sync Zotero library: START
[2/6] Sync Zotero library: OK

[3/6] Build user profile: START
[3/6] Build user profile: OK

[4/6] Collect arXiv candidates: START
[4/6] Collect arXiv candidates: OK

[5/6] Run local rough ranking: START
[5/6] Run local rough ranking: OK

[6/6] Run LLM reranking: START
[6/6] Run LLM reranking: OK

Top Recommendations
1. ...
2. ...
```

非 `--dry-run` 后检查：

```sql
SELECT id, ranking_run_id, rank, local_score, llm_score, reason
FROM recommendations
ORDER BY id DESC
LIMIT 5;

SELECT id, ranking_method, embedding_model, result_count, created_at
FROM ranking_runs
ORDER BY id DESC
LIMIT 5;
```

如果 Zotero 或 arXiv 远程失败，但本地已有数据，workflow 会继续并在日志中说明：

```text
Remote Zotero sync failed; continuing with ... local papers.
arXiv collection failed; continuing with ... local candidates.
```

如果关键数据不存在，则会停止并打印明确原因。

如果 LLM 精排失败，workflow 不会中断，会回退到本地 Top K，并在日志中打印脱敏后的 `Fallback reason`。

## 模块 8：Streamlit 本地 UI

### 功能

提供适合比赛 demo 的本地 Web UI，用于配置参数、查看用户画像、运行完整推荐 workflow、查看推荐卡片并提交反馈。

### 需要的数据

启动 UI 本身只需要安装依赖：

```bash
pip install -r requirements.txt
```

如果要完整运行推荐，需要前面模块所需的配置和数据：

- `.env` 中的 Zotero 配置。
- `.env` 中的 LLM 配置。
- arXiv 网络访问。
- 或者本地已有 `user_library_papers` 和 `candidate_papers`，并在 UI 中选择跳过同步。

### 生成的数据

根据用户操作，UI 会写入或更新：

- `.env`
- `user_profile`
- `ranking_runs`
- `local_rankings`
- `recommendations`
- `feedback`

### 运行命令

```bash
streamlit run app/ui_streamlit.py
```

启动后访问命令行输出的本地地址，通常是：

```text
http://localhost:8501
```

### 页面说明

`配置`

- 编辑 LLM Base URL、LLM Model、LLM API Key。
- 编辑 Zotero User ID、Zotero API Key、Zotero Library Type。
- 支持刷新 Zotero 文件夹列表，并选择使用全部 Zotero 文献或只使用勾选文件夹。
- 刷新 Zotero 文件夹列表会全量同步 collection 元数据，并清理 Zotero 中已经删除的文件夹。
- 如果 Zotero API 标记文件夹为 `deleted`，UI 会忽略该回收站文件夹。
- 勾选父文件夹时，模块 4 和模块 5 会同时使用其子文件夹中的论文。
- 编辑研究兴趣、arXiv categories、lookback days、max results。
- API key 输入框留空时，会保留 `.env` 中已有密钥。

`用户画像`

- 展示最新 `user_profile`。
- 展示显式兴趣、推断关键词、研究总结、代表性论文和 Zotero 文献数量。
- 支持重新构建画像。

`运行推荐`

- 在 UI 中运行模块 7 workflow。
- 支持选择是否跳过 Zotero 同步、是否跳过 arXiv 拉取。
- 支持选择 `profile_mode`、`ranking_mode`、`embedding_backend`。
- 支持设置 `local_top_n`、`final_top_k`、`candidate_limit`、`library_limit`。
- 支持 `dry-run`，即只生成和展示结果，不保存最终 recommendations。

`今日推荐`

- 展示已保存的推荐卡片。
- 卡片包含 title、authors、summary、why recommended、priority、arXiv link、local score、LLM score、ranking run id。
- 支持反馈按钮：`like`、`dislike`、`save`、`not_relevant`、`already_read`。
- 反馈写入 SQLite 的 `feedback` 表。

### 验收方法

启动 UI：

```bash
streamlit run app/ui_streamlit.py
```

验收重点：

1. 可以打开本地页面。
2. 可以在配置页编辑并保存参数。
3. 可以在用户画像页看到最新画像，或重新构建画像。
4. 可以在运行推荐页点击按钮执行 workflow。
5. 可以在今日推荐页看到推荐卡片。
6. 点击反馈按钮后，数据库中新增反馈记录。

检查反馈：

```bash
sqlite3 data/local.db
```

```sql
SELECT id, recommendation_id, paper_id, feedback_type, note, created_at
FROM feedback
ORDER BY id DESC
LIMIT 5;
```

## 推荐的模块验收顺序

首次运行建议按顺序验收：

```bash
python app/main.py --db-smoke-test
python -m connectors.zotero_connector --max-items 50
python -m connectors.arxiv_connector --max-results 50
python -m agents.profile_agent --profile-mode local
python -m agents.ranker_agent --ranking-mode library --top-n 20
python -m llm.client --ranking-run-id <上一步输出的 run id> --top-k 5 --dry-run
python -m workflows.daily_recommendation_workflow --skip-zotero --skip-arxiv --dry-run
streamlit run app/ui_streamlit.py
```

确认无误后，再运行完整每日 workflow：

```bash
python -m workflows.daily_recommendation_workflow
```
