# ObsidianDQ Evaluation Metrics

## Required Metrics

| Metric | Description | When Measurable |
| --- | --- | --- |
| **Controlled Incident Handling Success** | Compares detected rules and verification behavior to the known incident oracle | Always (offline) |
| **Controlled Verification Consistency** | Includes truthful verification failures as correct outcomes | Always (offline) |
| **Agent Task Success Rate** | Live-agent task completion rate | Only with genuine live-Groq evidence |
| **Tool Success Rate** | Live tool call success rate | Only with genuine live-Groq evidence |

## Metric Safeguards

- **Automated test pass rate** measures workflow-contract coverage, not LLM quality
- **Offline controlled handling success** measures deterministic workflow handling, not agent performance
- **Agent Task Success Rate** and **Tool Success Rate** remain `NOT MEASURED` unless genuine non-fallback traces exist
- **RCA precision/recall/F1** remain `NOT MEASURED` until independent semantic RCA labels exist
- **Failure Recovery Rate** remains `NOT MEASURED` until controlled runtime fault injection is added

## Interpreting Results

| Mode | What it measures | What it must not claim |
| --- | --- | --- |
| `offline_fallback` | Deterministic incident handling and verification consistency | LLM reasoning, live tool success, RCA F1, or agent task success |
| `live_llm` | Live-agent metrics only for cases with genuine non-fallback traces | Success inferred from fallback behavior |

## Running Evaluations

```powershell
# Offline controlled-system validation
$env:GROQ_API_KEY=''
python evaluation/run_controlled_benchmark.py

# Live-agent evaluation (requires valid Groq key)
$env:GROQ_API_KEY='your_key'
python evaluation/run_controlled_benchmark.py
```

## Result Layout

```
evaluation/
├── artifacts/<timestamp>_<mode>/     # generated inputs, cleaned/quarantine data, memory, healed SQL
└── results/<timestamp>_<mode>/
    ├── controlled_benchmark_report.md
    └── controlled_benchmark_results.json
```

The JSON is the source of truth. The Markdown report is the human-readable summary.
