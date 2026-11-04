# Agreed scope: option 1 today, extensions on the weekend

- **Today (2026-11-04):** Complete option 1: synchronous intake creation/retrieval and asynchronous AI guidance, limited to three APIs. Implementation and 23 fake/mock tests are complete. The real OpenAI adapter is included, but paid API calls remain unverified.
- **Weekend:** Review the MVP first, then add small increments starting with PII masking and input/output checking Python actions. NeMo integration, SSE, and the asynchronous board remain follow-up candidates; completing all of them in one weekend is not the agreed scope.
- **Implementation scope:** Keep today's implementation within the MVP and defer extensions to the weekend. Authentication and authorization are excluded from this implementation.

This small scope makes synchronous/asynchronous execution, dependency injection, and exception handling visible in one complete flow: create an intake, retrieve it, and generate guidance from its stored facts. Adding security actions and streaming individually later makes their effects and failures easier to compare.

[한국어](README.md) | [English](README.en.md)

## 1. Repository roadmap — ① → ③ → ②

| Order | Repository | Purpose |
|---|---|---|
| First, current ① | **`legal-intake-fastapi-lab`** | Review the course HOWTOs, experiment with FastAPI, and adapt selected Legal Intake functionality |
| Second ③ | **`legal-intake-hybrid-lab`** | Connect Spring Boot authentication/authorization to FastAPI AI services and verify service boundaries |
| Third ② | **`legal-intake-ai-service`** | Develop verified functionality into reusable AI services and address operational requirements |

Validated code, contracts, and tests can move into the next stage. This roadmap does not mean the later repositories have been implemented or deployed.

## 2. Reuse the existing Legal Intake design — 11 selected APIs

Reuse API contracts, processing rules, reason codes, and test cases from the existing Legal Intake design. **Select only the following 11 of the original 37 APIs; exclude 26.** This is a plan to port contracts and logic into FastAPI, not to execute Java code directly. It is separate from the three implemented MVP endpoints.

| ID | Selected API | Reuse |
|---|---|---|
| C02 | `POST /api/intakes/classify-preview` | Classification/guidance rules |
| C04 | `POST /api/legal-intake/minimal` | Minimal intake guidance |
| R01 | `GET /api/legal/procedures` | Procedure list fixture |
| R02 | `GET /api/legal/procedures/{code}` | Procedure detail fixture |
| R06 | `GET /api/legal/criminal/checklist/supplementary-investigation` | Fixed criminal checklist |
| S01 | `POST /api/ai/chat` | Port the JSON Chat contract to async processing |
| S02 | `POST /api/ai/chat/stream` | Inspect the full response before SSE publication |
| S03 | `POST /api/legal/guardrail/input` | Python/NeMo input checks |
| S04 | `POST /api/legal/guardrail/output` | Python/NeMo output checks |
| C13 | `GET /api/lab/marketing/summary` | Reduce the original marketing query to post/review aggregates |
| C14 | `GET /api/lab/security-events` | Reduce security-event queries to an in-memory lab view |

This section covers **only the 11 APIs selected from the existing design**. New health, board, review, AI marketing APIs, and the security-action expansion belong in section 3 below.

Excluded for this experiment: Spring login/JWT/roles, operational case storage, external search, file storage, Agent/Incident operations, Actuator/Prometheus, Redis, Celery, Kafka, RAG/memvid, OCR, and automatic publishing. The existing Java service/database is not modified. See the [detailed design](docs/BACKEND_DESIGN.md) for the full ID mapping and exact paths.

## 3. Future expansion — nine NeMo security Python actions

**Migration scope:** all nine actions below, not only the first three learning examples, belong in the FastAPI target. Login, JWT, roles, and resource ownership authorization are excluded. Settlement, slot release, and cancellation cleanup remain service responsibilities. See the [full flowchart](docs/assets/security-migration.svg) and [migration explanation](docs/SECURITY_MIGRATION_PLAN.md).

An action is an executable check. A `reasonCode` is a value explaining a decision. Existing reason codes are preserved where applicable; they are not renamed into functions.

| Action | Responsibility |
|---|---|
| `validate_request_context` | Bind request, target snapshot, and response; detect mixed A/B context |
| `check_session_risk` | Inspect accumulated session risk and existing block state |
| `check_input_policy` | Check harmful requests, jailbreaks, injection, secrets, and privacy risks |
| `mask_personal_data` | Replace defined PII patterns before storage, external transmission, or publication |
| `check_generation_admission` | Enforce bounded concurrency, waiting capacity, and waiting timeout |
| `check_request_budget` | Atomically check and reserve budget under a short lock |
| `check_output_policy` | Inspect complete output for empty/oversized or disallowed content |
| `check_marketing_response` | Flag guarantee/exaggeration wording for human review |
| `record_risk_event` | Record a confirmed policy block once |

The context and admission actions extend the original seven into **nine accepted designs**, not nine implemented actions. Admission precedes budget reservation so waiting requests do not unnecessarily hold funds. A single-worker example uses two active calls, four waiters, and a 0.5-second waiting limit; those values are not operational guarantees.

Timeout, disconnect cleanup, settlement, and slot release must be enforced by the service's `finally` path, not depend on a later action running successfully. Python `await` and NeMo's `execute_async` option are different; required check results must be available before generation starts.

Internal policy decisions are ALLOW/BLOCK/TRANSFORM/REVIEW with `reasonCode/detailCode`. Context mismatch and overload are technical errors, not attack scores. Action unit tests and actual NeMo rail integration tests must be distinguished. Pattern masking does not guarantee complete PII detection, and marketing checks are not automatic legal-compliance judgments.

**Marketing inspection remains mandatory for the expansion's M01/M02.** Inspect the complete output, mark review requirements, publish only a safe draft, and never automatically post it externally. Test normal wording, guarantees, negation/quotation, PII, and checker failure. These actions are intentionally not added to the small review coursework reference or current MVP.

### Ten new APIs and the overall target

| New area | APIs | Count |
|---|---|---|
| Health | H01 `GET /health` | 1 |
| Legal marketing board | B01–B05: create/list/detail/update/delete under `/api/posts` | 5 |
| Service-experience reviews | B06–B07: create/list under `/api/posts/{postId}/reviews` | 2 |
| AI marketing | M01 `POST /api/posts/{postId}/ai-summary`; M02 `POST /api/reviews/{reviewId}/reply-draft` | 2 |

**11 selected existing APIs + 10 new APIs = a 21-API expansion target.** The nine Python actions are internal checks, not additional HTTP endpoints. The three current intake MVP APIs and three review-reference APIs are separate contracts and are not added to this count. Board/marketing work belongs to the subsequent lab implementation; authentication and authorization are excluded.

### Advanced legal marketing board — weekend extension goals

Adapt the review exercise's three advanced tasks to **service-experience reviews and law-firm reply drafts**. These are planned extensions, not implemented features.

| Exercise | Planned behavior | Acceptance criteria |
|---|---|---|
| Rating-based tone | Apology/empathy for 1–2, empathy/improvement for 3, gratitude for 4–5 | Rating boundaries verified; marketing inspection applies to every rating |
| Save and retrieve drafts | Save M02's inspected, finally masked draft and review status; include them in B07 review lists | Generated draft appears on read; checker failures are not saved; no automatic external publication |
| Compare sync/async | Keep M02 async with an async client; add a separate experiment using def and a sync client | Same inputs/fake delay, two Postman tabs, thread and concurrent-request observations |

The synchronous comparison endpoint is a separate learning experiment outside the base 21-API target. Enabling one additional endpoint in the same app makes the total 22. FastAPI runs def handlers in a thread pool; one blocking handler does not imply that the entire server stops. See the [detailed advanced design](docs/LEGAL_MARKETING_BOARD.md) in Korean.

## 4. Implemented scope: two synchronous APIs and one asynchronous API

The selected MVP adapts the review exercise's processing structure to Legal Intake. It is a small learning contract, not a fully compatible replacement for the existing Spring intake API.

| Current API | Handler | Behavior |
|---|---|---|
| `POST /api/intakes` | `def` | Create an intake from `clientName`, `caseType`, `coreStatement`, and optional `desiredNextStep`; 201 or 422 |
| `GET /api/intakes/{intake_id}` | `def` | Return a camelCase intake; 200 or custom 404 |
| `POST /api/intakes/{intake_id}/guidance` | `async def` | Build a prompt from stored facts, await the LLM, and return guidance; 200 or 502 on provider failure |

The dictionary repository uses a short thread lock. The asynchronous guidance service offloads its snapshot lookup with `to_thread`. The client's name is excluded from the AI prompt. Automatic masking of all narrative PII, NeMo, budgets, SSE, authentication, and persistent storage are **not implemented in this MVP**. Use synthetic data. Restarting the server clears stored intakes.

### Review coursework contract

The separate `ohgi-review-server/` follows the supplied structure: `main`, dependencies, configuration, exceptions, dataclass domain, dictionary repository, schemas, clients, services, and routers. Application packages contain empty `__init__.py` files.

| Review API | Handler | Verified behavior |
|---|---|---|
| `POST /api/reviews` | `def` | `customerName`, integer rating 1–5, and content; 201 or 422 |
| `GET /api/reviews/{review_id}` | `def` | camelCase response or a custom `ReviewNotFoundError` mapped to 404 |
| `POST /api/reviews/{review_id}/reply` | `async def` | Stored review → prompt → awaited LLM → reply; `AiRequestError` mapped to 502 |

### Instructor's construction sequence

1. In an empty exercise directory: `uv init`, add `fastapi[standard]`, create packages and empty `__init__.py` files, then configure the entrypoint.
2. Domain entity → dictionary repository → DTOs → exceptions and handlers → review service → dependencies → router → application assembly.
3. Add `pydantic-settings` and `openai` → settings → LLM client → reply service → dependencies → async handler → lifespan.

Chapter 02 configuration and client code can be used as references. Compare independently written code with the study reference in this order.

Live fake-mode Uvicorn checks confirmed `/docs`, the expected status codes, synchronous handlers on `AnyIO worker thread`, and the reply on `MainThread`. Independent-environment startup, manual Postman interaction, and actual paid provider calls are separate checks. Rating-dependent tone, persisted replies, and an additional synchronous LLM endpoint remain optional exercises and have not been added.

### Legal marketing board: three required learning actions

Adapt the restaurant review sample to **law-firm posts, service-experience reviews, and reply drafts for human review**. Preserve `ohgi-review-server/` as the course comparison reference. The legal marketing board is a weekend extension, separate from today's three-endpoint intake MVP.

| Priority Python action | Purpose | Placement |
|---|---|---|
| `mask_personal_data` | Replace defined PII patterns, including phone numbers and email addresses | Before storage, before AI transmission, and before returning text |
| `check_request_budget` | Port existing cost controls into atomic checking/reservation and settlement | Before each paid M01 summary or M02 reply-draft call |
| `check_marketing_response` | Flag guarantees of success and exaggerated wording for review | After generation, before final masking and response |

Flow: post/review → mask and store → reserve budget → await OpenAI → output/marketing checks → final masking → return a review draft and settle costs. Exceeded budgets prevent generation; failed mandatory checks prevent output release. Response fields such as `reviewRequired` are proposed extension contracts, not current MVP fields. Drafts are not published automatically.

These three actions are the first learning subset of the existing nine-action design. They do not replace the full design. **NeMo actions are not installed or implemented yet; implementation is planned for the weekend.** See the [domain mapping, rationale, and acceptance criteria](docs/LEGAL_MARKETING_BOARD.md) in Korean.

### Subsequent expansion: design only

The root MVP's three APIs, the review reference's three APIs, and the planned expansion's 21 APIs have separate contracts and implementation states. The future board and AI services are designed around asynchronous handling; this does not change the current synchronous MVP requirements.

```text
Swagger / browser
 → Uvicorn / ASGI
 → FastAPI: trace, Pydantic, Depends, APIRouter
 → request context, session risk, input policy, PII masking
 → generation capacity → budget reservation
 → await OpenAI
 → usage settlement, output/marketing checks, final masking
 → response binding → JSON or inspected SSE
 → finally: close remaining reservations and release execution slots
```

In the future implementation, nonblocking AI I/O uses `await`, fake latency uses `asyncio.sleep`, and SSE uses async generators. Short validation and rules run locally. Synchronous I/O must not be called directly inside async handlers. Async declarations do not accelerate CPU-bound work. Future shared state uses short protected sections, and any added database requires a deliberate driver/session choice.

The current environment is localhost, one user, synthetic data, and one worker. Spring Boot, JWT, login, and role permissions are excluded for now. They belong to the hybrid stage. A `sessionId` and a content-checking action are not authentication.

## 5. Course HOWTO chapters and their application

The course grows **one project through chap01 → chap02 → chap03**. It uses menu data to teach structure and verification; this repository applies those concepts to intakes and the planned board features.

The locally reviewed course revision is **2026-11-04 / `f1928c8`**, under `C:\myLectureWs\08_fastapi-main\howto`. Course access may require permission. Full course source is not duplicated here.

### Chapter 01 — application structure

| Topic | Course concept | Application here |
|---|---|---|
| uv and environments | `pyproject.toml`, `.venv`, `uv.lock`, interpreter selection | Isolated and reproducible dependencies |
| Packages and entrypoint | `app/`, package markers, `app.main:app` | Explicit startup and module boundaries |
| Domain objects | Python entities | Immutable intake/review records |
| Repository | Dictionary create/read behavior rather than a database | Small in-memory experiments |
| Pydantic DTOs | Separate request/response models and validation | Types, lengths, required fields, and 422 responses |
| Aliases | snake_case internally, camelCase in JSON | Consistent API field names |
| Exceptions | Custom exceptions mapped to HTTP and JSON | 404, 422, and provider failure contracts |
| Services | Injected repositories and business processing | Keep routing separate from processing order |
| `Depends` / `Annotated` | Dependency trees and replaceable components | Swap real/fake clients in tests |
| Routers and assembly | Prefixes, routes, status codes, handlers | Explicit application wiring |
| Swagger / Postman | Inspect bodies, responses, and errors | Verify APIs before building a UI |

The course menu example has three endpoints: `GET /api/menus`, `GET /api/menus/{menu_code}`, and `POST /api/menus`. It covers an initial list, successful lookup, custom 404, invalid path/body 422, and creation 201. It is not a complete update/delete CRUD sample.

The basic flow is Router → Service → Repository → response DTO. FastAPI resolves declared dependencies but does not automatically discover Spring-style service beans. Per-request dependency caching differs from application-wide shared objects. Read custom `code/description/detail` errors and Pydantic's `loc`. Reloading or restarting resets dictionary data. Pyrefly search paths help the editor; they do not install runtime dependencies.

### Chapter 02 — configuration and synchronous/asynchronous LLM calls

| Topic | Main lesson |
|---|---|
| Settings | `BaseSettings`, `SecretStr`, environment variables, `.env`, defaults, model/timeout/limits |
| Reuse | `lru_cache` avoids repeatedly reading settings; changes require restart |
| Clients | Compare synchronous OpenAI calls with `AsyncOpenAI` and awaited responses |
| Fake client | Same interface with predictable responses and latency, without network costs |
| Coroutines | Calling an async function alone does not return its completed result |
| Lifespan / app.state | Create/share clients on startup and close them on shutdown |
| Dependency injection | Wire client → service → router and replace components in tests |
| Error mapping | Distinguish key, limit, connection, timeout, and policy failures |
| Observation | Inspect thread names, duration, model, and reported usage |

The course sends the same `{"question":"..."}` body to three endpoints:

| Course endpoint | Implementation | While waiting |
|---|---|---|
| `/api/ai/ask/sync` | `def` + synchronous client | Occupies a thread-pool worker |
| `/api/ai/ask/async` | `async def` + async client + `await` | Allows other ready work to run |
| `/api/ai/ask/blocking` | `async def` + synchronous client | Blocks the event loop; an intentionally incorrect example |

The first course experiment tests whether menu queries can respond during a five-second fake AI wait. The second sets `THREAD_POOL_SIZE=1` to compare thread-pool waiting with overlapping async waits. The course's default 40 refers to AnyIO limiter tokens, not a universal throughput ceiling.

Course `question`, the future chat request's `message`, and the MVP's saved `coreStatement` are different contracts. The MVP guidance endpoint takes an intake ID and no additional request body. Comparison-only blocking/synchronous LLM endpoints are not part of the MVP.

Unlike the course's missing-key fake fallback, this implementation uses an explicit fake/real setting and refuses real-client startup without a key. Provider/model access still needs verification. Do not commit `.env`; environment variables may override it, and changes require restart. An LLM does not automatically know application data: stored facts must be deliberately supplied. RAG/memvid remains outside the current scope.

### Chapter 03 — tests, coverage, and benchmarks

| Topic | Main lesson and planned application |
|---|---|
| pytest configuration | Development dependencies, `testpaths`, and `pythonpath` |
| `conftest` / fixtures | Per-test setup, yield cleanup, and isolated state |
| `dependency_overrides` | Replace provider components and remove overrides afterwards |
| Unit tests | Inject components, use assertions and `pytest.raises` |
| API tests | TestClient response codes, JSON contracts, and validation errors |
| Parameterization | Repeat normal, invalid, and security cases |
| Async tests | Await inside an existing loop; separate async concurrency verification |
| Fault injection | Failing providers, timeouts, and cancellation |
| Coverage | Code exercised by tests; not proof that paid providers work |
| Benchmarks | AsyncClient and `gather` against a running server |

The HOWTO's **20-passed example belongs to the course**, not this application's results. This MVP has 23 passing tests. Fake providers intentionally leave some real-network code unexecuted. A high coverage number alone does not prove completeness.

`asyncio.run` is suitable at standalone synchronous script/test entrypoints, not inside a handler whose loop is already running. Manage lifespan explicitly when the test requires it. A basic TestClient test and an actual async concurrency test have different purposes. TestClient can call ASGI in memory; the course benchmark requires a live server and two terminals.

| Metric | Meaning |
|---|---|
| Total duration | Completion time for a request batch |
| p50 | Median latency |
| p95 | Approximately 95% of requests complete within this latency |
| Maximum | Slowest request |
| RPS | Completed requests per second |
| Failures | Non-success status, connection error, timeout, etc. |

The benchmark uses fake mode and fixed latency, checks that the server is fake, sends 100 requests each to sync/async and ten to blocking, and distributes load across five clients. Use `127.0.0.1` to avoid irrelevant address-resolution effects. Do not compare total duration alone across different batch sizes. Check whether the load generator is the bottleneck. Instructor measurements are not guaranteed performance for another machine.

## 6. Planned Legal Intake expansion

| Area | Intended behavior |
|---|---|
| Classification, minimal guidance, references | Rules and fixed fixtures without AI |
| Chat, summaries, classifications, reply drafts | Shared asynchronous AI pipeline |
| Input security | Session risk, fixed policies, masking |
| Costs | Stage-specific reservation, reported/estimated settlement, single closure |
| Output security | Full-output inspection, marketing review, final masking |
| SSE | Inspected chunks and disconnect cleanup |

The planned migration reuses Java contracts, rules, reason codes, and test scenarios; it does not execute Java inside Python. The actual source reference is `legal-ai-intake-security-server`. The local `legal-ai-intake-system` directory mainly contains introductory documentation.

## 7. Cost, SSE, and error rules — expansion design

- Separate paid input inspection, generation, and output inspection; each needs its own accounting boundary when enabled.
- Atomically check/reserve; close OPEN exactly once as REPORTED, ESTIMATED, or RELEASED.
- Release on cancellation before the provider starts. Estimate after the call starts if usage is unknown; do not report unknown usage as zero cost.
- Settle incurred usage even if output is blocked, the request times out, or the client disconnects.
- Use bounded admission before reserving budget. Do not classify overload/context failures as malicious behavior.
- Preserve camelCase and normalize errors/logs to avoid raw PII leakage.
- SSE success is `meta → inspected token chunks → done`; policy blocks end with `blocked`, technical failures with `error`.
- The first version buffers and inspects the entire response before sending safe chunks. Async handling does not require exposing uninspected tokens.
- Read POST SSE with fetch. After headers are sent, report failures through events instead of changing the HTTP status.
- Do not delegate required checks/accounting to BackgroundTasks. An in-memory ledger is not a provider billing cap.

## 8. Review specification and board integration

The supplied review API/folder specification is implemented in `ohgi-review-server/`. Full upstream project source has not been claimed to have been cloned. The larger board/marketing integration follows this sequence:

1. Check source, README, execution requirements, and reuse conditions.
2. Inspect models, CRUD, storage, dependencies, and tests.
3. Compare with chap01 and finalize B01–B07 fields, paths, and responses.
4. Confirm asynchronous persistence boundaries; keep comparison/coursework code separate.
5. Verify masking before storage, read contracts, and missing-ID errors.
6. Connect M01/M02 to the shared AI pipeline and mandatory marketing action.
7. Define C13 summaries using data actually implemented.
8. Update contracts, diagrams, study notes, and README.

Review/post text is analysis data, not a system instruction. Drafts are for review; automatic external publishing is excluded. Do not expand the simple coursework server into the full operational security system.

## 9. Current status

| Item | Status |
|---|---|
| **Root Legal Intake MVP** | Implemented; sync create/read plus async guidance; 23 tests passed |
| Project environment | Python 3.14, project `.venv`, dependencies, and `uv.lock` prepared |
| Live MVP server | Started through `uv run --no-sync fastapi dev`; fake HTTP and `MainThread` verified |
| Postman collection | Prepared; manual execution in Postman has not been verified |
| Review reference | Three endpoints implemented; 11 fake/mock tests passed |
| Review live checks | `/docs`, create/read/reply, 422/404, worker-thread sync and MainThread async verified |
| Course source | Local revision `f1928c8` reviewed |
| Documentation | Korean/English README, eight design screens, beginner notes, eight review questions |
| Async waiting example | Observed roughly 3.01 s sequential and 1.01 s concurrent; not a server benchmark |
| Old separate chap02 exercise | Environment, fake endpoints, validation, and Swagger previously checked |
| Real paid OpenAI call | Not verified |
| 21-API expansion and nine NeMo actions | Design only; NeMo installation/compatibility not verified |
| Spring integration / deployment | Later stages |

Python 3.14 runs the MVP. NeMo compatibility must be checked independently; a separate compatible Python environment may be required. The root MVP, review reference, and future expansion are distinct implementation scopes.

## 10. Run the implemented code

### Legal Intake MVP

From a terminal in the repository root:

```powershell
uv sync --python 3.14
uv run fastapi dev --host 127.0.0.1 --port 8012
```

Open [Swagger](http://127.0.0.1:8012/docs). Do not start a second server on the same occupied port. If uv cache/Python lookup prevents startup after installation, use:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012
```

Create an intake:

```json
{
  "clientName": "Practice client",
  "caseType": "CIVIL",
  "coreStatement": "I am preparing documents for a deposit-return consultation.",
  "desiredNextStep": "Prepare consultation materials"
}
```

Use the returned `intakeId` for lookup and `POST /api/intakes/{id}/guidance`, without another body. Accepted case types are CIVIL, CRIMINAL, FAMILY, OTHER. Name length is 1–50, core statement 1–100, and the optional next-step field at most 100 characters. Responses use camelCase.

The default `.env.example` selects fake mode. If using a fresh clone, create a local `.env` as needed; it is ignored by Git. In fake mode, `model=fake-llm` is an explicit simulation. To try a real call, configure `FAKE_LLM=false`, your local `OPENAI_API_KEY`, and an accessible `OPENAI_MODEL`, then restart. Missing keys fail real-client startup. The sample model is not a promise of account access. The narrative is not comprehensively PII-masked, so use synthetic cases.

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The root tests isolate providers and make no real OpenAI calls. Import the [Postman collection](docs/legal-intake-mvp.postman_collection.json) for the five example requests. The [runbook](docs/RUN_MVP.md) explains each step.

### Review reference

This is a separate application with its own entrypoint:

```powershell
cd ohgi-review-server
uv sync --python 3.14
uv run fastapi dev --port 8011
```

Use `/docs` on port 8011. Send `customerName`, rating 1–5, and content to create a review, then request its reply. Its directory contains the detailed [reference README](ohgi-review-server/README.md), unittest instructions, and a localhost fake-mode verification script. Optional advanced exercises remain unimplemented.

### No-cost asyncio example

From the repository root with Python installed:

```powershell
python examples/async_wait_demo.py
```

The earlier local `fastapi-openai-practice` directory is not included in this repository. On the original study PC, that separate exercise runs on port 8001 and accepts `question`; do not confuse it with either application above.

## 11. Course command reference

These are course commands, not instructions to reinitialize the existing repository. Run `uv init` only in a separate empty directory.

| Step | Command |
|---|---|
| New chap01 project | `uv init --no-package --python 3.14` |
| FastAPI | `uv add "fastapi[standard]"` |
| chap02 | `uv add pydantic-settings openai` |
| chap03 | `uv add --dev pytest pytest-cov` |
| Existing starter/complete environment | `uv sync --python 3.14` in that chapter directory |
| Server | `uv run fastapi dev` |
| Tests | `uv run pytest`, `uv run pytest -v` |
| Coverage | `uv run pytest --cov=app` |

The entrypoint setting is `[tool.fastapi] entrypoint = "app.main:app"`. The pytest section specifies `testpaths = ["tests"]` and `pythonpath = ["."]`.

For the course benchmark, use two terminals in its `complete/chap03_test_benchmark` directory, not this MVP directory:

```powershell
# Terminal 1: course server, default port 8000
$env:FAKE_LLM="true"
$env:FAKE_LLM_DELAY_SECONDS="1"
uv run fastapi dev
```

```powershell
# Terminal 2: course load generator
uv run python benchmark/benchmark.py
```

Stop with Ctrl+C. Environment variables remain in that terminal session; reset them explicitly or open a new terminal before real-provider experiments. On the original PC, a broken uv Python shortcut was resolved by supplying the installed Python executable directly. No API keys belong in source control.

## 12. Implementation and review checkpoints

### Next implementation goals after today's MVP

Completed: the three-endpoint MVP and 23 tests. Weekend/later work proceeds through **shared foundations → nine actions and actual NeMo rails → common AI pipeline → real OpenAI verification → legal marketing board and inspected SSE**. Redis/DB persistence and multiple workers follow later. Authentication and authorization are excluded. Each milestone's acceptance criteria are in the [migration plan](docs/SECURITY_MIGRATION_PLAN.md).

1. Explain chap01 layers and a request's path.
2. Compare chap02 handlers, then verify fake async guidance.
3. Inspect stored facts passed to the provider and error conversion.
4. In the expansion, add input/context/masking, capacity, budget, output, and cleanup in that order.
5. Extend chap03-style tests with concurrency/cancellation cases.
6. Verify safe SSE publication before enabling streaming.
7. Integrate board samples and marketing policies.
8. Run fake load experiments and update documentation before hybrid integration.

- [x] Selected MVP: synchronous intake create/read and asynchronous guidance implemented; 23 tests and live fake HTTP checked.
- [x] Review reference: synchronous create/read, asynchronous reply, and fake/mock 201/422/404/502 checks.
- [ ] Real OpenAI account/model access and response verified.
- [ ] Manual Postman verification recorded separately.
- [ ] Expansion's NeMo actions unit-tested and actual rails integration-tested.
- [ ] Request contexts stay isolated; capacity/queue limits and cancellation cleanup verified in the expansion.
- [ ] Budget reservations, duplicate settlement, pre/post-call cancellation, and blocked-output usage verified.
- [ ] SSE never exposes uninspected content or duplicate terminal events.
- [ ] Production-style logging/errors/health do not reveal raw secrets or PII.
- [ ] Board source, modifications, and B/M contracts finalized.
- [ ] M01/M02 cannot bypass the marketing inspection.
- [ ] Documentation reproduces the implemented experiments.

Review in this order: **architecture → async/DI → security/costs/SSE**. Read the course source, locate its counterpart in this design, and confirm behavior through examples/tests. Do not treat planned features as implemented.

## 13. Source references and local study material

The original PC used `C:\myLectureWs` as its workspace. These sibling directories are not created by cloning this repository:

| Local resource | Purpose |
|---|---|
| `08_fastapi-main/howto/HOWTO-chap01.md` | Project structure, DI, basic APIs |
| `08_fastapi-main/howto/HOWTO-chap02.md` | LLM settings and sync/async experiments |
| `08_fastapi-main/howto/HOWTO-chap03.md` | Tests, coverage, benchmarks |
| `08_fastapi-main/complete` and `starter` | Completed examples and exercise scaffolds |
| `fastapi-openai-practice` | Earlier fake LLM environment and local instructions |
| `legal-ai-intake-security-server` | Java implementation and API specifications |
| `legal-ai-intake-system` | Existing service overview |

This README summarizes key course topics and their application. It is not a replacement for the complete original HOWTOs or source. Review course access/reuse conditions before redistributing course material.

- [Academy repository](https://github.com/20260728-saltlux-llm-agent-service-1st/08_fastapi)
- [FastAPI async](https://fastapi.tiangolo.com/async/) · [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) · [Lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [Official OpenAI Python documentation](https://developers.openai.com/api/reference/python)
- [NeMo custom actions](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/actions/creating-actions)
