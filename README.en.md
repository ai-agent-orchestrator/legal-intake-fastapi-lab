# Legal Intake FastAPI Lab

A public FastAPI project for consultation preparation and legal marketing drafts. The required development scope includes **nine security actions, LangChain, LangGraph, LangSmith, RAG, embeddings, vector RAG, and memvid**. The final app is capped at **11 HTTP operations**, including the existing MVP.

[한국어](README.md) | [English](README.en.md)

## 1. Required components

Start with ten synthetic guidance documents and enrich the existing guidance API with retrieved evidence. Llama is the planned generation family; local `multilingual-e5-large-instruct` is the first embedding candidate. Exact models and runtime settings require design review. Qwen is excluded from the default execution scope.

| Component | Responsibility | Minimal use |
|---|---|---|
| LangChain | Task building blocks | Messages, prompt templates, LCEL, retriever, structured output |
| LangGraph | Execution order and branches | Retrieve, then generate or request more materials |
| LangSmith | Tracing and evaluation | Stage timing, results, versions, synthetic dataset experiments |
| RAG | Evidence-grounded generation | Use retrieved consultation-preparation documents |
| Embeddings | Represent text as vectors | Encode documents and queries with compatible E5 settings |
| Vector RAG | Retrieve using vector similarity | Find relevant evidence despite different wording |
| memvid | Document/vector/index storage | Masked chunks and provenance in `.mv2` |

memvid supplies storage and retrieval within RAG. Do not add another vector database or multiple agents to the first implementation. Follow **Claude review → resolve findings → approve the final design → implement incrementally**.

## 2. Current status

As of November 6, 2026; published commits and uncommitted local work are separate.

| Area | Status |
|---|---|
| Root MVP | Three APIs: synchronous create/retrieve and asynchronous guidance; 23 original tests |
| Selected foundation `4fcc698` | Decision DTOs, immutable context, admission manager, budget ledger, risk store |
| L01 NeMo wrapper / L02 context and session risk | Implemented in the local working tree, not yet committed; latest recorded run includes real NeMo: 95 passed |
| LangChain/Graph/Smith, E5 and memvid RAG | Required planned scope; implementation and real integration validation pending |
| Marketing board and M01/M02 | Planned; failed marketing checks in the recovery snapshot are not treated as completed work |
| Generation client | Existing fake/OpenAI async client; Llama adapter planned |

The 95-test result is not evidence that the new RAG stack works. Keep recovery branch `wip/codex-legal-snapshot` separate from `main`. See the [local L01/L02 record](docs/L01_L02_IMPLEMENTATION.md).

| Current root API | Execution | Contract |
|---|---|---|
| POST `/api/intakes` | `def` | 201, invalid input 422 |
| GET `/api/intakes/{intake_id}` | `def` | 200, missing intake 404 |
| POST `/api/intakes/{intake_id}/guidance` | `async def` | Stored-fact guidance, provider failure 502 |

In-memory records disappear on restart. Fake/mock tests and real provider verification are recorded separately.

## 3. Minimal vector concepts

- A vector is the numerical representation produced by an embedding model.
- Cosine similarity compares vector directions to rank related candidates in a compatible embedding space.
- Top-k controls the number of candidates, not whether they are sufficient evidence.
- Similarity is not correctness probability or legal accuracy. Match model, revision, dimensions and preprocessing, then validate retrieved evidence.

Keep this to basic Legal Intake learning. No separate research system, personal ranking formula, Llama query summarizer or custom retrieval architecture is being added.

## 4. Planned flow

```text
Indexing:
synthetic documents -> inspect/mask -> token chunks -> E5 -> memvid

Requests:
context/session/input checks and masking
 -> E5 query embedding -> memvid -> evidence inspection/relevance gate
 -> LangGraph branch
    evidence found: LangChain prompt -> Llama -> structured draft
    insufficient evidence: request more materials, zero generation calls
 -> citation/output checks -> final mask/context validation -> response

LangSmith: stage tracing and synthetic evaluation, with pre-transmission filtering
```

Preserve document IDs, source versions and model revisions. Start with internal structured DTOs while keeping the existing normal response contract. Filter inputs, outputs, metadata and exceptions before tracing. Actual LangSmith traces and dataset experiments are part of completion criteria.

## 5. All nine security actions are required

| Action | Responsibility |
|---|---|
| `validate_request_context` | Bind request, snapshot and response |
| `check_session_risk` | Inspect accumulated risk and existing session blocks |
| `check_input_policy` | Legal abuse, jailbreak, injection, secrets and privacy checks |
| `mask_personal_data` | Defined PII transformations before storage/transmission/publication |
| `check_generation_admission` | Bounded concurrency, waiting capacity and timeout |
| `check_request_budget` | Atomic budget check and reservation |
| `check_output_policy` | Inspect the complete output |
| `check_marketing_response` | Flag guarantee/exaggeration wording for human review |
| `record_risk_event` | Record confirmed policy blocks without duplication |

The service owns capacity acquisition, budget reservation, calling, settlement and release, including timeout/cancellation cleanup. Separate function tests from actual NeMo rail execution and decision consumption. Not all nine actions are implemented and integrated yet.

### Mandatory marketing check

**M01 summaries and M02 reply drafts must pass `check_marketing_response` after full output inspection**, followed by final masking and context validation. Mark guarantee/exaggeration claims for review and return only a sanitized draft. Never publish externally automatically.

Test normal wording, guarantees, negated/quoted claims, PII and checker failures, including mixed-negation bypass cases. Running the sample does not establish completion of AI security integration.

Internal decisions are `ALLOW/BLOCK/TRANSFORM/REVIEW`; reasons are `reasonCode/detailCode`. Distinguish existing `COST_LIMIT_BLOCKED` and `DYNAMIC_SESSION_BLOCKED` from new proposals. Do not claim complete PII coverage or automated legal-advertising compliance.

## 6. At most 11 application APIs

This is the review target; only the original three are implemented in the root app. Ingestion, retrieval and evaluation stay internal or script-based.

| Group | Operations | Count |
|---|---|---|
| Existing intake | Create, retrieve, guidance | 3 |
| Health | GET `/health` | 1 |
| Posts | POST/GET `/api/posts`, GET `/api/posts/{postId}` | 3 |
| Reviews | POST/GET `/api/posts/{postId}/reviews` | 2 |
| Marketing AI | POST `/api/posts/{postId}/ai-summary`, POST `/api/reviews/{reviewId}/reply-draft` | 2 |
| Total | Method/path combinations | **11** |

The older 21-API design is a historical candidate list. Do not add independent chat/SSE, post edit/delete or standalone guardrail APIs on top. Keep synchronous comparisons in a separate learning app.

## 7. Development order and learning baseline

Review the design, complete mandatory security boundaries, then add ingestion, E5/memvid, LangChain/Llama, LangGraph, LangSmith evaluation and guidance integration. Use the [architecture](docs/RAG_ARCHITECTURE_REVIEW.md) and [Claude review request](docs/CLAUDE_RAG_DESIGN_REVIEW.md) before finalizing implementation.

Keep the foundational review/reply example brief:

1. In an empty folder: `uv init`, `uv add "fastapi[standard]"`, package folders and `entrypoint = "app.main:app"`.
2. Entity → dictionary repository → DTO → exceptions/handlers → service → dependency functions → router → `main.py`.
3. `uv add pydantic-settings openai` → settings → LLM client → reply service → dependencies → async handler → lifespan. Existing config/client examples may be reused.

Acceptance: `uv run fastapi dev`, three APIs in Swagger/Postman, 201/422/404, a reply based on the saved review and `MainThread` in the real server log. The [separate review example](ohgi-review-server/README.md) is not the root intake app.

Extensions: rating-based tone (1–2 apology/empathy, 3 empathy/improvement, 4–5 thanks), storing inspected replies and returning them on review lookup, and a separate `def`/sync-client comparison. Main M02 remains async and all ratings pass marketing checks.

Never commit `.env`. For foundational learning, construct and explain the layers yourself; use AI for data structures, syntax and error interpretation. Consult existing HOWTO-chap01/02/03 notes as needed.

## 8. Run the current MVP

From the repository root; do not run `uv init` again:

```powershell
uv sync --python 3.14
$env:FAKE_LLM = "true"
$env:GUARDRAIL_BACKEND = "local"
uv run fastapi dev
```

Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

```powershell
uv run pytest -q -m "not nemo"
```

Verify real credentials/providers and the planned Llama/E5/memvid/LangSmith integrations separately. The [L01/L02 record](docs/L01_L02_IMPLEMENTATION.md) describes its local dedicated runtime; check whether that uncommitted code has been published before following those instructions from a fresh clone.

## 9. Study and review materials

- [30-page Dark Tablet PDF](docs/LEGAL_INTAKE_RAG_DESIGN_DARK_TABLET.pdf)
- [Basic study plan](docs/rag-basic-dark-tablet.html) · [Markdown](docs/RAG_BASIC_DESIGN.md)
- [Architecture review](docs/rag-architecture-dark-tablet.html) · [Markdown](docs/RAG_ARCHITECTURE_REVIEW.md)
- [Claude review request](docs/claude-rag-review-dark-tablet.html) · [Markdown](docs/CLAUDE_RAG_DESIGN_REVIEW.md)
- [Security migration target](docs/SECURITY_MIGRATION_PLAN.md) · [Marketing board contract](docs/LEGAL_MARKETING_BOARD.md)

Download HTML to read it in a browser; use Markdown/PDF directly on GitHub. These are review drafts, not evidence that Claude has already reviewed them.

## 10. Repository roadmap

Maintain ① `legal-intake-fastapi-lab` → ③ `python-memvid-guardrail` → ② `spring-fastapi-async-refactor`, followed by separate private commercialization. Validate components here, extract reusable modules, then connect Spring authentication/authorization to FastAPI AI services.

Authentication/authorization, automatic publishing, general web search, operational DBs and Redis/Celery/Kafka are outside this phase. Do not modify the existing Java service or database.
