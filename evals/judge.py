import json
import urllib.request


MODEL = "llama3.2:3b"


# =========================================================
# LLM-AS-JUDGE
# =========================================================

def judge_mapping(
    source_field,
    sample_values,
    predicted_target,
    target_fields
):

    prompt = f"""
You are an independent evaluator for a payroll field mapping system.

Source field:
{source_field}

Sample values:
{sample_values}

The mapping AI predicted:
{predicted_target}

Available target fields:
{target_fields}

Your job:

1. Decide whether the predicted target is correct.
2. If it is wrong, choose the best target from the available target fields.
3. Give a confidence score from 0.00 to 1.00.

Return ONLY valid JSON:

{{
  "verdict": "PASS or FAIL",
  "suggested_target": "one target field",
  "confidence": 0.00,
  "reason": "short reason"
}}

Rules:

- suggested_target MUST be one of the available target fields.
- If verdict is PASS, suggested_target must equal predicted_target.
- If verdict is FAIL, suggested_target must NOT equal predicted_target.
- Do not invent a target field.
- Do not include any text outside the JSON.
"""

    # Ask Ollama to force JSON output
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode("utf-8")

    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    raw_response = result["response"].strip()

    # =====================================================
    # PARSE JUDGE RESPONSE
    # =====================================================

    try:
        judge_result = json.loads(raw_response)

    except json.JSONDecodeError:
        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": "",
            "confidence": 0.0,
            "reason": "Judge returned invalid JSON."
        }


    # =====================================================
    # READ JUDGE VALUES
    # =====================================================

    verdict = str(
        judge_result.get("verdict", "")
    ).upper()

    suggested_target = str(
        judge_result.get("suggested_target", "")
    ).strip()

    reason = str(
        judge_result.get("reason", "")
    ).strip()

    try:
        confidence = float(
            judge_result.get("confidence", 0)
        )

    except (ValueError, TypeError):
        confidence = 0.0


    # =====================================================
    # VALIDATE JUDGE OUTPUT
    # =====================================================

    # Verdict must be PASS or FAIL
    if verdict not in ["PASS", "FAIL"]:

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge returned an invalid verdict."
        }


    # Confidence must be between 0 and 1
    if confidence < 0 or confidence > 1:

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge returned an invalid confidence score."
        }


    # Suggested target must exist
    if suggested_target not in target_fields:

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge suggested an invalid target field."
        }


    # PASS must agree with original prediction
    if (
        verdict == "PASS"
        and suggested_target != predicted_target
    ):

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge PASS result contradicts its suggested target."
        }


    # FAIL must suggest a different target
    if (
        verdict == "FAIL"
        and suggested_target == predicted_target
    ):

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge FAIL result contradicts its suggested target."
        }


    # Low confidence goes to human review
    if confidence < 0.80:

        return {
            "verdict": "NEEDS_REVIEW",
            "suggested_target": suggested_target,
            "confidence": confidence,
            "reason": "Judge confidence is below 0.80."
        }


    # Valid judge result
    return {
        "verdict": verdict,
        "suggested_target": suggested_target,
        "confidence": confidence,
        "reason": reason
    }


# =========================================================
# TEST THE JUDGE
# =========================================================

if __name__ == "__main__":

    result = judge_mapping(
        source_field="Pay_Cycle",
        sample_values=[
            "Every Two Weeks",
            "Every Week"
        ],
        predicted_target="work_state",
        target_fields=[
            "employee_id",
            "paygroup_code",
            "work_state",
            "cost_center",
            "regular_earnings",
            "overtime_earnings"
        ]
    )

    print("\nLLM JUDGE RESULT")
    print("-------------------------")
    print(json.dumps(result, indent=2))