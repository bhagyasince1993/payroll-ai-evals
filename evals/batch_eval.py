import json
import os
from collections import defaultdict

from evals.judge import judge_mapping


# =========================================================
# CONFIGURATION
# =========================================================

LOG_FILE = "results/eval_logs.jsonl"
SCHEMA_FILE = "data/target_schema.json"
GROUND_TRUTH_FILE = "data/ground_truth.json"

# Temporary while developing.
# Later change back to 100.
BATCH_SIZE = 3


# =========================================================
# LOAD DATA
# =========================================================

def load_eval_logs():

    if not os.path.exists(LOG_FILE):
        return []

    records = []

    with open(LOG_FILE, "r") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return records


def load_ground_truth():

    if not os.path.exists(GROUND_TRUTH_FILE):
        return {}

    with open(GROUND_TRUTH_FILE, "r") as file:
        return json.load(file)


def load_target_fields():

    with open(SCHEMA_FILE, "r") as file:
        schema = json.load(file)

    return list(schema.keys())


# =========================================================
# UNIQUE CLIENT RUNS
# =========================================================

def get_unique_uploads(records):

    return {
        record.get("upload_id")
        for record in records
        if record.get("upload_id")
    }


# =========================================================
# BUILD ONE CASE PER FIELD PER UPLOAD
# =========================================================

def build_mapping_cases(records):

    cases = {}
    samples = defaultdict(list)

    for record in records:

        upload_id = record.get("upload_id")

        if not upload_id:
            continue

        source_field = record.get("source_field")
        predicted_target = record.get("target_field")
        client_file = record.get("client_file")
        original_value = record.get("original_value")

        key = (
            upload_id,
            source_field
        )

        cases[key] = {
            "upload_id": upload_id,
            "client_file": client_file,
            "source_field": source_field,
            "predicted_target": predicted_target
        }

        if original_value is not None:

            original_value = str(original_value)

            if (
                original_value not in samples[key]
                and len(samples[key]) < 5
            ):
                samples[key].append(
                    original_value
                )

    for key in cases:

        cases[key]["sample_values"] = (
            samples[key]
        )

    return list(cases.values())


# =========================================================
# EVALUATE ONE MAPPING
# =========================================================

def evaluate_case(
    case,
    target_fields,
    ground_truth
):

    source_field = case["source_field"]

    predicted_target = case[
        "predicted_target"
    ]


    # =====================================================
    # KNOWN FIELD
    # Use trusted ground truth
    # =====================================================

    if source_field in ground_truth:

        expected_target = ground_truth[
            source_field
        ]

        if predicted_target == expected_target:
            verdict = "PASS"

        else:
            verdict = "FAIL"

        return {
            **case,

            "evaluation_type":
                "GROUND_TRUTH",

            "expected_target":
                expected_target,

            "verdict":
                verdict,

            "suggested_target":
                expected_target,

            "confidence":
                1.0,

            "reason":
                "Compared against confirmed ground truth."
        }


    # =====================================================
    # NEW / UNKNOWN FIELD
    # Send to LLM Judge
    # =====================================================

    judge_result = judge_mapping(

        source_field=
            source_field,

        sample_values=
            case["sample_values"],

        predicted_target=
            predicted_target,

        target_fields=
            target_fields
    )


    return {
        **case,

        "evaluation_type":
            "LLM_JUDGE",

        "expected_target":
            "",

        "verdict":
            judge_result.get(
                "verdict",
                "NEEDS_REVIEW"
            ),

        "suggested_target":
            judge_result.get(
                "suggested_target",
                ""
            ),

        "confidence":
            judge_result.get(
                "confidence",
                0
            ),

        "reason":
            judge_result.get(
                "reason",
                ""
            )
    }


# =========================================================
# RUN BATCH EVALUATION
# =========================================================

def run_batch_eval():

    records = load_eval_logs()

    ground_truth = load_ground_truth()

    target_fields = load_target_fields()

    uploads = get_unique_uploads(
        records
    )

    upload_count = len(
        uploads
    )

    cases = build_mapping_cases(
        records
    )

    ready = (
        upload_count >= BATCH_SIZE
    )


    # =====================================================
    # NOT ENOUGH DATA YET
    # =====================================================

    if not ready:

        return {
            "upload_count": upload_count,
            "batch_target": BATCH_SIZE,
            "ready": False,
            "total_cases": 0,
            "passed": 0,
            "failed": 0,
            "needs_review": 0,
            "pass_rate": 0,
            "ground_truth_cases": 0,
            "judge_cases": 0,
            "results": []
        }


    # =====================================================
    # RUN EVALS
    # =====================================================

    results = []

    for case in cases:

        try:

            result = evaluate_case(
                case,
                target_fields,
                ground_truth
            )

        except Exception as error:

            result = {
                **case,

                "evaluation_type":
                    "SYSTEM",

                "expected_target":
                    "",

                "verdict":
                    "NEEDS_REVIEW",

                "suggested_target":
                    "",

                "confidence":
                    0,

                "reason":
                    f"Evaluation error: {error}"
            }

        results.append(
            result
        )


    # =====================================================
    # METRICS
    # =====================================================

    total = len(results)

    passed = sum(
        1
        for result in results
        if result["verdict"] == "PASS"
    )

    failed = sum(
        1
        for result in results
        if result["verdict"] == "FAIL"
    )

    needs_review = sum(
        1
        for result in results
        if result["verdict"] == "NEEDS_REVIEW"
    )

    ground_truth_cases = sum(
        1
        for result in results
        if result["evaluation_type"]
        == "GROUND_TRUTH"
    )

    judge_cases = sum(
        1
        for result in results
        if result["evaluation_type"]
        == "LLM_JUDGE"
    )

    if total > 0:
        pass_rate = (
            passed / total
        ) * 100

    else:
        pass_rate = 0


    # =====================================================
    # RETURN TO STREAMLIT
    # =====================================================

    return {
        "upload_count":
            upload_count,

        "batch_target":
            BATCH_SIZE,

        "ready":
            True,

        "total_cases":
            total,

        "passed":
            passed,

        "failed":
            failed,

        "needs_review":
            needs_review,

        "pass_rate":
            pass_rate,

        "ground_truth_cases":
            ground_truth_cases,

        "judge_cases":
            judge_cases,

        "results":
            results
    }


# =========================================================
# TERMINAL TEST
# =========================================================

if __name__ == "__main__":

    report = run_batch_eval()

    print(
        json.dumps(
            report,
            indent=2
        )
    )