# Controlled Agent Evaluation — ObsidianDQ

Run timestamp: `2026-09-07T16:28:09Z`  
LLM provider detected: `groq`  
Mode: `live_llm`

## Executive Summary

This evaluation executed 20 controlled incidents with live Groq configured. Live metrics are populated only where genuine non-fallback traces were recorded.

## System Contract Validation

Automated tests: **33 / 33 passed (100.0%)**.

This demonstrates implemented workflow contracts. It is not an LLM-agent success rate.

| Contract | Result |
| --- | --- |
| Dynamic tool calling | PASS |
| Investigation evidence storage | PASS |
| Root-cause generation | PASS |
| Required remediation plan structure | PASS |
| Incident-memory retrieval | PASS |
| Critic/revision loop | PASS (automated contract test) |
| Human approval pause/resume | PASS |
| Remediation | PASS |
| Post-remediation verification | PASS |
| Failed-verification handling | PASS |

## Controlled Incident Handling

| Metric | Result | Sample Size |
| --- | ---: | ---: |
| Controlled Incident Handling Success | 100.0% | 20 incidents |
| Controlled Verification Consistency | 100.0% | 20 remediation attempts |

## Live LLM Evaluation

| Execution evidence | Result |
| --- | ---: |
| LIVE_LLM_SUCCESSFULLY_EXECUTED | 5 cases |
| LLM_CONFIGURED_BUT_CALL_FAILED | 15 cases |
| OFFLINE_FALLBACK | 0 cases |
| Provider | groq |
| LLM call failures | 84 |

| Metric | Result | Sample Size |
| --- | ---: | ---: |
| Agent Task Success Rate | 0.0% | 5 live incidents |
| Tool Success Rate | 80.0% | 5 live tool calls |
| RCA Precision | NOT MEASURABLE | 0 |
| RCA Recall | NOT MEASURABLE | 0 |
| RCA F1 | NOT MEASURABLE | 0 |
| Failure Recovery Rate | NOT MEASURABLE | 0 injected failures |

Recorded workflow tool events: 148. These include fallback events and are not live tool-use evidence.

## Metric Definitions

- **Controlled Incident Handling Success:** deterministic issue detection and verification behavior match the predefined controlled oracle.
- **Agent Task Success Rate:** end-to-end success of a genuine live LLM-agent run with recorded structured agent contribution.
- **Controlled Verification Consistency:** reported verification state agrees with the deterministic post-remediation DQ result, including correctly reported failures.
- **Tool Success Rate:** successful, valid genuine live-agent tool calls divided by all live-agent tool calls.
- **RCA Precision / Recall / F1:** semantic root-cause accuracy against independent RCA labels.
- **Failure Recovery Rate:** correct recovery from deliberately injected runtime failures.

## Limitations

- Offline fallback runs do not measure LLM-agent reasoning quality.
- Deterministic controlled incident handling is not equivalent to LLM Task Success Rate.
- RCA metrics require independent semantic root-cause ground truth.
- Failure Recovery Rate requires deliberately injected runtime failures.
- Tool Success Rate requires genuine live-agent tool traces.
- A 20-case benchmark is limited evidence and is not production-level reliability.

## Failed Cases

No controlled handling cases failed the deterministic benchmark oracle.

Raw per-incident evidence is stored alongside this report in `controlled_benchmark_results.json`.