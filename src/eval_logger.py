import json
import os
import uuid
from datetime import datetime


LOG_FILE = "results/eval_logs.jsonl"
UPLOAD_FOLDER = "data/uploads"


def save_uploaded_file(uploaded_file):

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Create unique ID for this upload
    upload_id = str(uuid.uuid4())

    original_filename = uploaded_file.name

    saved_filename = f"{upload_id}_{original_filename}"

    file_path = os.path.join(
        UPLOAD_FOLDER,
        saved_filename
    )

    # Save uploaded CSV
    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return upload_id, file_path


def save_eval_log(
    upload_id,
    client_file,
    source_field,
    target_field,
    original_value,
    translated_value,
    translation_status
):

    os.makedirs("results", exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(),
        "upload_id": upload_id,
        "client_file": client_file,
        "source_field": source_field,
        "target_field": target_field,
        "original_value": str(original_value),
        "translated_value": str(translated_value),
        "translation_status": translation_status
    }

    with open(LOG_FILE, "a") as file:
        file.write(
            json.dumps(record) + "\n"
        )