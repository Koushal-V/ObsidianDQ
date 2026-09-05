# ObsidianDQ

## Deterministic & Agentic Data Quality, Observability, and Self-Healing Engine

ObsidianDQ is an intelligent data quality and observability system designed to automatically detect data quality problems, trace their potential upstream causes through data lineage, repair structurally invalid SQL, apply controlled remediation, quarantine high-risk records, and enforce safety guardrails.

The system combines deterministic data-quality rules with an agentic workflow implemented using LangGraph.

---

# 1. Project Overview

Modern data pipelines can fail because of missing values, invalid values, negative measurements, schema inconsistencies, or incorrect transformation queries.

Traditional data-quality systems generally identify the problem but require manual investigation and remediation.

ObsidianDQ extends this workflow by providing:

- Automated stage profiling
- Deterministic data-quality detection
- Severity classification
- Upstream lineage-based root-cause analysis
- SQL self-healing using `sqlglot`
- Controlled remediation
- Automatic quarantine of high-severity records
- Guardrail-based approval
- Interactive Streamlit observability dashboard
- Automated tests

The complete workflow is:

```text
Data
  ↓
Stage Profiling
  ↓
DQ Detection
  ↓
Lineage RCA
  ↓
SQL Self-Healing
  ↓
Remediation
  ↓
Quarantine
  ↓
Guardrails
  ↓
Pipeline Result

2. Key Features
2.1 Stage Profiling

The profiling module analyzes the input stage and provides:

Row count
Column count
Column names
Basic dataset information
2.2 Data Quality Detection

ObsidianDQ detects deterministic data-quality violations.

Current rules include:

NOT_NULL

Detects missing values in required columns.

PRICE_NON_NEGATIVE

Detects negative price values.

VALID_STATUS

Detects invalid status values.

Each detected issue contains:

Rule
Column
Description
Number of affected rows
Severity

Example:

NOT_NULL
Column: customer_id
Affected rows: 2
Severity: MEDIUM
3. Severity Model

Issues are classified according to their potential impact.

HIGH
MEDIUM
LOW

High-severity issues receive stronger remediation controls.

For example:

PRICE_NON_NEGATIVE
Severity: HIGH
Action: QUARANTINE

while medium-severity issues may be routed for review.

4. Lineage-Based Root Cause Analysis

ObsidianDQ uses the pipeline lineage to investigate where a data-quality problem may originate.

Current lineage:

raw_customers
      ↓
stg_orders
      ↓
fct_sales

The lineage analysis identifies:

Affected stage
Direct upstream stages
Upstream ancestors
Potential root-cause stage
Direct downstream stages
Downstream blast radius

This allows the system to distinguish between the stage where an issue is detected and the stage where the problem may have originated.

5. SQL Self-Healing

The SQL self-healing module uses sqlglot to parse SQL into an Abstract Syntax Tree (AST).

The healer performs:

SQL parsing
Structural problem detection
AST normalization
Safe deterministic repair
Table-reference validation
SQL diff generation
Repaired SQL generation

The system intentionally avoids hallucinating tables or columns.

Only deterministic and structurally safe transformations are applied.

The original and repaired SQL are both exposed in the dashboard.

6. Remediation

After DQ detection, remediation actions are selected according to issue severity.

Example:

MEDIUM → REVIEW
HIGH   → QUARANTINE

The remediation result records:

Severity
Rule
Column
Action
Rows affected
Description
7. Automatic Quarantine

High-risk records can be isolated into a separate quarantine dataset.

Example:

data/quarantine/stg_orders_quarantine.parquet

This prevents problematic records from being silently propagated through downstream processing.

The dashboard provides:

Number of quarantined rows
Quarantine preview
Quarantine file location
8. Guardrails

The guardrail layer provides a final safety check before the pipeline completes remediation.

It evaluates:

DQ issue count
Severity distribution
Detected issues
High-severity conditions

Possible actions include:

APPROVED
CONTROLLED_REMEDIATION
BLOCK

For example:

Approval: APPROVED
Action: CONTROLLED_REMEDIATION
Warning: High-severity issue detected

This prevents uncontrolled automatic modifications.

9. Agent Architecture

ObsidianDQ is implemented as a LangGraph stateful workflow.

                  ┌─────────────────┐
                  │ Stage Profiling │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   DQ Detection  │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │  Lineage RCA    │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ SQL Self-Healer │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   Remediation   │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   Guardrails    │
                  └────────┬────────┘
                           ↓
                         END

The workflow maintains a shared AgentState.

Important state information includes:

Pipeline information
Stage information
Profile metrics
DQ results
Severity summary
Lineage information
Root cause
Blast radius
Original SQL
Repaired SQL
SQL validation
Remediation results
Quarantine information
Guardrail results
