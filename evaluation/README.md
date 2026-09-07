# ObsidianDQ Evaluation Operations

This folder stores reproducible, audit-ready evaluations without confusing
deterministic workflow checks with live LLM-agent performance.

## Run an evaluation

```powershell
# Offline controlled-system validation (recommended for CI)
$env:GROQ_API_KEY=''
python evaluation/run_controlled_benchmark.py

# Live-agent evaluation (requires a valid Groq key and network access)
$env:GROQ_API_KEY='your_key'
python evaluation/run_controlled_benchmark.py
```

Each run first executes the complete automated test suite, then runs 20 labeled
incidents through the actual LangGraph workflow.

## Result layout

```text
evaluation/
├── artifacts/<timestamp>_<mode>/     # generated inputs, cleaned/quarantine data, memory, healed SQL
└── results/<timestamp>_<mode>/
    ├── controlled_benchmark_report.md
    └── controlled_benchmark_results.json
```

The JSON is the source of truth. It retains each case's expected oracle, actual
workflow state, normalized tool events, approval evidence, safety classification,
and verification evidence. The Markdown report is the human-readable summary.

## Interpreting modes

| Mode | What it measures | What it must not claim |
| --- | --- | --- |
| `offline_fallback` | Deterministic controlled incident handling and verification consistency. | LLM reasoning, live tool success, RCA F1, or agent task success. |
| `live_llm` | Live-agent metrics only for cases that include genuine non-fallback traces. | Success inferred from fallback behavior. |

## Metric safeguards

- **Controlled Incident Handling Success** compares detected rules and verification behavior to the known incident oracle.
- **Controlled Verification Consistency** includes truthful verification failures as correct outcomes; it is not a remediation-success rate.
- **Agent Task Success Rate** and **Tool Success Rate** remain `NOT MEASURABLE` unless genuine live-Groq evidence exists.
- RCA scores remain `NOT MEASURABLE` until an independent semantic RCA-label set is added.
- Failure Recovery Rate remains `NOT MEASURABLE` until controlled runtime fault injection is added.

Do not report one metric as evidence for another. In particular, automated test
pass rate and offline controlled handling are not LLM-agent performance metrics.
