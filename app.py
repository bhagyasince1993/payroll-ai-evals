import streamlit as st
import pandas as pd
import json
import urllib.request

from src.eval_logger import save_eval_log, save_uploaded_file
from evals.batch_eval import run_batch_eval


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = "llama3.2:3b"


# =========================================================
# LOAD TARGET SCHEMA
# =========================================================

with open("data/target_schema.json", "r") as file:
    target_schema = json.load(file)

TARGET_FIELDS = list(target_schema.keys())


# =========================================================
# LOAD TRANSLATION RULES
# =========================================================

with open("data/translation_rules.json", "r") as file:
    translation_rules = json.load(file)


# =========================================================
# AI FIELD MAPPING
# =========================================================

def ask_llm(source_column, sample_values):

    prompt = f"""
You are a payroll data mapping system.

Source field:
{source_column}

Sample values:
{sample_values}

Available target fields:
{chr(10).join(TARGET_FIELDS)}

Choose exactly ONE target field that best matches the source field.

Return ONLY the target field name.
Do not explain your answer.
"""

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    return result["response"].strip()


# =========================================================
# TRANSLATION
# =========================================================

def translate_value(target_field, value):

    value_string = str(value).strip()

    if target_field in translation_rules:

        field_rules = translation_rules[target_field]

        if value_string in field_rules:
            return field_rules[value_string], "RULE"

    if target_field in [
        "employee_id",
        "regular_earnings",
        "overtime_earnings"
    ]:
        return value_string, "PRESERVED"

    return value_string, "NEEDS_REVIEW"


# =========================================================
# EVAL DASHBOARD
# =========================================================

def show_eval_dashboard():

    st.divider()

    st.header("📊 AI Eval Dashboard")

    report = run_batch_eval()

    if not report["ready"]:

        st.info(
            f'{report["upload_count"]} client runs captured. '
            f'Batch eval starts at {report["batch_target"]}.'
        )

        return

    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Client Runs",
        report["upload_count"]
    )

    col2.metric(
        "Mapping Cases",
        report["total_cases"]
    )

    col3.metric(
        "Pass Rate",
        f'{report["pass_rate"]:.2f}%'
    )


    col4, col5, col6 = st.columns(3)

    col4.metric(
        "✅ Passed",
        report["passed"]
    )

    col5.metric(
        "❌ Failed",
        report["failed"]
    )

    col6.metric(
        "⚠️ Needs Review",
        report["needs_review"]
    )


    # -----------------------------------------------------
    # BUILD HUMAN-READABLE TABLE
    # -----------------------------------------------------

    rows = []

    for result in report["results"]:

        verdict = result["verdict"]

        if verdict == "PASS":
            display_result = "✅ PASS"

        elif verdict == "FAIL":
            display_result = "❌ FAIL"

        else:
            display_result = "⚠️ NEEDS REVIEW"


        rows.append({

            "Client":
                result["client_file"],

            "Source Field":
                result["source_field"],

            "AI Mapped To":
                result["predicted_target"],

            "Expected / Suggested":
                result["expected_target"]
                or result["suggested_target"],

            "Result":
                display_result,

            "Evaluation":
                result["evaluation_type"]
        })


    eval_df = pd.DataFrame(rows)


    # -----------------------------------------------------
    # FAILURES FIRST
    # -----------------------------------------------------

    st.subheader("❌ Failures & Review")

    problem_df = eval_df[
        eval_df["Result"] != "✅ PASS"
    ]

    if problem_df.empty:

        st.success(
            "No mapping failures found."
        )

    else:

        st.dataframe(
            problem_df,
            width="stretch",
            hide_index=True
        )


    # -----------------------------------------------------
    # ALL RESULTS
    # -----------------------------------------------------

    with st.expander(
        "View All Evaluation Results"
    ):

        st.dataframe(
            eval_df,
            width="stretch",
            hide_index=True
        )


# =========================================================
# STREAMLIT PAGE
# =========================================================

st.set_page_config(
    page_title="Payroll AI Evals",
    page_icon="🧪",
    layout="wide"
)

st.title(
    "🧪 Payroll AI Mapping, Translation & Evals"
)

st.write(
    "Upload client payroll data. "
    "The system maps fields, translates values, "
    "captures execution traces, and evaluates AI quality."
)

st.divider()


# =========================================================
# UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "Upload Client Payroll CSV",
    type=["csv"]
)


if uploaded_file is not None:

    df = pd.read_csv(
        uploaded_file,
        dtype=str
    )

    st.success(
        f"{uploaded_file.name} uploaded successfully."
    )

    st.subheader(
        "Source Payroll Data"
    )

    st.dataframe(
        df,
        width="stretch"
    )


    # =====================================================
    # RUN BUTTON
    # =====================================================

    if st.button(
        "Run AI Mapping & Translation"
    ):

        upload_id, saved_file_path = (
            save_uploaded_file(
                uploaded_file
            )
        )

        mapping_results = {}
        mapping_table = []
        translation_review = []


        # =================================================
        # AI MAPPING
        # =================================================

        with st.spinner(
            "Llama is mapping payroll fields..."
        ):

            for column in df.columns:

                samples = (
                    df[column]
                    .dropna()
                    .head(5)
                    .tolist()
                )

                prediction = ask_llm(
                    column,
                    samples
                )

                mapping_results[
                    column
                ] = prediction

                mapping_table.append({
                    "Source Field":
                        column,

                    "Target Field":
                        prediction
                })


        st.success(
            "AI field mapping completed."
        )

        st.subheader(
            "AI Field Mapping"
        )

        st.dataframe(
            pd.DataFrame(
                mapping_table
            ),
            width="stretch",
            hide_index=True
        )


        # =================================================
        # TRANSLATION
        # =================================================

        translated_df = pd.DataFrame()

        for source_column in df.columns:

            target_field = mapping_results[
                source_column
            ]

            translated_values = []

            for value in df[
                source_column
            ]:

                translated_value, status = (
                    translate_value(
                        target_field,
                        value
                    )
                )

                translated_values.append(
                    translated_value
                )

                translation_review.append({

                    "Source Field":
                        source_column,

                    "Target Field":
                        target_field,

                    "Original Value":
                        value,

                    "Translated Value":
                        translated_value,

                    "Status":
                        status
                })


                save_eval_log(

                    upload_id=
                        upload_id,

                    client_file=
                        uploaded_file.name,

                    source_field=
                        source_column,

                    target_field=
                        target_field,

                    original_value=
                        value,

                    translated_value=
                        translated_value,

                    translation_status=
                        status
                )


            translated_df[
                target_field
            ] = translated_values


        # =================================================
        # RESULTS
        # =================================================

        st.subheader(
            "Translated Payroll Data"
        )

        st.dataframe(
            translated_df,
            width="stretch"
        )


        st.subheader(
            "Translation Review"
        )

        review_df = pd.DataFrame(
            translation_review
        )

        st.dataframe(
            review_df,
            width="stretch",
            hide_index=True
        )


        # =================================================
        # PROCESSING SUMMARY
        # =================================================

        total_values = len(
            translation_review
        )

        needs_review = sum(
            1
            for item in translation_review
            if item["Status"]
            == "NEEDS_REVIEW"
        )

        automatically_handled = (
            total_values
            - needs_review
        )


        st.subheader(
            "Processing Summary"
        )

        col1, col2, col3 = (
            st.columns(3)
        )

        col1.metric(
            "Values Processed",
            total_values
        )

        col2.metric(
            "Automatically Handled",
            automatically_handled
        )

        col3.metric(
            "Needs Review",
            needs_review
        )


        st.success(
            "Client file and evaluation data captured successfully."
        )

        st.write(
            f"Upload ID: `{upload_id}`"
        )

        st.write(
            f"Saved file: `{saved_file_path}`"
        )


# =========================================================
# ALWAYS SHOW EVAL DASHBOARD
# =========================================================

show_eval_dashboard()