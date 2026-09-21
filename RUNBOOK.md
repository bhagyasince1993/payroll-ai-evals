# Payroll AI Evals Runbook

This project maps client payroll columns to a common payroll schema, translates coded values, records evaluation evidence, and reviews mapping quality across multiple client uploads.

## 1. What the system contains

### User-facing application

- `app.py`: Streamlit application for CSV upload, Ollama-based field mapping, value translation, logging, and the evaluation dashboard.

### Mapping and translation scripts

- `src/mapper.py`: deterministic mapping using normalized field-name similarity.
- `src/translator.py`: deterministic translation using known field mappings and translation rules.
- `src/ai_mapper.py`: command-line AI mapping for `data/client2_payroll.csv`.
- `src/eval_logger.py`: saves uploaded files and app evaluation records.

### Evaluation scripts

- `evals/run_evals.py`: evaluates deterministic mapping against `data/expected_mapping.json`.
- `evals/translation_eval.py`: evaluates translations against `data/expected_translations.json`.
- `evals/judge.py`: calls Ollama as an LLM judge and validates its JSON response.
- `evals/batch_eval.py`: evaluates distinct uploaded client runs from `results/eval_logs.jsonl`.

### Data and generated artifacts

- `data/payroll_input.csv`: baseline evaluation input.
- `data/client2_payroll.csv`: alternate client input used by the AI mapper.
- `data/target_schema.json`: allowed target fields, descriptions, and types.
- `data/translation_rules.json`: exact source-value translation rules.
- `data/expected_mapping.json`: baseline mapping ground truth.
- `data/expected_translations.json`: baseline translation ground truth.
- `data/ground_truth.json`: mapping ground truth for all known client field names used by batch evaluation.
- `data/uploads/`: uploaded CSV files saved by the Streamlit app. The directory is created on demand.
- `results/eval_logs.jsonl`: append-only evaluation records created by the Streamlit app.

The scripts print reports to the terminal or display them in Streamlit. They do not currently export a final translated CSV or a separate report file.

## 2. Prerequisites

Required for deterministic scripts:

- Python 3
- A shell opened in the project root

Required for the Streamlit application:

- Python packages `streamlit` and `pandas`
- Ollama installed and reachable at `http://localhost:11434`
- Ollama model `llama3.2:3b`

The project has no dependency lockfile or requirements file. Install dependencies into a virtual environment rather than the system Python installation.

## 3. Setup

Run from the project root:

```bash
cd /path/to/payroll-ai-evals
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install streamlit pandas
```

The Python files use paths such as `data/target_schema.json` relative to the current working directory. Always run commands from `/path/to/payroll-ai-evals`.

For AI-backed workflows, start Ollama in a separate terminal if it is not already running:

```bash
ollama serve
ollama pull llama3.2:3b
```

Confirm the model is available with:

```bash
ollama list
```

## 4. Baseline deterministic checks

These checks do not require Ollama.

### Field mapping

```bash
python src/mapper.py
```

The script reads the columns in `data/payroll_input.csv`, compares each one with the target fields, and prints the best match and similarity confidence. It does not apply translations or save output.

### Value translation

```bash
python src/translator.py
```

The script uses these known mappings:

| Source field | Target field |
| --- | --- |
| `PAY_GRP` | `paygroup_code` |
| `WORK_ST` | `work_state` |
| `COST_CTR` | `cost_center` |

Known values are translated from `data/translation_rules.json`. Missing values are printed as `UNKNOWN - NEEDS REVIEW`.

### Mapping evaluation

```bash
python evals/run_evals.py
```

For each source column in `data/payroll_input.csv`, the evaluator compares the similarity-based prediction with `data/expected_mapping.json` and prints `PASS` or `FAIL`, followed by total, passed, failed, and accuracy metrics.

### Translation evaluation

```bash
python evals/translation_eval.py
```

For every unique value in the three mapped categorical fields, the evaluator compares `data/translation_rules.json` with `data/expected_translations.json` and prints translation accuracy.

The evaluation scripts print failures but do not currently exit non-zero when failures exist. Treat the summary and individual failure lines as the acceptance result.

## 5. Run the command-line AI mapper

Ensure Ollama is running, then execute:

```bash
python src/ai_mapper.py
```

The script reads `data/client2_payroll.csv`, sends each column and its first five rows of sample values to the `llama3.2:3b` model, and prints the returned target field.

The response is not schema-validated by this script. Before using a result, confirm it exactly matches one of the keys in `data/target_schema.json`.

## 6. Run the Streamlit application

Start the application from the project root:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit.

### Process a client file

1. Upload a client payroll CSV.
2. Confirm the displayed source rows and source columns.
3. Select **Run AI Mapping & Translation**.
4. Review the AI field mapping table.
5. Review translated payroll data.
6. Review the translation review table, especially rows marked `NEEDS_REVIEW`.

The app reads uploaded columns as strings and sends up to five non-null sample values per column to Ollama.

### Translation statuses

- `RULE`: an exact value match exists in `data/translation_rules.json`.
- `PRESERVED`: the target is `employee_id`, `regular_earnings`, or `overtime_earnings`, so the input is retained as text.
- `NEEDS_REVIEW`: no exact rule exists and the target is not a preserved field.

The app logs each source value, model target, translated value, and status after processing. It saves the uploaded CSV under `data/uploads/` with a generated UUID prefix and appends records to `results/eval_logs.jsonl`.

## 7. Understand the evaluation log

Each current log record contains:

- `timestamp`
- `upload_id`
- `client_file`
- `source_field`
- `target_field`
- `original_value`
- `translated_value`
- `translation_status`

The batch evaluator requires `upload_id` to distinguish client runs. Older records without `upload_id` are ignored when counting uploads and building batch cases.

The log is append-only. Do not edit it manually while the Streamlit app is running. Back it up before cleanup or migration because it is the input to the batch dashboard.

## 8. Run batch evaluation

The Streamlit dashboard invokes this automatically, but it can also be run from the terminal:

```bash
python evals/batch_eval.py
```

The batch evaluator:

1. Reads valid JSON records from `results/eval_logs.jsonl`.
2. Counts unique `upload_id` values.
3. Builds one mapping case per `(upload_id, source_field)` pair.
4. Collects up to five distinct sample values for each case.
5. Waits until the configured batch size is reached.
6. Uses `data/ground_truth.json` for known source fields.
7. Sends unknown fields to `evals/judge.py` for LLM evaluation.
8. Reports pass, fail, needs-review, pass rate, ground-truth cases, and judge cases.

`evals/batch_eval.py` currently sets `BATCH_SIZE = 3`. The comments identify `100` as the later intended production value; change the constant deliberately and record the reason when changing batch policy.

When fewer than three unique uploads have valid `upload_id` values, the report returns `ready: false` and zero evaluated cases. Once ready, known fields are evaluated exactly against `data/ground_truth.json`.

## 9. LLM judge behavior

`evals/judge.py` calls the same local Ollama model and requests JSON containing:

- `verdict`: `PASS` or `FAIL`
- `suggested_target`: one target schema field
- `confidence`: a number from `0.00` to `1.00`
- `reason`: a short explanation

The judge result becomes `NEEDS_REVIEW` when JSON is invalid, the verdict is invalid, confidence is outside `0..1`, the suggested target is not in the target schema, the verdict contradicts the suggested target, or confidence is below `0.80`.

Run its built-in smoke check with:

```bash
python evals/judge.py
```

This requires Ollama and tests a sample `Pay_Cycle` mapping request.

## 10. Updating data, mappings, or rules

When onboarding a new client format:

1. Add or upload the client CSV.
2. Confirm every source field maps to a key in `data/target_schema.json`.
3. Add known source-field mappings to `data/ground_truth.json` when the mapping is confirmed.
4. Add exact categorical value translations to `data/translation_rules.json`.
5. Update expected files when changing the baseline test contract.
6. Run the deterministic mapping and translation evaluations.
7. Run or inspect the batch evaluation once the required number of uploads exists.
8. Exercise the Streamlit workflow and resolve all intended `NEEDS_REVIEW` rows.

Keep target names consistent across `target_schema.json`, ground truth, rules, prompts, and uploaded mapping results. Treat a change to expected data as a contract change requiring review, not as a way to make a failing implementation pass.

## 11. Troubleshooting

### `FileNotFoundError` for a file under `data/`

Change to the project root and rerun the command. Relative paths are not resolved relative to each script's own directory.

### `ModuleNotFoundError` for `streamlit` or `pandas`

Activate `.venv` and install the packages:

```bash
source .venv/bin/activate
python -m pip install streamlit pandas
```

### Connection refused on port `11434`

Start Ollama with `ollama serve`, or verify that an existing Ollama service is healthy. Confirm `llama3.2:3b` appears in `ollama list`.

### Model returns an invalid target

The AI mapper and app display the model response without enforcing membership in the target schema. Inspect the response and target schema before accepting it. Add validation before production use if invalid responses are possible.

### Translation remains `NEEDS_REVIEW`

The current translation lookup is an exact string match. Add the exact source value to the appropriate target field in `data/translation_rules.json`, or review the value as an intentional exception. Rerun `python evals/translation_eval.py` afterward.

### Batch dashboard shows no cases

Check that `results/eval_logs.jsonl` exists, records are valid JSON, and records contain unique `upload_id` values. The batch report does not become ready until `BATCH_SIZE` unique uploads have been logged.

### Judge result becomes `NEEDS_REVIEW`

Inspect the reason in the report. Common causes are invalid JSON, an unknown target field, a contradictory verdict, or confidence below `0.80`. Review the case manually before changing ground truth.

## 12. Operational limitations and safety

- Payroll files can contain sensitive personal and compensation data. Keep uploads, logs, and console output within the approved environment.
- There is no automated unit-test suite, lockfile, or dependency manifest in the current project.
- Evaluation scripts report failures but do not set a failing process exit code.
- AI mappings are not persisted as a standalone mapping artifact and are not fully schema-validated before translation.
- The app does not validate required CSV columns before processing.
- Duplicate AI target predictions can overwrite columns in the in-memory translated dataframe.
- Batch evaluation depends on append-only logs and currently uses a development batch size of three.
- The app does not export the translated dataframe; preserve reviewed results through an approved downstream process.