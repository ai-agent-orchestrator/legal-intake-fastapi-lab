# Legal Intake FastAPI Lab

A public FastAPI project for consultation preparation and legal marketing drafts. The required scope of this repository is **the existing intake/guidance Python actions, nine security actions, and legal-marketing hardening**. The app is capped at **11 HTTP operations**, including the existing MVP.

LangChain, LangGraph, LangSmith, RAG, embeddings, vector search and memvid are **not required here**; they are completed separately in the research multi-agent search-tool repository. (See [7. RAG and search separation](#7-rag-and-search-separation).)

[한국어](README.md) | [English](README.en.md)

## 1. Scope

| Area | In scope | Out of scope (moved to the research repo) |
|---|---|---|
| Intake/guidance | Create/retrieve intake, async guidance from stored facts | Retrieval-grounded guidance generation |
| Security | All nine security actions plus capacity, budget and settlement handling | RAG document inspection and evidence gating |
| Marketing | Posts, reviews, M01 summary, M02 reply draft, `check_marketing_response` | Marketing drafts using retrieval results |
| Retrieval/generation | Existing OpenAI async adapter and fake client | LangChain, LangGraph, LangSmith, E5, memvid, Llama |

**Completion means actions are implemented, integrated and pass tests.** A plan document or a successful sample run is not completion.

## 2. Current status

| Area | Status |
|---|---|
| Root MVP | Three APIs: synchronous create/retrieve and asynchronous guidance; 23 original tests |
| Selected foundation `4fcc698` | Decision DTOs, immutable context, admission manager, budget ledger, risk store |
| L01 NeMo wrapper / L02 context and session risk | Security input-action foundation implemented; real NeMo tests are run separately ([record](docs/L01_L02_IMPLEMENTATION.md)) |
| Nine security actions | Partly implemented; full integration in progress |
| Marketing board and M01/M02 | Planned; failed marketing checks in the recovery snapshot are not treated as completed work |
| RAG/search code | Still in the repository but out of scope here; to be moved to the research repo |

Keep recovery branch `wip/codex-legal-snapshot` separate from `main`.

| Current root API | Execution | Contract |
|---|---|---|
| POST `/api/intakes` | `def` | 201, invalid input 422 |
| GET `/api/intakes/{intake_id}` | `def` | 200, missing intake 404 |
| POST `/api/intakes/{intake_id}/guidance` | `async def` | Stored-fact guidance, provider failure 502 |

In-memory records disappear on restart. Fake/mock tests and real provider verification are recorded separately.

## 3. All nine security actions are required

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

### Marketing hardening: `check_marketing_response`

**M01 summaries and M02 reply drafts must pass `check_marketing_response` after full output inspection**, followed by final masking and context validation. Mark guarantee/exaggeration claims for review and return only a sanitized draft. Never publish externally automatically.

Test normal wording, guarantees, negated/quoted claims, PII and checker failures, including mixed-negation bypass cases. Running the sample does not establish completion of AI security integration.

Internal decisions are `ALLOW/BLOCK/TRANSFORM/REVIEW`; reasons are `reasonCode/detailCode`. Distinguish existing `COST_LIMIT_BLOCKED` and `DYNAMIC_SESSION_BLOCKED` from new proposals. Do not claim complete PII coverage or automated legal-advertising compliance.

## 4. At most 11 application APIs

This is the review target; only the original three are implemented in the root app.

| Group | Operations | Count |
|---|---|---|
| Existing intake | Create, retrieve, guidance | 3 |
| Health | GET `/health` | 1 |
| Posts | POST/GET `/api/posts`, GET `/api/posts/{postId}` | 3 |
| Reviews | POST/GET `/api/posts/{postId}/reviews` | 2 |
| Marketing AI | POST `/api/posts/{postId}/ai-summary`, POST `/api/reviews/{reviewId}/reply-draft` | 2 |
| Total | Method/path combinations | **11** |

The older 21-API design is a historical candidate list. Do not add independent chat/SSE, post edit/delete, standalone guardrail APIs or search APIs. Keep synchronous comparisons in a separate learning app.

## 5. Development order and learning baseline

Order: **finish the nine security actions → service boundaries (capacity, budget, settlement) → posts/reviews → M01/M02 with marketing checks → regression and integration tests.**

Keep the foundational review/reply example brief:

1. In an empty folder: `uv init`, `uv add "fastapi[standard]"`, package folders and `entrypoint = "app.main:app"`.
2. Entity → dictionary repository → DTO → exceptions/handlers → service → dependency functions → router → `main.py`.
3. `uv add pydantic-settings openai` → settings → LLM client → reply service → dependencies → async handler → lifespan. Existing config/client examples may be reused.

Acceptance: `uv run fastapi dev`, three APIs in Swagger/Postman, 201/422/404, a reply based on the saved review and `MainThread` in the real server log. The [separate review example](ohgi-review-server/README.md) is not the root intake app.

Extensions: rating-based tone (1–2 apology/empathy, 3 empathy/improvement, 4–5 thanks), storing inspected replies and returning them on review lookup, and a separate `def`/sync-client comparison. Main M02 remains async and all ratings pass marketing checks.

Never commit `.env`. For foundational learning, construct and explain the layers yourself; use AI for data structures, syntax and error interpretation. Consult existing HOWTO-chap01/02/03 notes as needed.

## 6. Run the current MVP

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

Verify real OpenAI credentials and model access separately. The [L01/L02 record](docs/L01_L02_IMPLEMENTATION.md) describes the dedicated security runtime and full test procedure.

## 7. RAG and search separation

The following are **collected and completed separately in the research multi-agent search-tool repository**. Do not add them here.

- LangChain, LangGraph, LangSmith
- RAG, embeddings (E5), vector search, memvid
- Llama generation adapter and synthetic-document retrieval evaluation

Candidates to move (re-verify paths at move time):

| Area | Path |
|---|---|
| App code | `app/rag/` |
| Runtime | `rag-runtime/` |
| Scripts | E5/memvid/retrieval-evaluation files under `scripts/` |
| Data and tests | `fixtures/rag/`, `tests/rag/`, `tests/test_rag_b03_b05.py` |
| Docs | `docs/RAG_*.md`, `docs/CLAUDE_RAG_DESIGN_REVIEW.md`, `docs/EMBEDDING_RETRIEVAL_STUDY.md`, `docs/evidence/` |

Until the move is complete these files remain in the repository but **are not part of this repository's completion criteria.** Afterwards the research repo can reuse the security actions as a shared module if needed.

## 8. Repository roadmap

| Order | Role |
|---|---|
| ① `legal-intake-fastapi-lab` (this repo) | Validate intake, security and marketing features in standalone FastAPI |
| ③ [`langchain-rag-research-agent`](https://github.com/ai-agent-orchestrator/langchain-rag-research-agent) (formerly python-memvid-guardrail) | Extract validated security components as reusable modules |
| ② `spring-fastapi-async-refactor` | Connect Spring authentication/authorization to FastAPI AI services |
| Research multi-agent repo | Complete the LangChain/LangGraph/RAG search tool separately |
| Later | Separate private commercialization |

Keep ① → ③ → ②. Authentication/authorization, automatic publishing, general web search, operational DBs and Redis/Celery/Kafka are outside this phase. Do not modify the existing Java service or database.

## References

- [Security migration target](docs/SECURITY_MIGRATION_PLAN.md) · [Marketing board contract](docs/LEGAL_MARKETING_BOARD.md)
- [Local L01/L02 scope and verification record](docs/L01_L02_IMPLEMENTATION.md)
