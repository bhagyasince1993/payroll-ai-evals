# Payroll AI Integration & Evaluation Platform
An AI-powered data integration platform that dynamically maps, translates, and validates payroll data from different client schemas, with an AI agent layer and a dedicated evaluation framework using ground truth, deterministic checks, and LLM-as-Judge.
## Problem

Payroll clients often provide the same business information using different field names, formats, and value conventions.

For example:

- `EMP_NO` → `employee_id`
- `Worker_ID` → `employee_id`
- `Payroll_Frequency` → `paygroup_code`
- `Department` → `cost_center`
- `OT_Wages` → `overtime_earnings`

Traditional data conversion requires manual mapping, translation, and validation for each client.

The goal of this project is to build a dynamic data integration layer that can understand previously unseen client schemas and transform them into a common payroll model without writing client-specific code for every new file.

The second challenge is trust: when AI makes these decisions, we need a way to measure whether those decisions are actually correct. That is why the platform includes a separate AI evaluation layer.

## How It Works

A client uploads a payroll CSV with its own schema.

The platform then:

1. Discovers the source schema and sample values.
2. Uses AI to map source fields to a canonical payroll schema.
3. Translates client-specific values into standardized values.
4. Validates the mapped and translated data.
5. Captures the AI execution trace.
6. Evaluates the AI decisions using trusted ground truth or LLM-as-Judge.
7. Displays the results in a human-readable evaluation dashboard.

The system is designed so that a new client can upload a previously unseen CSV without requiring client-specific mapping code.
## Architecture

```text
                    CLIENT PAYROLL CSV
                            │
                            ▼
                 ┌─────────────────────┐
                 │ DATA INGESTION      │
                 │ Schema Discovery    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ AI MAPPING          │
                 │                     │
                 │ Source → Target     │
                 │ Confidence Score    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ TRANSLATION         │
                 │                     │
                 │ Client Values       │
                 │ → Canonical Values  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ VALIDATION          │
                 │                     │
                 │ Schema + Rules      │
                 │ Data Quality        │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ AI AGENT            │
                 │                     │
                 │ Understand Request  │
                 │ Select Tools        │
                 │ Execute Workflow    │
                 └──────────┬──────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │ AI EVALUATION LAYER          │
              │                              │
              │ Ground Truth                 │
              │ Deterministic Evaluation     │
              │ LLM-as-Judge                 │
              │ Confidence Checks             │
              │ Human Review                 │
              └──────────────┬───────────────┘
                             │
                             ▼
                 ┌─────────────────────┐
                 │ STREAMLIT DASHBOARD │
                 │                     │
                 │ PASS / FAIL         │
                 │ Confidence          │
                 │ Failure Details     │
                 └─────────────────────┘
                 ## Data Integration Layer

The data integration layer is designed to work like an AI-assisted, AWS Glue-style data integration workflow.

A new client can upload a payroll file with an unfamiliar schema. The system discovers the fields, understands their meaning, maps them to a canonical payroll schema, translates client-specific values, and validates the result.

### Example

Client file:

| Client Field | Sample Value |
|---|---|
| `EMP_NO` | `100245` |
| `Payroll_Frequency` | `Every Two Weeks` |
| `Department` | `FIN-001` |
| `OT_Wages` | `450.25` |

The system maps these to:

| Source Field | Canonical Field |
|---|---|
| `EMP_NO` | `employee_id` |
| `Payroll_Frequency` | `paygroup_code` |
| `Department` | `cost_center` |
| `OT_Wages` | `overtime_earnings` |

The important design principle is that the system does not require a new Python mapping implementation for every client.## AI Field Mapping

The mapping engine uses the source field name, sample values, and available target schema to determine the most likely canonical field.

### Example

```text
Source Field:
OT_Wages

Sample Values:
450.25
120.50
875.00

Available Targets:
employee_id
paygroup_code
work_state
cost_center
regular_earnings
overtime_earnings
## Translation

After a source field is mapped to a canonical field, the translation layer standardizes client-specific values.

For example:

| Client Value | Canonical Value |
|---|---|
| `Every Week` | `WEEKLY` |
| `Weekly` | `WEEKLY` |
| `Every Two Weeks` | `BIWEEKLY` |
| `Biweekly` | `BIWEEKLY` |

This separates two different problems:

**Mapping**
```text
Which target field does this source field represent?
## Validation

After mapping and translation, the system validates the resulting data before it can be considered ready for downstream processing.

Validation checks include:

- Required fields
- Target field validity
- Data types
- Allowed values
- Mapping consistency
- Translation rules
- Missing values
- Duplicate records
- Data quality issues

Example:

```text
Source Field
     ↓
AI Mapping
     ↓
Translation
     ↓
Validation
     ↓
PASS / FAIL / NEEDS_REVIEW
## AI Agent

The AI Agent sits above the data integration capabilities and orchestrates the workflow based on a user's request.

Instead of requiring the user to manually run individual steps, the agent can determine which tools are needed and execute them in the appropriate sequence.

### Example

User:

```text
Map and validate this client's payroll file.
## AI Evaluation

The evaluation layer independently measures whether the AI system made the correct decision.

The system uses different evaluation methods depending on whether trusted ground truth is available.

### Deterministic Evaluation

When the expected result is known:

```text
AI Prediction
      ↓
Expected Result
      ↓
Deterministic Evaluator
      ↓
PASS / FAIL
Predicted:
regular_earnings

Expected:
overtime_earnings

Result:
FAIL
PASS
FAIL
NEEDS_REVIEW


## Evaluation Results

The evaluation pipeline can run across multiple client payroll files and aggregate the results into a single report.

### Example Batch

```text
Client Uploads: 9

Mapping Cases: 54

PASS: 36
FAIL: 18
NEEDS_REVIEW: 0

Pass Rate: 66.67%
| Client   | Source Field | AI Prediction    | Expected          | Verdict |
| -------- | ------------ | ---------------- | ----------------- | ------- |
| Client 3 | Pay_Cycle    | employee_id      | paygroup_code     | FAIL    |
| Client 3 | Dept_Code    | employee_id      | cost_center       | FAIL    |
| Client 1 | OT_AMT       | regular_earnings | overtime_earnings | FAIL    |



## Evaluation Flywheel

Every new client run can become a future evaluation case.

```text
Client File
    ↓
AI Mapping / Agent Execution
    ↓
Execution Trace
    ↓
Evaluation Case
    ↓
Ground Truth Available?
   ↙              ↘
 YES              NO
  ↓                ↓
Deterministic    LLM-as-Judge
Evaluation           ↓
  ↓              Human Review
  └────────┬─────────┘
           ↓
     Trusted Eval Data
           ↓
      Improve AI
           ↓
       Re-run Evals
       ## Project Structure

payroll-ai-evals/
│
├── app.py
├── README.md
├── RUNBOOK.md
│
├── data/
│   ├── target_schema.json
│   ├── ground_truth.json
│   ├── expected_mapping.json
│   ├── expected_translations.json
│   └── translation_rules.json
│
├── src/
│   ├── ai_mapper.py
│   ├── mapper.py
│   ├── translator.py
│   └── eval_logger.py
│
└── evals/
    ├── judge.py
    ├── batch_eval.py
    ├── run_evals.py
    └── translation_eval.py

    | Component             | Purpose                                  |
| --------------------- | ---------------------------------------- |
| `ai_mapper.py`        | AI-assisted semantic field mapping       |
| `mapper.py`           | Mapping logic and target schema handling |
| `translator.py`       | Client value translation                 |
| `batch_eval.py`       | Multi-client evaluation                  |
| `judge.py`            | LLM-as-Judge evaluation                  |
| `translation_eval.py` | Translation evaluation                   |
| `eval_logger.py`      | Captures evaluation/execution data       |
| `app.py`              | Streamlit dashboard                      |
| `ground_truth.json`   | Expected evaluation results              |

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python |
| AI Model | Llama 3.2 |
| Model Runtime | Ollama |
| UI / Dashboard | Streamlit |
| Data Format | CSV / JSON / JSONL |
| Mapping | AI + deterministic rules |
| Translation | Rule-based normalization |
| Evaluation | Deterministic evaluation |
| AI Evaluation | LLM-as-Judge |
| Version Control | Git / GitHub |

The architecture is intentionally modular so that the local LLM can later be replaced or extended with other models or hosted AI services.
## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/bhagyasince1993/payroll-ai-evals.git
cd payroll-ai-evals


2. Create a Python environment
python3 -m venv .venv
source .venv/bin/activate


3. Install dependencies
pip install -r requirements.txt

4. Start the local LLM

This project uses Ollama for local LLM inference.
Make sure Ollama is running and the required model is available.

5. Run the evaluation pipeline
python3 evals/batch_eval.py

6. Launch the Streamlit dashboard
streamlit run app.py


