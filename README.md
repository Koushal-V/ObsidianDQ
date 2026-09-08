# Hybrid Agentic Data Quality Investigation and Remediation System

ObsidianDQ is a local data-quality investigation app. A FastAPI backend runs a LangGraph workflow over CSV or Parquet files, optional SQL, and a lineage JSON file. A Next.js dashboard shows the run, evidence, proposals, and approval state.

This is a **Hybrid Agentic Data Quality Investigation and Remediation System**. It uses deterministic code for data quality detection and pipeline stages (profiling, lineage traversal, SQL repair, quarantine, and re-checking). LLM-based agents provide investigation with dynamic tool selection, root-cause reasoning, planning, triage, and criticism. The graph supports feedback/loop-based investigation and remediation, human-in-the-loop approval for risky actions, and verification after remediation.

LLM agents inspect evidence and propose decisions. They do not execute row changes or SQL writes.

When an LLM call is missing or fails, agents keep going with documented fallbacks. Triage without an LLM proposal flags every issue for human review. The critic currently **approves** on LLM failure rather than blocking the run. Failed post-remediation verification is recorded as `VERIFICATION_FAILED` and still continues to guardrails.

## What is implemented

- Profile CSV and Parquet datasets (row counts, column stats).
- Detect `NOT_NULL`, `NO_DUPLICATES`, `PRICE_NON_NEGATIVE`, `VALID_STATUS`, `UNIQUE_ORDER_ID`, and `ORDER_DATE_RANGE` (dates before `2020-01-01`).
- Walk a local lineage graph for upstream candidates and downstream blast radius.
- Groq tool-using investigation (sample rows, column stats, lineage, similar incidents). Gemini is used for some later agents when Groq is not configured; investigation tool-calling is Groq-only.
- Root-cause, planning, triage, and critic nodes produce reviewable JSON/state, not side effects.
- Human approval via a LangGraph interrupt when plan risk is `HIGH`, a proposal is `FLAG_FOR_REVIEW`, or confidence is below `0.7`.
- After critic approval or human approve: SQL healer, then remediation, then verification on the cleaned file.
- Local incident memory and run history stored in DuckDB (`data/obsidiandq.duckdb`).
- Dashboard: upload, confirmation ticket, staged run animation, then the run console.

The demo dataset and lineage live under `data/raw`, `data/queries`, and `data/lineage`. This is not a warehouse or production orchestrator.

## Workflow

The compiled graph in `src/agent/graph.py` is:

```text
START
  -> stage_profile
  -> dq_detect
  -> lineage_rca
  -> investigation_agent
  -> root_cause_agent
  -> planning_agent
  -> triage_agent
       |-- no issues            -> guardrails
       |-- escalate (once)      -> root_cause_agent
       |-- otherwise            -> critic_agent
  -> critic_agent
       |-- revision or escalate -> investigation_agent  (critic retry count <= 1)
       |-- human review         -> interrupt -> human_review_queue
       |-- auto remediate       -> sql_healer
       |-- no issues            -> guardrails
  -> sql_healer -> remediation -> verify_agent
       |-- passed               -> guardrails
       |-- failed               -> verification_recovery -> guardrails
  -> END

human_review_queue (after approve) -> sql_healer
human_review_queue (after reject)  -> END
```

The graph uses an in-memory `MemorySaver` checkpointer and `interrupt_before=["human_review_queue"]`. API run state is also in-process (`RUN_STATES` in `backend/main.py`). Restarting the backend or using multiple workers loses paused runs.

### Agents and nodes

| Node | What it does | If the LLM is unused or fails |
| --- | --- | --- |
| Investigation | Groq may call read-only tools over several turns. | Deterministic samples, lineage, and memory search; marked as fallback evidence. |
| Root-cause | Interprets investigation + lineage. | Lineage ancestor heuristic; `upstream_causality_proven` stays unproven. |
| Planning | Structured plan that must include `INVESTIGATE`, `SQL_HEAL`, `QUARANTINE`, `VERIFY`. | Fixed four-step baseline plan. Risk still comes from issue severity. |
| Triage | Proposes `AUTO_QUARANTINE`, `FLAG_FOR_REVIEW`, `IGNORE_TRANSIENT`, or `ESCALATE_UPSTREAM`. | Every uncovered issue becomes `FLAG_FOR_REVIEW` with confidence `0.0`. |
| Critic | `APPROVED` or `REVISION_REQUIRED`. | Defaults to **`APPROVED`**. |
| SQL healer | Deterministic parse/validate/repair. | Not an LLM. |
| Remediation | Applies proposals; writes quarantine and cleaned files. Source file is not overwritten. | Uses whatever proposals are in state. |
| Verify | Re-runs `detect_dq_issues` on the cleaned path. Passes only if remaining issue count is `0`. | Always deterministic. |

`AUTO_QUARANTINE` and `IGNORE_TRANSIENT` change what remediation does to rows. Human approval unblocks the **pipeline**, not a single issue.

## LLM providers

`src/agent/utils/llm.py` prefers Groq when `GROQ_API_KEY` is set, then Gemini (`GEMINI_API_KEY` or `GOOGLE_API_KEY`). Default Groq model is `openai/gpt-oss-20b` unless `GROQ_MODEL` is set. Temperature is `0.1`. Groq text generation retries up to three times on rate limits.

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b

# optional fallback if Groq is not configured
GEMINI_API_KEY=your_key_here
```

`GET /api/health` returns `llm_provider` and `llm_available`. Each pipeline response includes `agent_execution` for **root-cause, triage, and critic only** (investigation and planning flags exist on state but are not in this object):

```json
{
  "mode": "LLM_AGENT_FIRST",
  "llm_used": true,
  "fallback_used": false,
  "llm_agents": {
    "root_cause": true,
    "triage": true,
    "critic": true
  }
}
```

`llm_used` is true if any of those three completed through an LLM. `fallback_used` is true if any of the three did not.

## Application structure

### Backend

| Path | Responsibility |
| --- | --- |
| `backend/main.py` | FastAPI: health, upload, run, approve, quarantine; formats dashboard JSON. |
| `src/agent/graph.py` | LangGraph nodes, routing, interrupt, `run_pipeline`. |
| `src/agent/state.py` | Shared `AgentState`. |
| `src/agent/nodes/stage_profile.py` | Profiling. |
| `src/agent/nodes/dq_detect.py` | Rule-based issue list. |
| `src/agent/nodes/lineage_rca.py` | Lineage graph. |
| `src/agent/nodes/investigation_agent.py` | Tool-using investigation. |
| `src/agent/nodes/root_cause_agent.py` | Root-cause conclusion. |
| `src/agent/nodes/planning_agent.py` | Reviewable remediation plan. |
| `src/agent/nodes/triage_agent.py` | Per-issue proposals and routing hints. |
| `src/agent/nodes/critic_agent.py` | Approve or request revision. |
| `src/agent/nodes/sql_healer.py` | Constrained SQL repair. |
| `src/agent/nodes/remediation.py` | Quarantine / cleaned outputs. |
| `src/agent/nodes/verify_agent.py` | Post-remediation DQ on the cleaned file. |
| `src/agent/nodes/guardrails.py` | Final safety fields; appends incident memory. |
| `src/agent/utils/llm.py` | Provider selection and generation. |
| `src/agent/utils/memory.py` | JSONL incident memory. |
| `evaluation/run_controlled_benchmark.py` | Offline vs live-Groq controlled incidents. |

### Frontend

| Path | Responsibility |
| --- | --- |
| `frontend/app/page.tsx` | Upload → ticket → run animation → console. |
| `frontend/app/components/UploadStep.tsx` | Dataset, SQL, lineage upload or demo preset. |
| `frontend/app/components/PipelineRunScreen.tsx` | Timed stage animation (not live graph progress). |
| `frontend/app/components/console/RunConsole.tsx` | Health check, views, approve/reject. |
| `frontend/app/components/console/ActionViews.tsx` | Proposals, critic, approval, trace. |
| `frontend/app/components/console/LineageView.tsx` | Lineage graph. |
| `frontend/app/components/console/DataViews.tsx` | Preview and column metrics. |
| `frontend/app/lib/runState.ts` | Response types and present-state helpers. |

## Frontend data flow

1. Upload files or choose the demo preset.
2. Confirm the ticket, then `POST /api/pipeline/run`.
3. `PipelineRunScreen` plays a fixed-duration animation, then `RunConsole` renders the API payload.
4. Approve or reject calls `POST /api/pipeline/approve` and resumes the paused graph for that `run_id`.

Useful response fields: `pipeline_health`, `issues`, `root_cause_analysis` (including investigation evidence and plan when present), `agent_execution`, `lineage_graph`, `sql_diagnostics`, `remediation`, `verification`, `guardrails`, `workflow_status`, `requires_human_approval`, `route_taken`.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Process up, selected provider, LLM configured. |
| `POST` | `/api/pipeline/upload` | Save CSV/Parquet, SQL, or lineage JSON under `data/uploads`. |
| `POST` | `/api/pipeline/run` | Run the graph. Empty body uses demo `stg_orders` / `fct_sales.sql` / `lineage.json`. |
| `POST` | `/api/pipeline/approve` | Resume a paused run (`approve` or `reject`). |
| `POST` | `/api/pipeline/quarantine` | Explicit quarantine helper (separate from the graph path). |

CORS is limited to localhost / `127.0.0.1` (any port).


## Storage

Structured run data is stored in a local DuckDB database (`data/obsidiandq.duckdb`):

- **runs** - pipeline execution records
- **incidents** - detected DQ issues linked to runs
- **dq_results** - full DQ detection result payloads
- **rca_evidence** - root-cause investigation evidence trails
- **remediation_results** - remediation actions and outcomes
- **evaluation_records** - controlled-benchmark evaluation payloads

CSV/Parquet files remain the input/output dataset format. The storage utility lives in `src/agent/utils/db.py` and uses parameterized SQL with safe connection handling.
## Run locally

### Backend

```powershell
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the URL Next.js prints, usually `http://localhost:3000`.

## Tests and evaluation

Contract tests (no live provider required if keys are unset or mocked):

```powershell
py -3.10 -m pytest -q tests
```

That covers `tests/test_agent.py`, `test_agentic_workflow.py`, `test_agentic_core.py`, `test_api_contract.py`, and `test_evaluation_logic.py`. Do not point pytest at a live Groq or Gemini key.

Controlled 20-incident benchmark (runs the test suite first, then the real graph):

```powershell
# Offline: deterministic handling only
$env:GROQ_API_KEY=''
python evaluation/run_controlled_benchmark.py

# Live Groq: live metrics only where non-fallback traces exist
$env:GROQ_API_KEY='your_key'
python evaluation/run_controlled_benchmark.py
```

How to read results is in `evaluation/README.md`. The newest pointer is `evaluation/LATEST.md`.

Grounding rules that the harness already encodes:

- Automated pytest pass rate is workflow-contract coverage, not LLM quality.
- Offline controlled handling success is not agent task success.
- RCA precision/recall/F1 stay `NOT MEASURABLE` until independent semantic RCA labels exist.
- Live metrics require genuine non-fallback Groq traces. A configured key with failed calls is not a live success.

## Repository hygiene

`.gitignore` excludes `.env`, caches, Node/`frontend/.next`, uploads, `data/*.duckdb`, quarantine files, healed SQL, and `evaluation/artifacts/`. Evaluation **reports** under `evaluation/results/` are kept. Do not commit API keys.

## Limitations

- LLM quality depends on provider, model, quota, and network. Recent live Groq benchmarks have recorded many call failures; check `evaluation/LATEST.md` instead of assuming agents ran.
- Critic LLM failure does not fail closed; it approves.
- Verification failure does not roll back files; it sets `VERIFICATION_FAILED` and still hits guardrails.
- Checkpointer and `RUN_STATES` are in memory.
- DQ rules and demo schema are orders-shaped (`price`, `status`, `order_id`, `order_date`). Other schemas only get generic null/duplicate checks.
- `PipelineRunScreen` is not subscribed to real node progress.
- `requirements.txt` still lists packages used by experiments or older paths (for example Streamlit); the supported UI is the Next.js app.
