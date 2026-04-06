# Copilot Implementation Plan — Instagram Competitor Knowledge Engine

## 0. Purpose

This document is a technical implementation plan for evolving the current **Senpai Reel** app from a scrape-and-analytics tool into a **competitor knowledge ingestion and retrieval system** for short-form Instagram content.

The target outcome is **not** a better dashboard.

The target outcome is a system that can:

1. ingest competitor posts and videos reliably,
2. extract what competitors are **saying** and **showing**,
3. convert each post into reusable **knowledge units**,
4. rank those units using market evidence,
5. expose them to a retrieval layer that powers an internal research assistant / marketing agent.

This plan is designed to be handed to **GitHub Copilot** so implementation can proceed in discrete, technical workstreams.

---

## 1. Strategic Reframe

### Current app
The current app mostly does the following:

- scrape Instagram reel metadata into DuckDB,
- optionally normalize some fields into structured tables,
- provide data viewer + analytics pages,
- provide helper scripts for video downloads,
- contain partially built audio / AI video / graph modules that are not fully integrated.

### Desired app
The future app should become:

> **Instagram Competitor Knowledge Engine**
>
> A system that continuously ingests competitor short-form content, extracts semantic knowledge from speech + on-screen text + metadata, stores it in structured form, and makes it retrievable for strategy analysis and content generation.

### Core design decision
Do **not** make fine-tuning the first implementation path.

Build **retrieval over a continuously updated proprietary corpus** first.

That means:

- preserve raw assets,
- generate structured knowledge artifacts,
- store embeddings,
- retrieve evidence-backed records at answer time,
- optionally add model fine-tuning much later for specific style tasks.

---

## 2. Product Scope for Engineering

### In scope
- Instagram competitor account ingestion
- asset preservation
- metadata normalization
- audio extraction + transcription
- on-screen text extraction (OCR)
- message-unit extraction
- topic / hook / CTA / audience labeling
- embeddings + retrieval
- trend snapshots
- source-backed query layer
- agent-facing APIs

### Out of scope for phase 1
- full autonomous content generation agent
- direct model fine-tuning on raw corpus
- multi-platform ingestion
- social scheduling / publishing
- graph analytics as primary value path
- enterprise auth / billing / team permissions
- polished public-facing product UI

---

## 3. Technical Principles

1. **Raw source first**
   - Preserve original metadata and assets.
   - Never overwrite raw source-of-truth fields.

2. **Structured knowledge second**
   - Downstream semantic tables should be derived from raw artifacts and re-buildable.

3. **Segment-level indexing**
   - Do not store only post-level transcript blobs.
   - Store time-coded segments and extracted message units.

4. **Retrieval before training**
   - Knowledge should remain inspectable, updateable, and attributable.

5. **Evidence-backed outputs**
   - Every generated insight must map back to source posts and timestamps.

6. **Idempotent pipelines**
   - Re-running the pipeline must not create uncontrolled duplicates.

7. **Swappable extraction providers**
   - Transcription / OCR / embedding providers should be configurable.

8. **Incremental evolution**
   - Keep existing Streamlit app, but progressively turn it into an operator console.

---

## 4. High-Level Architecture

```text
                     +------------------------------+
                     |        Streamlit UI          |
                     |  operator console / search   |
                     +--------------+---------------+
                                    |
                                    v
+--------------------------------------------------------------------+
|                         Orchestration Layer                         |
| ingest job -> download job -> transcribe job -> OCR job -> extract |
| -> embed -> index -> trend snapshot                                |
+--------------------------------------------------------------------+
   |                |                  |                  |
   v                v                  v                  v
+---------+   +------------+    +-------------+    +----------------+
| Source  |   | Asset Store |    | DuckDB/SQL  |    | Vector Index   |
| Adapter |   | mp4/wav/jpg |    | canonical   |    | embeddings      |
| public  |   | local/S3    |    | knowledge   |    | retrieval       |
+---------+   +------------+    +-------------+    +----------------+
                                    |
                                    v
                          +----------------------+
                          | Agent / Query Layer  |
                          | evidence-grounded    |
                          +----------------------+
```

---

## 5. Recommended Repository Refactor

Refactor current structure into clearer bounded modules.

```text
senpai-reel/
├── app.py
├── pages/
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── db.py
│   ├── models.py
│   └── utils/
├── ingestion/
│   ├── adapters/
│   │   ├── instagram_apify.py
│   │   ├── instagram_browser.py
│   │   └── base.py
│   ├── jobs/
│   │   ├── scrape_accounts.py
│   │   ├── download_assets.py
│   │   └── deduplicate_posts.py
│   └── parsers/
├── processing/
│   ├── audio/
│   │   ├── extract_audio.py
│   │   ├── transcribe.py
│   │   └── segment_normalizer.py
│   ├── vision/
│   │   ├── frame_sampler.py
│   │   ├── ocr.py
│   │   └── overlay_text_merger.py
│   ├── semantics/
│   │   ├── message_unit_extractor.py
│   │   ├── taxonomy.py
│   │   ├── topic_classifier.py
│   │   ├── hook_classifier.py
│   │   └── stance_detector.py
│   └── embeddings/
│       ├── embedder.py
│       └── index_sync.py
├── knowledge/
│   ├── retrieval/
│   │   ├── hybrid_search.py
│   │   ├── reranker.py
│   │   └── evidence_builder.py
│   ├── trends/
│   │   ├── trend_snapshot.py
│   │   ├── message_scoring.py
│   │   └── creator_baselines.py
│   └── exports/
│       ├── markdown_export.py
│       ├── jsonl_export.py
│       └── training_corpus_export.py
├── api/
│   ├── app.py
│   ├── schemas.py
│   └── routes/
├── tasks/
│   ├── worker.py
│   ├── scheduler.py
│   └── queue.py
├── storage/
│   ├── raw/
│   ├── audio/
│   ├── frames/
│   └── derived/
├── tests/
└── docs/
```

### Notes
- Keep DuckDB initially if speed of local analytics matters.
- Add a vector index that can start local and later move to a managed vector DB.
- Keep provider-specific adapters isolated.

---

## 6. Canonical Data Model

Use a canonical schema that separates **raw**, **derived**, and **knowledge** layers.

### 6.1 Raw entities

#### `creator_accounts`
Represents each competitor account under monitoring.

```sql
CREATE TABLE IF NOT EXISTS creator_accounts (
    creator_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,                 -- instagram
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT,
    profile_url TEXT,
    bio TEXT,
    category TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `posts`
Canonical post table.

```sql
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,                 -- instagram
    creator_id TEXT NOT NULL,
    shortcode TEXT,
    post_url TEXT NOT NULL,
    caption TEXT,
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP NOT NULL,
    media_type TEXT,                        -- reel, post, carousel
    duration_seconds DOUBLE,
    location_name TEXT,
    like_count INTEGER,
    comment_count INTEGER,
    view_count INTEGER,
    play_count INTEGER,
    raw_payload JSON,
    ingest_status TEXT DEFAULT 'scraped',
    FOREIGN KEY (creator_id) REFERENCES creator_accounts(creator_id)
);
```

#### `post_metrics_history`
Store metrics snapshots over time instead of only latest values.

```sql
CREATE TABLE IF NOT EXISTS post_metrics_history (
    id BIGINT PRIMARY KEY,
    post_id TEXT NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    like_count INTEGER,
    comment_count INTEGER,
    view_count INTEGER,
    play_count INTEGER,
    save_count INTEGER,                     -- nullable / usually unavailable
    share_count INTEGER,                    -- nullable / usually unavailable
    source TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `hashtags`
```sql
CREATE TABLE IF NOT EXISTS hashtags (
    id BIGINT PRIMARY KEY,
    post_id TEXT NOT NULL,
    hashtag TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `mentions`
```sql
CREATE TABLE IF NOT EXISTS mentions (
    id BIGINT PRIMARY KEY,
    post_id TEXT NOT NULL,
    mentioned_handle TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `media_assets`
Tracks persisted media files and download status.

```sql
CREATE TABLE IF NOT EXISTS media_assets (
    asset_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,               -- video, audio, frame, thumbnail
    local_path TEXT,
    storage_uri TEXT,
    mime_type TEXT,
    file_size_bytes BIGINT,
    sha256 TEXT,
    width INTEGER,
    height INTEGER,
    duration_seconds DOUBLE,
    status TEXT NOT NULL,                   -- pending, downloaded, failed, processed
    downloaded_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

### 6.2 Derived content entities

#### `transcript_segments`
Core speech representation.

```sql
CREATE TABLE IF NOT EXISTS transcript_segments (
    segment_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    language TEXT,
    speaker_label TEXT,
    start_sec DOUBLE NOT NULL,
    end_sec DOUBLE NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE,
    is_music BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `screen_text_segments`
OCR / overlay text extracted from frames.

```sql
CREATE TABLE IF NOT EXISTS screen_text_segments (
    screen_text_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    frame_time_sec DOUBLE,
    frame_index INTEGER,
    text TEXT NOT NULL,
    confidence DOUBLE,
    bbox_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `captions_normalized`
Optional normalized caption parsing.

```sql
CREATE TABLE IF NOT EXISTS captions_normalized (
    post_id TEXT PRIMARY KEY,
    clean_caption TEXT,
    emoji_count INTEGER,
    question_count INTEGER,
    exclamation_count INTEGER,
    sentence_count INTEGER,
    reading_grade DOUBLE,
    language TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

### 6.3 Knowledge entities

#### `message_units`
This is the most important table in the entire system.

Each row is one reusable knowledge atom.

```sql
CREATE TABLE IF NOT EXISTS message_units (
    message_unit_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    source_type TEXT NOT NULL,              -- transcript, screen_text, caption, merged
    source_segment_ids JSON,                -- references to transcript/screen_text segments
    start_sec DOUBLE,
    end_sec DOUBLE,
    raw_text TEXT NOT NULL,
    normalized_text TEXT,
    unit_type TEXT NOT NULL,                -- hook, claim, advice, cta, pain, proof, objection
    topic TEXT,
    subtopic TEXT,
    stance TEXT,                            -- supportive, critical, contrarian, neutral
    target_audience TEXT,
    tone TEXT,                              -- authoritative, empathetic, urgent, aspirational
    hook_type TEXT,                         -- question, myth, mistake, promise, list, fear
    cta_type TEXT,                          -- comment, follow, DM, save, share, link
    confidence DOUBLE,
    extraction_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

#### `message_unit_scores`
Decouple scoring from extraction.

```sql
CREATE TABLE IF NOT EXISTS message_unit_scores (
    id BIGINT PRIMARY KEY,
    message_unit_id TEXT NOT NULL,
    score_name TEXT NOT NULL,               -- evidence_score, trend_score, novelty_score
    score_value DOUBLE NOT NULL,
    score_context JSON,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_unit_id) REFERENCES message_units(message_unit_id)
);
```

#### `topics`
Controlled vocabulary / taxonomy support.

```sql
CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    topic_name TEXT NOT NULL UNIQUE,
    parent_topic_id TEXT,
    description TEXT
);
```

#### `message_unit_topics`
Many-to-many mapping if needed.

```sql
CREATE TABLE IF NOT EXISTS message_unit_topics (
    id BIGINT PRIMARY KEY,
    message_unit_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    confidence DOUBLE,
    FOREIGN KEY (message_unit_id) REFERENCES message_units(message_unit_id),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);
```

#### `trend_snapshots`
Periodic trend rollups.

```sql
CREATE TABLE IF NOT EXISTS trend_snapshots (
    trend_snapshot_id TEXT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    platform TEXT NOT NULL,
    topic TEXT NOT NULL,
    creator_count INTEGER,
    post_count INTEGER,
    message_unit_count INTEGER,
    avg_like_count DOUBLE,
    avg_comment_count DOUBLE,
    avg_view_count DOUBLE,
    trend_score DOUBLE,
    summary_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.4 Retrieval entities

#### `embeddings`
Use one row per searchable chunk.

```sql
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL,              -- transcript_segment, screen_text, message_unit, post
    object_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    vector_dim INTEGER NOT NULL,
    vector_store_ref TEXT,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `search_queries_log`
Track actual use and quality.

```sql
CREATE TABLE IF NOT EXISTS search_queries_log (
    query_id TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    filters_json JSON,
    results_json JSON,
    clicked_object_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. Identity, Keys, and Idempotency

### Rules
- `creator_id`: deterministic UUID derived from platform + handle
- `post_id`: deterministic from platform + shortcode or platform-native ID
- `asset_id`: deterministic from post_id + asset_type + sha256
- `message_unit_id`: deterministic hash of post_id + normalized_text + source span + unit_type

### Deduplication strategy
- Unique constraint on `posts(post_id)`
- Unique constraint on `(post_id, snapshot_at)` in metrics history if desired
- Compute content hash for transcripts and OCR text
- Prevent repeated creation of identical message units

### Reprocessing
Derived tables should be re-buildable from raw inputs:
- transcript regeneration allowed
- OCR regeneration allowed
- message extraction versioned
- scores recomputed independently

---

## 8. Pipeline Design

Use a job-based processing pipeline.

### Job stages
1. `scrape_account`
2. `normalize_posts`
3. `download_post_video`
4. `extract_audio`
5. `transcribe_audio`
6. `sample_frames`
7. `ocr_frames`
8. `merge_multimodal_content`
9. `extract_message_units`
10. `compute_message_scores`
11. `generate_embeddings`
12. `sync_vector_index`
13. `update_trend_snapshots`

### Recommended pattern
Each stage writes its own status to a `job_runs` table or queue backend.

#### `job_runs`
```sql
CREATE TABLE IF NOT EXISTS job_runs (
    job_run_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    object_type TEXT NOT NULL,              -- creator, post, asset
    object_id TEXT NOT NULL,
    status TEXT NOT NULL,                   -- queued, running, succeeded, failed
    attempt_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT,
    payload_json JSON
);
```

### Orchestration options
Phase 1:
- simple Python orchestrator + local queue + cron/manual trigger

Phase 2:
- Celery / RQ / Dramatiq / Prefect / Temporal depending on complexity

### Recommendation
Start simple:
- Python task runner
- deterministic status table
- retry logic
- batch CLI commands

---

## 9. Ingestion Layer

### 9.1 Source adapters
Create a pluggable adapter interface.

```python
class BaseSourceAdapter(Protocol):
    def fetch_profile(self, handle: str) -> dict: ...
    def fetch_posts(self, handle: str, limit: int = 50) -> list[dict]: ...
    def download_post_media(self, post: dict) -> Path | None: ...
```

### 9.2 Adapter responsibilities
Each adapter should:
- fetch public metadata
- normalize fields to canonical post schema
- provide post URL
- attempt direct media acquisition
- emit source provenance metadata

### 9.3 Public data caution
Do not hardcode assumptions that saves/shares are available.
Design metrics as optional / sparse.

### 9.4 Immediate media acquisition
Download video **during or immediately after scrape**.
Do not rely on expiring CDN URLs later.

### 9.5 Backfill support
Add CLI command:
```bash
python -m ingestion.jobs.scrape_accounts --handles file.txt --limit 50
```

---

## 10. Media Processing

### 10.1 Audio extraction
Input:
- mp4 video asset

Output:
- wav audio asset
- metadata: duration, sample rate, channels

Use `ffmpeg` for deterministic extraction.

### 10.2 Transcription
Requirements:
- word or segment timestamps
- language detection
- confidence if provider supports it
- optional speaker labels

Output:
- normalized `transcript_segments`

Implementation abstraction:
```python
class BaseTranscriber(Protocol):
    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]: ...
```

Support:
- provider A
- provider B
- local whisper fallback

### 10.3 Frame sampling
Sample frames:
- uniformly across video
- extra samples at scene changes if possible

Store:
- sampled frame images
- frame timestamps
- scene change scores

### 10.4 OCR
Run OCR on sampled frames.

Key challenge:
overlay text may persist across adjacent frames.

Solution:
- normalize text
- merge duplicate OCR lines across near-identical consecutive frames
- output time windows instead of frame-only fragments

### 10.5 Multimodal merge
Create merged candidate text blocks from:
- transcript segments
- screen text windows
- caption

This merged representation becomes input to semantic extraction.

---

## 11. Semantic Extraction Layer

This is the core intelligence layer.

### 11.1 Why `message_units`
A post contains many reusable semantic elements:
- opening hook
- promise
- claim
- myth
- proof
- CTA
- target audience signal
- pain statement

The system should extract these as separate rows.

### 11.2 Extraction strategy
Use a two-stage approach.

#### Stage A: heuristic pre-segmentation
Split content into candidate chunks using:
- transcript timestamps
- sentence boundaries
- OCR windows
- caption paragraphs

#### Stage B: semantic classification / transformation
For each candidate chunk:
- classify `unit_type`
- normalize text
- infer `topic`
- infer `hook_type`
- infer `tone`
- infer `target_audience`
- infer `stance`
- assign confidence

### 11.3 Extraction API contract
```python
@dataclass
class MessageUnit:
    message_unit_id: str
    post_id: str
    source_type: str
    start_sec: float | None
    end_sec: float | None
    raw_text: str
    normalized_text: str
    unit_type: str
    topic: str | None
    subtopic: str | None
    stance: str | None
    target_audience: str | None
    tone: str | None
    hook_type: str | None
    cta_type: str | None
    confidence: float
```

### 11.4 Controlled vocabularies
Define enums or taxonomies for:
- `unit_type`
- `hook_type`
- `cta_type`
- `tone`
- `stance`

Suggested `unit_type` values:
- `hook`
- `claim`
- `advice`
- `pain`
- `proof`
- `cta`
- `audience`
- `objection`
- `story`
- `offer`

Suggested `hook_type` values:
- `question`
- `mistake`
- `myth`
- `promise`
- `list`
- `fear`
- `curiosity`
- `contrarian`
- `authority`

### 11.5 Topic taxonomy
Start with a seed taxonomy file:
```yaml
jobs_australia:
  - resume
  - interview
  - linkedin
  - visas
  - networking
  - ATS
  - salary
  - recruiter_behavior
marketing:
  - hooks
  - copywriting
  - brand
  - offer
  - growth
  - audience
  - positioning
```

Allow custom per-domain extensions.

---

## 12. Message Scoring and Trend Logic

A raw message unit is not enough.
It needs **market evidence**.

### 12.1 Compute creator baselines
For each creator:
- median likes
- median views
- median comments
- average post frequency
- average engagement ratio where possible

Store in a materialized table:
```sql
CREATE TABLE IF NOT EXISTS creator_baselines (
    creator_id TEXT PRIMARY KEY,
    baseline_like_count DOUBLE,
    baseline_comment_count DOUBLE,
    baseline_view_count DOUBLE,
    baseline_post_frequency DOUBLE,
    updated_at TIMESTAMP
);
```

### 12.2 Score dimensions
For each `message_unit`, compute:

#### `evidence_score`
Based on:
- post performance relative to creator baseline
- recency
- extraction confidence

#### `repetition_score`
Based on:
- same or similar idea repeated across posts
- same or similar idea repeated across creators

#### `trend_score`
Based on:
- recent frequency growth
- creator diversity
- engagement-weighted recurrence

#### `novelty_score`
Based on:
- semantic distance from historical norms

### 12.3 Practical formula (initial)
```text
evidence_score =
  0.35 * relative_views +
  0.25 * relative_likes +
  0.15 * relative_comments +
  0.15 * extraction_confidence +
  0.10 * recency_weight
```

```text
trend_score =
  0.4 * recent_occurrence_growth +
  0.3 * creator_diversity +
  0.2 * evidence_score +
  0.1 * recurrence_consistency
```

### 12.4 Trend snapshots
Generate daily or weekly snapshots by topic.

Output example:
- top hooks this week
- fastest rising topics
- highest-evidence claims
- creator clusters repeating same message
- contradictory viewpoints

---

## 13. Embeddings and Retrieval

### 13.1 Searchable objects
Embed the following:
- transcript segments
- merged text chunks
- message units
- trend summaries

Do not embed only raw posts.

### 13.2 Embedding granularity
Recommended:
- message unit embedding = primary retrieval object
- transcript segment embedding = supporting evidence object

### 13.3 Retrieval modes
Implement hybrid search:
1. lexical search
2. vector similarity
3. reranking
4. evidence stitching

### 13.4 Query examples to support
- "What are competitors saying about landing a job in Australia?"
- "Show common hooks used by HR creators for resume advice."
- "Find contrarian takes about ATS optimization."
- "What CTAs are most common in high-performing posts on interview prep?"
- "What did creator X repeatedly say in the last 30 days?"

### 13.5 Retrieval output contract
Every answer should be built from:
- answer summary
- supporting message units
- source posts
- time references
- confidence notes

Example response payload:
```json
{
  "answer": "Most creators frame ATS advice around keyword matching, resume tailoring, and recruiter filtering myths.",
  "evidence": [
    {
      "message_unit_id": "mu_123",
      "text": "Your resume gets rejected before a human even sees it.",
      "unit_type": "claim",
      "creator_handle": "example_creator",
      "post_url": "https://...",
      "posted_at": "2026-04-01T12:00:00Z",
      "evidence_score": 0.84
    }
  ]
}
```

---

## 14. Agent Architecture

### 14.1 Do not make the agent the system of record
The LLM should not be the storage layer.
It should orchestrate reasoning over retrieval results.

### 14.2 Agent responsibilities
The agent may:
- summarize trends,
- compare creator viewpoints,
- propose content angles,
- synthesize repeated patterns,
- generate draft content based on retrieved evidence.

The agent should not:
- invent unsupported competitor claims,
- answer without sources,
- assume sparse metrics are complete.

### 14.3 Agent pipeline
```text
user question
 -> parse intent
 -> retrieve message units + segments + trend snapshots
 -> rerank by topic + recency + evidence
 -> assemble evidence pack
 -> LLM synthesizes answer
 -> return source-backed response
```

### 14.4 Modes
Support at least 3 modes:
- `research_mode`
- `trend_mode`
- `content_mode`

#### `research_mode`
Goal:
- factual evidence-backed analysis

#### `trend_mode`
Goal:
- identify emerging repeated messages

#### `content_mode`
Goal:
- derive content ideas from corpus without copying specific creators

---

## 15. API Design

Add a lightweight API layer so the knowledge engine is usable outside Streamlit.

### 15.1 Recommended stack
- FastAPI
- Pydantic models
- background tasks or queue integration

### 15.2 Core endpoints

#### `POST /ingest/accounts`
Start scrape for list of competitor handles.

Request:
```json
{
  "platform": "instagram",
  "handles": ["creator1", "creator2"],
  "limit_per_handle": 30
}
```

#### `GET /posts`
Filters:
- handle
- topic
- date range
- min views
- has transcript

#### `GET /posts/{post_id}`
Return:
- metadata
- asset paths
- transcript
- screen text
- message units

#### `GET /message-units/search`
Query params:
- q
- topic
- handle
- unit_type
- date_from
- date_to
- min_evidence_score

#### `GET /trends`
Filters:
- topic
- date window
- handle subset

#### `POST /agent/query`
Body:
```json
{
  "mode": "research_mode",
  "question": "What are creators saying about ATS and Australian job applications?"
}
```

Return:
- answer
- evidence pack
- citations / post URLs
- related topics

---

## 16. Streamlit Refactor Plan

Keep Streamlit as the operator console.

### Replace or add pages

#### Page: `Ingestion Console`
- competitor account management
- scrape job trigger
- job status
- failed download retry
- asset counts

#### Page: `Corpus Explorer`
- list posts
- transcript viewer
- screen text viewer
- source evidence panel

#### Page: `Knowledge Explorer`
- search message units
- filter by topic, creator, hook type, CTA type, tone
- compare creators side-by-side

#### Page: `Trend Monitor`
- topic trend charts
- rising hooks
- repeated claims
- creator overlap

#### Page: `Agent Workbench`
- ask questions over the corpus
- show retrieved evidence
- allow export to markdown / jsonl

### Deprecate as primary pages
- graph network as primary UX
- generic analytics as main value proposition

Not delete immediately, but demote.

---

## 17. Export Formats

The system should export knowledge in multiple forms.

### 17.1 JSONL export
For downstream agent pipelines / batch processing.

One JSON object per message unit:
```json
{
  "message_unit_id": "...",
  "topic": "resume",
  "unit_type": "hook",
  "text": "...",
  "creator_handle": "...",
  "post_url": "...",
  "posted_at": "...",
  "scores": {
    "evidence_score": 0.81,
    "trend_score": 0.72
  }
}
```

### 17.2 Markdown export
Use for human review and ChatGPT project uploads.

Structure by:
- topic
- date range
- creator
- evidence ranking

### 17.3 Retrieval corpus export
Chunked documents for external vectorization if needed.

### 17.4 Training corpus export
Only later.
Should exclude:
- low-confidence extraction
- unsupported OCR-only fragments
- duplicated message units

---

## 18. Configuration Design

Centralize configuration in `core/config.py`.

### Config domains
- source adapter settings
- ffmpeg path
- transcription provider
- OCR provider
- embedding provider
- vector store backend
- storage paths
- scoring weights
- topic taxonomy file
- LLM prompt templates
- environment profile (local/dev/prod)

Example:
```python
class Settings(BaseSettings):
    APP_ENV: str = "local"
    STORAGE_ROOT: str = "./storage"
    TRANSCRIBER_PROVIDER: str = "openai"
    OCR_PROVIDER: str = "tesseract"
    EMBEDDING_PROVIDER: str = "openai"
    VECTOR_BACKEND: str = "local"
    DEFAULT_PLATFORM: str = "instagram"
```

---

## 19. Observability and QA

### 19.1 Logging
Every stage should emit structured logs:
- object id
- stage
- provider
- duration
- status
- error class

### 19.2 Quality checks
Add quality flags:
- transcript empty
- OCR noise likely
- low audio confidence
- duplicate post
- suspiciously short or long content
- message extraction low confidence

### 19.3 Human review workflow
Build a review table or UI state for:
- message units needing approval
- failed OCR
- failed asset download
- taxonomy conflicts

### 19.4 Metrics to track
- % posts with downloaded video
- % posts with audio extracted
- % posts with transcript
- avg transcript segments per post
- % posts with OCR text
- avg message units per post
- query success rate
- top searched topics

---

## 20. Testing Strategy

### 20.1 Unit tests
Cover:
- schema normalization
- transcript segment normalization
- OCR merge logic
- message unit extraction transforms
- score calculation
- deterministic IDs
- duplicate detection

### 20.2 Integration tests
Cover:
- scrape -> normalize -> DB insert
- media -> audio -> transcript
- transcript + OCR -> message units
- embeddings -> search
- trend snapshot generation

### 20.3 Golden datasets
Create a small curated dataset of 20-50 posts with manually reviewed outputs:
- transcripts
- OCR text
- message units
- topic tags
- hook labels

Use it to measure regressions.

### 20.4 LLM-assisted extraction QA
If using LLMs for semantic extraction:
- store prompt version
- store model name
- compare outputs on golden set
- review changes before rollout

---

## 21. Security, Compliance, and Data Governance

### Engineering stance
Treat source access and platform usage as replaceable and reviewable.

Requirements:
- isolate source adapters
- log provenance of each acquired object
- store access method metadata
- allow deletion of creator or post data
- support reprocessing without source mutation

Do not hardwire the system to one brittle acquisition path.

### Governance
- keep raw payload provenance
- version semantic extraction
- version scoring logic
- support delete/rebuild workflows

---

## 22. Migration Plan From Current Codebase

### Phase 0 — Stabilize current app
Tasks:
- review `core/db.py`
- remove duplicated ETL logic between `core/db.py` and `pipeline/transform.py`
- add migration scripts
- add deduplication rules to raw ingestion
- make structured processing automatic

### Phase 1 — Canonical ingestion + assets
Tasks:
- introduce `creator_accounts`, `posts`, `media_assets`
- write normalization layer from current raw payloads into canonical tables
- integrate immediate media download after scrape
- track asset status and failure reasons

### Phase 2 — Speech + OCR pipeline
Tasks:
- wire audio extraction
- implement transcriber abstraction
- persist transcript segments
- implement frame sampling + OCR
- persist screen text segments

### Phase 3 — Semantic knowledge extraction
Tasks:
- create `message_units`
- build extraction pipeline
- define taxonomy files
- add confidence scores and extraction versioning

### Phase 4 — Retrieval + search
Tasks:
- add embeddings
- implement hybrid search
- create evidence builder
- expose API + Streamlit search UI

### Phase 5 — Trend intelligence
Tasks:
- creator baselines
- message scoring
- trend snapshots
- rising topics / hooks dashboards

### Phase 6 — Agent workbench
Tasks:
- evidence-grounded Q&A endpoint
- prompt templates
- export to markdown / JSONL
- content ideation mode

---

## 23. Work Breakdown for Copilot

Below is a concrete implementation backlog.

### Epic A — Database foundation
1. Create migration framework
2. Create canonical schema SQL files
3. Add deterministic ID utilities
4. Add repository classes / data access layer
5. Add data validation models

### Epic B — Ingestion refactor
1. Build source adapter interface
2. Wrap existing Apify ingestion in new adapter
3. Normalize current raw payloads into canonical post model
4. Add account ingestion CLI
5. Add post dedupe logic
6. Add metrics history snapshots

### Epic C — Asset pipeline
1. Create media asset table and repository
2. Implement immediate video download stage
3. Implement checksum + metadata extraction
4. Add retry logic for failed downloads
5. Add local storage path manager

### Epic D — Audio pipeline
1. Implement ffmpeg audio extraction
2. Create transcriber interface
3. Add provider implementation
4. Normalize transcript segments
5. Add transcript QA flags

### Epic E — Vision/OCR pipeline
1. Create frame sampler
2. Extract frames on time intervals + scene changes
3. Run OCR provider
4. Merge repeated OCR text across frames
5. Persist screen text segments

### Epic F — Semantic extraction
1. Create message-unit datamodel
2. Implement chunk builder from transcript/OCR/caption
3. Implement unit type classifier
4. Implement topic classifier
5. Implement tone / hook / CTA / audience labeling
6. Version extraction runs

### Epic G — Scoring and trends
1. Compute creator baselines
2. Implement evidence_score
3. Implement repetition detection
4. Implement trend_score
5. Create trend snapshot generator

### Epic H — Retrieval layer
1. Embed message units
2. Embed transcript segments
3. Implement lexical search
4. Implement vector similarity search
5. Implement reranker
6. Implement evidence pack builder

### Epic I — API and agent
1. Add FastAPI app
2. Create search endpoints
3. Create trends endpoint
4. Create agent query endpoint
5. Add evidence-backed answer format

### Epic J — Streamlit operator console
1. Add ingestion page
2. Add corpus explorer
3. Add knowledge explorer
4. Add trend monitor
5. Add agent workbench

### Epic K — Exports
1. JSONL export
2. markdown export
3. topic bundle export
4. low-confidence filtering rules

### Epic L — Observability + testing
1. structured logging
2. job status tracking
3. golden test dataset
4. integration tests
5. semantic regression checks

---

## 24. Suggested Implementation Order for Copilot

Use this order to minimize dead ends.

### Step 1
Create canonical schema + migration scripts.

### Step 2
Build normalization pipeline from current `raw_scrapes` to:
- `creator_accounts`
- `posts`
- `hashtags`
- `mentions`
- `post_metrics_history`

### Step 3
Add `media_assets` and integrate immediate video download.

### Step 4
Wire audio extraction and persist `transcript_segments`.

### Step 5
Wire frame sampling and persist `screen_text_segments`.

### Step 6
Create `message_units` from transcript + OCR + caption.

### Step 7
Add scoring and baselines.

### Step 8
Add embeddings and hybrid retrieval.

### Step 9
Expose search + agent endpoints.

### Step 10
Refactor Streamlit into operator console.

---

## 25. Non-Goals and Anti-Patterns to Avoid

### Do not do these early
- train/fine-tune on raw Instagram dump
- build giant graphs before reliable transcript/OCR pipeline
- focus on aesthetic dashboards before retrieval works
- over-optimize for every metric field
- build multi-platform acquisition before one platform is solid
- create too many taxonomies too early
- let message extraction become opaque and non-auditable

### Highest-risk anti-patterns
1. **Over-engineering**
   - building advanced agent behaviors before reliable corpus creation

2. **Output over outcome**
   - collecting many videos without improving answer quality

3. **Feature-first thinking**
   - adding analytics widgets before semantic retrieval exists

4. **Complexity creep**
   - too many partially connected pipelines and no single source of truth

---

## 26. Acceptance Criteria for “System Works”

The new system should be considered functionally successful when all of the following are true:

1. A user can add competitor handles and ingest recent posts.
2. Each ingested post becomes a canonical `post` record with stable ID.
3. Video assets are downloaded and tracked automatically.
4. Transcript segments are stored with timestamps.
5. On-screen text is extracted and stored.
6. At least one `message_unit` is extracted for the majority of valid posts.
7. Search can retrieve message units by topic or phrasing.
8. Search results show source evidence with post URL and text span.
9. Trend snapshots can identify repeated or rising messages by topic.
10. An agent query can answer a topic question using retrieved evidence, not raw hallucination.

---

## 27. First Technical Deliverable

The first meaningful milestone is **not** “agent mode”.

It is:

> **A repeatable ingestion-to-knowledge pipeline for one Instagram competitor account that produces:**
> - canonical posts,
> - persisted video/audio assets,
> - transcript segments,
> - screen text segments,
> - message units,
> - searchable embeddings.

If that works well for one account, scale to many.

---

## 28. Immediate Copilot Prompt Starters

Use these prompts with Copilot as implementation starters.

### Prompt 1 — canonical schema
> Create SQL migration files and Python repository classes for the following tables: creator_accounts, posts, post_metrics_history, hashtags, mentions, media_assets, transcript_segments, screen_text_segments, message_units, message_unit_scores, creator_baselines, trend_snapshots, embeddings, job_runs. Use DuckDB-compatible SQL and add deterministic ID generation helpers.

### Prompt 2 — normalize current raw scrapes
> Refactor the current raw_scrapes ingestion code so it maps Apify Instagram reel payloads into canonical creator_accounts, posts, hashtags, mentions, and post_metrics_history tables. Preserve raw JSON in posts.raw_payload and implement idempotent upsert behavior.

### Prompt 3 — asset pipeline
> Implement a media asset pipeline that downloads Instagram post video assets immediately after scrape, computes sha256, extracts media metadata via ffprobe, stores local paths in media_assets, and updates job_runs with retry-safe statuses.

### Prompt 4 — transcription pipeline
> Build an audio extraction and transcription pipeline using ffmpeg and a provider abstraction. Persist timestamped transcript_segments linked to post_id and include provider name, language, confidence, and start/end seconds.

### Prompt 5 — OCR pipeline
> Build a frame sampling and OCR module for short-form videos. Sample frames uniformly plus on scene changes, run OCR, merge duplicate overlay text across nearby frames, and persist screen_text_segments with time and confidence.

### Prompt 6 — message unit extraction
> Implement a semantic extraction pipeline that turns transcript segments, OCR text, and captions into message_units. Classify each unit into unit_type, topic, tone, hook_type, cta_type, stance, and target_audience. Make extraction versioned and auditable.

### Prompt 7 — retrieval
> Implement hybrid search over message_units and transcript_segments using lexical search plus vector similarity. Return evidence-backed results with source post metadata and ranked scores.

### Prompt 8 — FastAPI
> Create a FastAPI app exposing endpoints for account ingestion, post retrieval, message unit search, trend snapshots, and evidence-backed agent query. Use Pydantic models and repository classes.

### Prompt 9 — Streamlit console
> Refactor the current Streamlit app into an operator console with pages for ingestion status, corpus explorer, knowledge explorer, trend monitor, and agent workbench. Use the canonical schema instead of the legacy tables.

---

## 29. Final Engineering Judgment

This system should be built as a **knowledge substrate** first and an **agent** second.

The durable asset is not the UI and not the model prompt.

The durable asset is:
- the competitor corpus,
- the structured message units,
- the scoring logic,
- and the retrieval layer that turns all of that into reusable intelligence.

Build that well, and everything else becomes easier.
