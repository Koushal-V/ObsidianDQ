# ObsidianDQ

ObsidianDQ is an agentic data-quality and pipeline-observability application. It uses a LangGraph workflow with Root-Cause, Triage, and Critic agents to investigate data issues, propose actions, route the workflow, and control remediation.

Deterministic code supplies evidence and executes approved row-level operations safely. It does not replace the agent's decision. If an LLM call fails, the workflow fails closed and routes the run to human review.

## What It Does

- Profiles CSV and Parquet datasets.
- Detects nulls, invalid values, negative prices, duplicates, and uniqueness issues.
- Uses lineage to identify possible upstream causes and downstream impact.
- Uses an LLM agent to inspect evidence and propose an action per issue.
- Uses a Critic Agent to review the root-cause conclusion and proposals.
- Routes to remediation, escalation, or human approval based on agent output.
- Repairs SQL with constrained `sqlglot` AST operations after approval.
- Writes high-risk records to a separate quarantine dataset.
- Shows the run, evidence, proposals, lineage, SQL, and guardrails in a Next.js dashboard.

## Agentic Workflow

```text
Profile data
    -> Detect DQ issues
    -> Analyze lineage
    -> Root-Cause Agent
    -> Triage Agent
    -> Critic Agent
    -> Agent-selected route
       |-- escalate upstream -> Root-Cause Agent
       |-- human review      -> approval gate
       |-- auto remediation  -> SQL healer
    -> Remediation
    -> Guardrails
    -> Final dashboard result
```

### Agent responsibilities

| Agent | Role | Output |
| --- | --- | --- |
| Root-Cause Agent | Investigates the affected stage using sample rows and lineage evidence. | Root-cause stage, reasoning, evidence, causality flag. |
| Triage Agent | Decides how each issue should be handled. | `AUTO_QUARANTINE`, `FLAG_FOR_REVIEW`, `IGNORE_TRANSIENT`, or `ESCALATE_UPSTREAM`, with confidence and reasoning. |
| Critic Agent | Audits the root-cause conclusion and triage proposals. | `APPROVED` or `REVISION_REQUIRED`, with reasoning. |

The Triage Agent's proposals are passed into remediation. `AUTO_QUARANTINE` and `IGNORE_TRANSIENT` change the action applied to the data. Human approval is required for low-confidence or review proposals.

## LLM Providers

Groq is preferred when `GROQ_API_KEY` is configured. Gemini remains supported as a fallback provider.

Recommended Groq configuration:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Gemini configuration:

```dotenv
GEMINI_API_KEY=your_key_here
```

The provider is selected in `src/agent/utils/llm.py`. The API exposes the selected provider through `GET /api/health`. Each run also returns `agent_execution`:

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

`llm_used: true` means at least one agent completed through an LLM. The per-agent fields show exactly which agents used the LLM. A mixed run can use the LLM for one agent and fallback behavior for another.

## Application Structure

### Backend

| Path | Responsibility |
| --- | --- |
| `backend/main.py` | FastAPI routes, uploads, pipeline execution, approvals, health checks, and API response formatting. |
| `src/agent/graph.py` | LangGraph nodes, conditional routing, checkpointed review, and pipeline execution. |
| `src/agent/state.py` | Shared state contract passed between nodes. |
| `src/agent/nodes/stage_profile.py` | Dataset profiling. |
| `src/agent/nodes/dq_detect.py` | Deterministic DQ evidence generation. |
| `src/agent/nodes/lineage_rca.py` | Lineage graph traversal and impact analysis. |
| `src/agent/nodes/root_cause_agent.py` | LLM-backed root-cause investigation with safe fallback. |
| `src/agent/nodes/triage_agent.py` | LLM-backed action proposals and routing decision. |
| `src/agent/nodes/critic_agent.py` | LLM-backed proposal and root-cause review. |
| `src/agent/nodes/sql_healer.py` | SQL parsing, validation, constrained repair, and diff generation. |
| `src/agent/nodes/remediation.py` | Executes agent-selected actions and writes quarantine output. |
| `src/agent/nodes/guardrails.py` | Final safety validation. |
| `src/agent/utils/llm.py` | Groq-first provider selection and text generation. |

### Frontend

| Path | Responsibility |
| --- | --- |
| `frontend/app/page.tsx` | Upload, confirmation, and run-console flow. |
| `frontend/app/components/UploadStep.tsx` | Dataset, SQL, and lineage uploads with visible status. |
| `frontend/app/components/console/RunConsole.tsx` | Loads run data, checks provider health, and handles approvals. |
| `frontend/app/components/console/ActionViews.tsx` | Recommendations, agent confidence, Critic result, approval, remediation, and technical trace. |
| `frontend/app/components/console/LineageView.tsx` | Interactive lineage and impact view. |
| `frontend/app/components/console/DataViews.tsx` | Dataset preview and column-quality metrics. |
| `frontend/app/lib/runState.ts` | Frontend response types and status helpers. |

## Frontend Data Flow

1. The user uploads files or selects demo data.
2. The frontend calls `POST /api/pipeline/run`.
3. FastAPI runs the LangGraph workflow.
4. The API converts `AgentState` into a dashboard response.
5. `RunConsole` stores the response and renders the Overview, Issues, Lineage, Data, Actions, and Details views.
6. Approval calls `POST /api/pipeline/approve` to resume the paused graph.

Important response fields:

- `pipeline_health`: health score and scan metrics.
- `issues`: detected DQ issues and severity.
- `root_cause_analysis`: root cause, agent reasoning, proposals, evidence, and route.
- `agent_execution`: provider and per-agent LLM usage.
- `lineage_graph`: nodes, edges, and affected assets.
- `sql_diagnostics`: SQL healing status, original SQL, repaired SQL, and replacements.
- `remediation`: actions and quarantine output.
- `guardrails`: final safety decision.
- `workflow_status`, `requires_human_approval`, and `route_taken`: current workflow state.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend status, selected provider, and LLM availability. |
| `POST` | `/api/pipeline/upload` | Validate and save CSV/Parquet, SQL, or lineage JSON. |
| `POST` | `/api/pipeline/run` | Start a pipeline run. |
| `POST` | `/api/pipeline/approve` | Approve or reject a paused run. |
| `POST` | `/api/pipeline/quarantine` | Execute the explicit quarantine operation. |

## Run Locally

### Backend

```powershell
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the URL printed by Next.js, normally `http://localhost:3000`.

## Tests and Build

Backend tests:

```powershell
py -3.10 -m pytest -q tests/test_agent.py tests/test_agentic_workflow.py tests/test_api_contract.py
```

Frontend build:

```powershell
Set-Location frontend
npm run build
```

Tests should run with provider credentials isolated or mocked. Do not allow automated tests to call a live Groq or Gemini API.

## Repository Hygiene

The `.gitignore` excludes local secrets, Python caches, pytest artifacts, Node dependencies, Next.js build output, uploaded files, run history, generated healed SQL, and generated quarantine data.

Tracked demo assets remain available under `data/raw`, `data/queries`, and `data/lineage`. Do not commit `.env` or API keys.

## Limitations

- LLM calls depend on provider availability, model access, quotas, and network connectivity.
- Failed LLM calls route safely to human review.
- The current graph checkpointer and API run-state store are in memory; production multi-worker deployments need durable shared persistence.
- The local demo uses a small synthetic dataset and is not a production data warehouse integration.
